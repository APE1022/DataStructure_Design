import random
import numpy as np
import gym
from gym import spaces
import pickle

"""
早期测试文件（已弃用）
===================================
本模块实现了基于 OpenAI Gym 框架的园区充电调度仿真环境，包含车辆、充电机器人、电池对象的定义，以及环境状态更新、任务分配和强化学习训练流程。

主要功能：
- 定义车辆(Car)、机器人(Robot)、电池(Battery)等核心对象
- 实现充电环境(ChargingEnv)的状态管理、任务分配与仿真流程
- 支持最近任务优先、最大需求优先等多种调度策略
- 集成 Q-learning 智能体进行强化学习训练
- 支持环境重置、状态观测、奖励计算和仿真步进

设计说明：
本模块适用于园区级自动充电调度的研究与算法测试，支持不同规模环境的灵活配置。通过与 Gym 兼容的接口，可方便集成各类 RL 算法进行智能调度策略优化。

用法示例：
    # 选择规模并初始化环境
    env = ChargingEnv(park_size=(20, 20), n_robots=16, n_vehicles=30)
    agent = QLearningAgent(env)
    agent.train_endless(log_interval=400)

创建/维护者: 甄理
创建日期: 2025-05-14
最后修改: 2025-05-14
版本: 0.1.0
"""

# 车辆类
class Car:
    def __init__(self, id, arrival_time, departure_time, parking_spot, remaining_battery, required_battery, home_x=0,
                 home_y=0):
        self.arrival_time = arrival_time  # 到达时间
        self.departure_time = departure_time  # 离开时间
        self.parking_spot = parking_spot  # 停车位置
        self.remaining_battery = remaining_battery  # 剩余电量
        self.required_battery = required_battery  # 离开时需要的电量
        self.sum_distance = parking_spot[0] + parking_spot[1]  # 到(0,0)的距离
        self.id = id  # id
        self.x, self.y = parking_spot
        self.home_x = home_x  # 充电站横坐标
        self.home_y = home_y  # 充电站纵坐标
        self.battery_gap = None
        self.x, self.y = self.parking_spot
        self.serviced = False
        self.available = 1  # 是否正在充电
        self.completed = 0  # 是否达到离开标准
        self.failed = 0  # 是否能够正常离开
        self.charged_rate = 0  # 充电速率(默认为0)
        self.counted = 0  # 是否已经计算过奖励

        if self.completed == 1 or self.failed == 1:  # 如果车辆已经离开或失败则永远不可充电
            self.available = 0

        if self.remaining_battery >= self.required_battery:  # 如果已达到离开要求则更改已完成
            self.completed = 1

    def battery_update(self, per_time=1):  # 充单位时间的电后的电量变化
        self.remaining_battery += self.charged_rate * per_time

    def calculate_battery_gap(self):
        self.battery_gap = self.required_battery - self.remaining_battery

    def charge(self, rate, per_time=1):
        self.remaining_battery = min(self.remaining_battery + rate * per_time, 100)
        self.calculate_battery_gap()

    def update_reward(self):
        self.calculate_battery_gap()  # 每次更新前计算 gap
        if self.battery_gap <= 0:
            return 0.0
        # 可选：使用一个更直观的奖励公式
        return 1.0 if self.remaining_battery >= self.required_battery else 0.1

    def is_done(self):
        # 比如当 remaining_battery >= required_battery 时
        return self.remaining_battery >= self.required_battery


# 充电机器人类
class Robot:
    """
    A robot that swaps or recharges batteries for vehicles.
    """
    def __init__(self, id, home=(0, 0), cost_per_unit=0.5, initial_battery=None):
        self.id = id
        self.home = home  # docking station
        self.x, self.y = home
        self.cost_per_unit = cost_per_unit
        self.goal_x = self.x
        self.goal_y = self.y

        # Battery attributes
        self.battery = None         # reference to Battery instance
        self.battery_level = 0      # current level mirror
        if initial_battery is not None:
            self.assign_battery(initial_battery)

        # charging metrics
        self.initial_rate = 2.0     # max charge rate
        self.current_rate = self.initial_rate
        self.in_action = False      # busy flag
        self.target_vehicle = None

    def assign_battery(self, battery: "Battery"):
        """
        Assign a Battery object to this robot.
        """
        self.battery = battery
        battery.in_use = True
        self.battery_level = battery.charge_level

    def release_battery(self):
        """
        Release current battery back to pool.
        """
        if self.battery:
            self.battery.in_use = False
            self.battery = None
            self.battery_level = 0

    def move_cost(self, distance):
        return distance * self.cost_per_unit

    def can_return(self):
        """
        Check if robot has enough battery to return home.
        """
        dist = abs(self.x - self.home[0]) + abs(self.y - self.home[1])
        return self.battery_level >= self.move_cost(dist)

    def update_charge_rate(self):
        """
        Charging speed decays linearly to 50% at full battery.
        """
        factor = 1 - 0.5 * (self.battery_level / 100)
        self.current_rate = max(self.initial_rate * factor, 0.1)

    def charge(self, minutes=1):
        """
        Charge attached battery and robot.
        """
        if minutes is None:
            minutes = self.time_scale
        self.update_charge_rate()
        increment = self.current_rate * minutes
        self.battery_level = min(self.battery_level + increment, 100)
        if self.battery:
            self.battery.charge_level = self.battery_level

    def discharge(self, distance):
        """
        Consume battery based on movement.
        """
        cost = self.move_cost(distance)
        self.battery_level = max(self.battery_level - cost, 0)
        if self.battery:
            self.battery.charge_level = self.battery_level

    def go_to(self, target_x, target_y):
        if self.x != target_x:
            step_x = 1 if target_x > self.x else -1
            new_x = self.x + step_x
            new_y = self.y
        elif self.y != target_y:
            step_y = 1 if target_y > self.y else -1
            new_x = self.x
            new_y = self.y + step_y
        else:
            # 已经在目标位置
            new_x, new_y = self.x, self.y

        move_dist = abs(new_x - self.x) + abs(new_y - self.y)
        self.discharge(move_dist)
        self.x, self.y = new_x, new_y

class Battery:
    """
    Represents a swappable battery pack.
    """
    def __init__(self, id, charge_level=100, max_rate=1.0):
        self.id = id
        self.charge_level = charge_level  # percentage [0, 100]
        self.max_rate = max_rate  # charge rate when not in use
        self.in_use = False

    def charge(self, minutes=1):
        """
        Charge this battery if it is not currently in use.
        """
        if not self.in_use:
            self.charge_level = min(self.charge_level + self.max_rate * minutes, 100)
            
# 充电环境类
class ChargingEnv(gym.Env):
    """
    Environment where robots service vehicles by swapping or recharging.
    """
    metadata = {'render.modes': ['human']}

    def __init__(self, park_size=(1, 1), n_robots=1, n_vehicles=1):
        regen_interval = 10500
        self.park_size = park_size
        self.n_robots = n_robots
        self.n_vehicles = n_vehicles

        #时间速度
        self.time_scale = 0.01 * (self.park_size[0]**2 / 100)
        self.spawn_prob = self.n_vehicles / regen_interval
        self.next_car_id = self.n_vehicles

        # build battery pool
        self.batteries = [Battery(i) for i in range(n_robots // 2)]

        # create robots
        self.robots = []
        print("请输入1选择最近任务策略，2选择最大任务策略")
        self.strategy = int(input())  # 改成实例属性
        for i in range(n_robots):
            # round-robin assign
            bat = self.batteries[i % len(self.batteries)]
            robot = Robot(i, initial_battery=bat)
            self.robots.append(robot)

        # gym spaces
        self.action_space = spaces.Discrete(n_robots + 1)
        self.observation_space = spaces.Box(low=0, high=100,
                                            shape=(n_robots * 5 + n_vehicles * 5,), dtype=np.float32)

        self.vehicles = []  # will be populated on reset()
        self.current_step = 0
        self.max_steps = 14400

    def reset(self):
        # reset time and vehicles
        self.current_step = 0
        self.vehicles = self._generate_vehicles(self.n_vehicles)
        return self._get_obs()

    def regenerate_vehicles(self):
        self.vehicles = self._generate_vehicles(self.n_vehicles)

    def _generate_vehicles(self, count):
        vehicles = []
        for i in range(count):
            arrival = random.randint(0, 720)
            stay = random.randint(0, 720)
            departure = arrival + stay
            spot = (random.randint(0, self.park_size[0]),
                    random.randint(0, self.park_size[1]))
            remaining = random.randint(5, 50)
            # 确保 required >= remaining
            required = random.randint(remaining, 100)
            car = Car(i, arrival, departure, spot, remaining, required)
            car.calculate_battery_gap()  # 如果你需要这个方法
            vehicles.append(car)
        return vehicles

    def _get_obs(self):
        data = []
        # robots: x, y, battery_level, current_rate, in_action
        for r in self.robots:
            data.extend([r.x, r.y, r.battery_level, r.current_rate, float(r.in_action)])
        # vehicles: x, y, remaining_battery, required_battery, is_serviced
        for v in self.vehicles:
            data.extend([
                v.parking_spot[0],  # x
                v.parking_spot[1],  # y
                v.remaining_battery,
                v.required_battery,
                float(v.serviced)
            ])

        return np.array(data, dtype=np.float32)

    def step(self, action):
        reward = 0.0

        if random.random() < self.spawn_prob:
            # 生成一辆新车，地点、电量都随机
            new_car = self._generate_vehicles(1)[0]
            # 给它一个新的唯一 ID
            new_car.id = self.next_car_id
            self.next_car_id += 1
            # 加入环境
            self.vehicles.append(new_car)

        # 1) 对每个机器人，看它是否空闲
        if action < self.n_robots:
            rob = self.robots[action]
            if not rob.in_action:
                # 如果电量不足以去服务下一个最近车辆并且返回，则先回家充电
                if self.strategy == 1:
                    veh = self._find_nearest_unserviced(rob.home)
                elif self.strategy == 2:
                    veh = self._find_max_demand_unserviced(rob.home)
                if veh is None:
                    # 没有未服务车辆就不动
                    pass
                else:
                    cost_to_veh = rob.move_cost(abs(rob.x - veh.x) + abs(rob.y - veh.y))
                    cost_back = rob.move_cost(abs(veh.x - rob.home[0]) + abs(veh.y - rob.home[1]))
                    # 如果当前电量 < 去(veh)+回(home)所需
                    if rob.battery_level < cost_to_veh + cost_back:
                        # 先回家充电
                        rob.goal_x, rob.goal_y = rob.home
                        rob.in_action = True
                        rob.target_vehicle = None
                        rob.charging_at_home = True  # 新增：标记为在家充电
                    else:
                        # 电量足够，直接去服务
                        rob.goal_x, rob.goal_y = veh.x, veh.y
                        rob.in_action = True
                        rob.target_vehicle = veh
                        rob.charging_at_home = False

        # 2) 移动阶段（不变）
        for rob in self.robots:
            if rob.in_action:
                rob.go_to(rob.goal_x, rob.goal_y)

        # 3) 到达后要么服务车辆，要么在家充电
        for rob in self.robots:
            # 在家充电
            if getattr(rob, 'charging_at_home', False) and (rob.x, rob.y) == rob.home:
                # 充到满电或至少能去一次完整任务再返回
                rob.charge(minutes=self.time_scale)
                #最大或者最近优先，更换注释行数切换
                if self.strategy == 1:
                    veh = self._find_nearest_unserviced(rob.home)
                elif self.strategy==2:
                    veh = self._find_max_demand_unserviced(rob.home)
                if veh:
                    cost_to_veh = rob.move_cost(abs(rob.x - veh.x) + abs(rob.y - veh.y))
                    cost_back = rob.move_cost(abs(veh.x - rob.home[0]) + abs(veh.y - rob.home[1]))
                    if rob.battery_level >= cost_to_veh + cost_back:
                        rob.charging_at_home = False
                        rob.target_vehicle = veh
                        rob.goal_x, rob.goal_y = veh.x, veh.y

            # 服务车辆（原逻辑）
            elif rob.target_vehicle and (rob.x, rob.y) == (rob.target_vehicle.x, rob.target_vehicle.y):
                veh = rob.target_vehicle
                veh.charge(rob.current_rate, per_time=self.time_scale)
                reward += veh.update_reward()
                if veh.is_done():
                    veh.completed = 1
                    veh.available = 0
                    veh.serviced = True
                    # 服务完成后，让机器人回家
                    rob.in_action = True
                    rob.charging_at_home = True
                    rob.target_vehicle = None
                    rob.goal_x, rob.goal_y = rob.home



        for bat in self.batteries:
            bat.charge(minutes=self.time_scale)

        self.current_step += 1
        done = self.current_step >= self.max_steps or all(v.serviced for v in self.vehicles)
        obs = self._get_obs()
        return obs, reward, done, {}

    def _find_nearest_unserviced(self, origin):
        best, dist = None, float('inf')
        ox, oy = origin
        for v in self.vehicles:
            if not v.serviced:
                d = abs(v.x - ox) + abs(v.y - oy)
                if d < dist:
                    best, dist = v, d
        return best

    def _find_max_demand_unserviced(self,origin):
        best_vehicle = None
        max_gap = -float('inf')
        for v in self.vehicles:
            if not v.serviced:
                v.calculate_battery_gap()
                if v.battery_gap > max_gap:
                    max_gap = v.battery_gap
                    best_vehicle = v
        return best_vehicle


class QLearningAgent:
    def __init__(self, env, learning_rate=0.1, discount_factor=0.9, exploration_rate=1.0, exploration_decay=0.995,
                 exploration_min=0.01):
        self.env = env
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate
        self.exploration_decay = exploration_decay
        self.exploration_min = exploration_min

        # Q 表，初始化为 0
        self.q_table = np.zeros((25, self.env.action_space.n))  # Q 表的大小应该和状态空间匹配

    def choose_action(self, state):
        """选择动作，基于探索和利用"""
        state_index = self.discretize_state(state)  # 离散化状态
        # print(f"State index: {state_index}, Type: {type(state_index)}")  # 打印索引及类型
        if random.uniform(0, 1) < self.exploration_rate:
            return self.env.action_space.sample()  # 随机选择动作
        else:
            return np.argmax(self.q_table[state_index])  # 选择 Q 值最高的动作

    def update_q_table(self, state, action, reward, next_state, done):
        """根据 Q-learning 更新公式更新 Q 表"""
        state_index = self.discretize_state(state)
        next_state_index = self.discretize_state(next_state)

        # 确保 next_state_index 在 Q 表范围内
        if next_state_index >= self.q_table.shape[0]:
            next_state_index = self.q_table.shape[0] - 1

        # 选择下一个状态的最佳动作
        best_next_action = np.argmax(self.q_table[next_state_index])  # 选择下一个状态的最佳动作

        current_q_value = self.q_table[state_index, action]

        # 更新 Q 值
        new_q_value = current_q_value + self.learning_rate * (
                reward + self.discount_factor * self.q_table[next_state_index, best_next_action] - current_q_value)
        self.q_table[state_index, action] = new_q_value

    def discretize_state(self, state):
        """将状态离散化为一个整数索引"""
        state_index = 0
        for i, feature in enumerate(state):
            state_index += int(feature * 10)  # 假设状态值在 [0, 1] 范围，放大10倍来离散化

        return state_index % 25  # 使状态索引在范围 [0, 24] 内

    def train_endless(self, log_interval=5):
        # 1) 只在最开始重置一次环境
        state = self.env.reset()
        total_reward = 0.0
        t = 0

        # 用于累积记录哪些车辆已经完成过
        completed_ids = set()
        cumulative_completed = 0

        while True:
            t += 1
            action = self.choose_action(state)
            next_state, reward, done, _ = self.env.step(action)
            self.update_q_table(state, action, reward, next_state, done)
            state = next_state
            total_reward += reward

            # 检查本次 step 中有哪些车辆新完成
            for v in self.env.vehicles:
                if getattr(v, 'completed', 0) == 1 and v.id not in completed_ids:
                    completed_ids.add(v.id)
                    cumulative_completed += 1


            if t % log_interval == 0:
                print(f"[Step {t/log_interval}] TotalReward={total_reward:.4f}  CumulativeCompleted={cumulative_completed}")

scale=0
print("请选择规模small，medium或者large")
scale = input().strip().lower()

if scale == 'small':
    env = ChargingEnv(park_size=(10, 10), n_robots=4, n_vehicles=10)
elif scale == 'medium':
    env = ChargingEnv(park_size=(20, 20), n_robots=16, n_vehicles=30)
elif scale == 'large':
    env = ChargingEnv(park_size=(30, 30), n_robots=36, n_vehicles=40)
agent = QLearningAgent(env)
#每一步多长时间
agent.train_endless(log_interval=400)

# 保存 Q 表
# 如果需要保存 Q 表，下面的代码可以用于保存
# pickle.dump(qlearning_agent.q_table, open("q_table.pkl", "wb"))
