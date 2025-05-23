import random
import numpy as np
import gym
from gym import spaces
import pickle 

"""
早期测试文件（已弃用）
==========================================================
本模块实现了基于 OpenAI Gym 框架的园区充电调度仿真环境，包含车辆(Car)、充电机器人(Robot)的定义、环境状态管理、任务分配与强化学习训练流程。

主要功能：
- 定义车辆(Car)和充电机器人(Robot)的属性与行为
- 实现充电环境(ChargingEnv)的状态管理、任务分配与仿真流程
- 支持环境的重置、状态观测、奖励计算和仿真步进
- 集成 Q-learning 智能体进行强化学习训练与策略优化
- 支持 Q 表的保存与加载

设计说明：
本模块适用于园区级自动充电调度的算法测试与强化学习研究。通过与 Gym 兼容的接口，可方便集成各类 RL 算法进行智能调度策略优化。

用法示例：
    env = ChargingEnv()
    agent = QLearningAgent(env)
    agent.train(episodes=1000)
    pickle.dump(agent.q_table, open("q_table.pkl", "wb"))

创建/维护者: 肖翔云
创建日期: 2025-04-07
最后修改: 2025-04-07
版本: 0.0.1
"""

# 车辆类
class Car:
    def __init__(self, id, arrival_time, departure_time, parking_spot, remaining_battery, required_battery, home_x = 0, home_y = 0):
        self.arrival_time = arrival_time  # 到达时间
        self.departure_time = departure_time  # 离开时间
        self.parking_spot = parking_spot  # 停车位置
        self.remaining_battery = remaining_battery  # 剩余电量
        self.required_battery = required_battery  # 离开时需要的电量
        self.sum_distance = parking_spot[0] + parking_spot[1]  # 到(0,0)的距离
        self.id = id  # id
        self.home_x = home_x  # 充电站横坐标
        self.home_y = home_y  # 充电站纵坐标
        self.battery_gap = None

        self.available = 1  # 是否正在充电
        self.completed = 0  # 是否达到离开标准
        self.failed = 0  # 是否能够正常离开
        self.charged_rate = 0  # 充电速率(默认为0)
        self.counted = 0  # 是否已经计算过奖励

        if self.completed == 1 or self.failed == 1:  # 如果车辆已经离开或失败则永远不可充电
            self.available = 0

        if self.remaining_battery >= self.required_battery:  # 如果已达到离开要求则更改已完成
            self.completed = 1
        
    def battery_update(self, per_time = 1):  # 充单位时间的电后的电量变化
        self.remaining_battery += self.charged_rate * per_time
    
    def calculate_battery_gap(self):
        self.battery_gap = self.required_battery - self.remaining_battery

# 充电机器人类
class Robot:
    def __init__(self, id, battery, x=0, y=0, cost_per_mile=0.5, charged_rate=2, home_x = 0, home_y = 0):
        self.battery = battery  # 电量
        self.cost_per_mile = cost_per_mile  # 每单位距离消耗的电量
        self.charge_per_minute = 1   # 每分钟充电电量
        self.charged_rate = charged_rate  # 返回基地充电的效率
        self.x, self.y = x, y  # 机器人当前位置
        self.home_x, self.home_y = home_x, home_y  # 充电站的位置 (假设充电站在(0,0))
        self.distance_to_home =abs(self.x - self.home_x) + abs(self.y - self.home_y)  # 机器人当前位置到充电站的曼哈顿距离
        self.id = id  # id
        self.charging_car_id = None

        self.available = 1  # 是否正在充电
        if self.battery > 100:  # 机器人的电量上限为100%
            self.battery = 100

    def charge_battery_update(self, per_time = 1):  # 充单位时间的电后的电量变化
        self.battery += self.charged_rate * per_time

    def cost_battery_update(self, per_time = 1):  # 给当前车辆充单位时间的电后的电量变化
        self.battery -= self.charge_per_minute * per_time

    def required_battery_to_return(self):
        return self.distance_to_home * self.cost_per_mile  # 返回充电站的电量需求

    def can_return_to_home(self):
        """判断机器人是否有足够电量返回充电站"""
        return self.battery >= self.required_battery_to_return() + 1
    
# 充电环境类
class ChargingEnv(gym.Env):
    def __init__(self, park_area_size=(100, 100), num_vehicles=20, num_robots=3):
        super(ChargingEnv, self).__init__()

        self.park_area_size = park_area_size
        self.num_vehicles = num_vehicles
        self.num_robots = num_robots

        self.robots = self.simulate_robots(num_robots)
        self.all_vehicles = self.simulate_cars(num_vehicles)
        self.vehicles = []
        
        self.current_time = 0  # 当前时间
        self.done = False  # 是否结束
        self.current_step = 0  # 步骤计数
        self.action_space = spaces.Discrete(self.num_robots + 1)  

        # 状态空间，机器人位置、电量、车辆位置、电量等
        self.observation_space = spaces.Box(low=0, high=1, shape=(self.num_robots + self.num_vehicles, 5))

    def simulate_cars(self, num_cars): 
        
        # print("正在模拟园区车辆")
        
        vehicles = []
        for i in range(num_cars):
            arrival_time = random.randint(0,720)  # 到达时间
            stay_duration_minutes = random.randint(0, 720)  # 随机停车时长
            departure_time = arrival_time + stay_duration_minutes
            parking_spot = (random.randint(0, self.park_area_size[0]), random.randint(0, self.park_area_size[1]))  # 停车位置
            remaining_battery = random.randint(5, 50)  # 剩余电量
            id = i

            # 需要先初始化 required_battery，再进入while循环
            required_battery = random.randint(20, 80)  # 离开时需要的电量，假设20%-80%
            
            # 确保剩余电量大于所需电量
            while required_battery < remaining_battery:
                required_battery = random.randint(20, 80)  # 重新生成需要的电量

            # 创建并返回Car对象
            car = Car(id, arrival_time, departure_time, parking_spot, remaining_battery, required_battery)
            car.calculate_battery_gap()

            vehicles.append(car)
        
        # print("成功模拟园区车辆")
        
        return vehicles


    def simulate_robots(self, num_robots):
        
        # print("正在生成模拟机器人")
        
        robots = []
        for i in range(num_robots):
            id = i
            robot = Robot(id, battery = 100)
            robots.append(robot)
        
        #print("成功生成模拟机器人")
        
        return robots

    def reset(self):
        """重置环境"""
        self.robots = self.simulate_robots(self.num_robots)
        self.all_vehicles = self.simulate_cars(self.num_vehicles)
        self.vehicles = []
        
        self.current_time = 0
        self.done = False
        self.current_step = 0
        return self._get_observation()

    def _get_observation(self):
        """获取当前环境的观察信息"""
        # 获取机器人的信息
        robots_info = np.array([[robot.x, robot.y, robot.battery, robot.cost_per_mile, robot.charge_per_minute] for robot in self.robots])
        
        # 如果有车辆，获取车辆信息，否则确保 vehicles_info 为一个形状匹配的空数组
        if self.vehicles:
            vehicles_info = np.array([[vehicle.parking_spot[0], vehicle.parking_spot[1], vehicle.remaining_battery, vehicle.required_battery, vehicle.sum_distance] for vehicle in self.vehicles])
        else:
            vehicles_info = np.empty((0, 5))  # 创建一个空的二维数组，列数是5，表示每辆车的信息

        # 将机器人的信息和车辆的信息合并
        observation = np.concatenate([robots_info, vehicles_info], axis=0)
        
        # 扁平化观察空间，转换为一维数组
        return observation.flatten()  # 扁平化为一维数组

    def fresh(self, per_time):  # 经过单位时间后，更新环境状态

        # print("正在更新环境状态")

        reward = 0

        for car in self.all_vehicles:  # 检测并加入车辆
            if self.current_time == car.arrival_time:
                self.vehicles.append(car)
        
        for car in self.vehicles:  # 检测是否存在无法成功按时离开的车辆
            if self.current_time == car.departure_time:
                if car.remaining_battery < car.required_battery and not car.counted:
                    car.failed = 1
                    car.counted = 1
                    reward -= 50

                elif car.remaining_battery >= car.required_battery and not car.counted:
                    car.completed = 1
                    reward += 100
                    car.counted = 1

        for robot in self.robots:  # 更新所有机器人的电量
            if robot.available:
                robot.charge_battery_update(per_time)
            else:
                robot.cost_battery_update(per_time)

        for car in self.vehicles:  # 更新所有车辆的电量
            if not car.available and not car.failed and not car.completed:
                car.battery_update(per_time = per_time)

                reward += (car.remaining_battery - (car.required_battery - car.battery_gap)) / car.battery_gap
        
        # 判断机器人是否有足够的电量返回充电站
        for robot in self.robots:
            if not robot.available:
                if not robot.can_return_to_home():
                    reward -= 3

                    # 如果没有足够的电量返回充电站，则执行返回充电站操作
                    robot.battery -= robot.required_battery_to_return()
                    #重置充电中的robot和car的属性
                    robot.available = 1
                    robot.x = 0
                    robot.y = 0

                    for car in self.vehicles:
                        if car.id == robot.charging_car_id:
                            car.available = 1
                            car.charged_rate = 0

                    robot.charging_car_id = None

        # print("成功更新环境")

        return reward
    
    def check_if_step(self):  # 检测当前是否存在可充电的车辆和机器人，如果有则采取行动
        num_cars_available = 0
        num_robots_available = 0

        for car in self.vehicles:
            if car.available == 1:
                num_cars_available += 1

        for robot in self.robots:
            if robot.available == 1:
                num_robots_available += 1
        
        if num_robots_available > 0 and num_cars_available > 0:
            return 1
        
        return 0

    def step(self, action):
        """执行一步操作"""

        if self.done:
            return self._get_observation(), 0, self.done, {}
        
        reward = 0
        done = False

        if action < self.num_robots:
            robot = self.robots[action]

            # 机器人执行动作
            if robot and self.check_if_step():
                closest_car = self._find_nearest_vehicle(0, 0)
                if closest_car and robot.battery > closest_car.sum_distance :
                    self._perform_action(robot)

            # 增加时间流逝，每次step增加一定的时间
            self.current_time += 1  # 每步增加1分钟

            # 更新所有车辆和机器人的状态
            reward += self.fresh(per_time = 1)

        if action == self.num_robots:
            self.current_time += 1
            reward += self.fresh(per_time = 1)

        self.current_step += 1
        
        if self.current_step >= 14400:
            done = True
        
        if len(self.vehicles) == len(self.all_vehicles):  # 检查所有车辆是否都完成处理
            for car in self.vehicles:
                uncompleted = 0
                if car.completed == 0 or car.failed == 0:
                    uncompleted += 1
                if not uncompleted:
                    done = True

        return self._get_observation(), reward, done, {}

    def _perform_action(self, robot):
        """根据机器人的状态执行动作"""

        target_vehicle = self._find_nearest_vehicle(0, 0)
        
        if target_vehicle:
            robot.available = 0
            target_vehicle.available = 0
            target_vehicle.charged_rate = robot.charge_per_minute
            robot.charging_car_id = target_vehicle.id
            robot.x = target_vehicle.parking_spot[0]
            robot.y = target_vehicle.parking_spot[1]

            robot.battery -= target_vehicle.sum_distance

    def _find_nearest_vehicle(self, home_x, home_y):
        """根据机器人的位置找到离它最近的车辆"""
        closest_vehicle = None
        min_distance = float('inf')  # 初始化最小距离为无穷大

        for vehicle in self.vehicles:
            if not vehicle.completed and not vehicle.failed and vehicle.available:  # 只选择没有充电且未完成的车辆
                # 计算车辆与机器人之间的曼哈顿距离
                distance = abs(vehicle.parking_spot[0] - home_x) + abs(vehicle.parking_spot[1] - home_y)

                # 更新最小距离和最近的车辆
                if distance < min_distance:
                    min_distance = distance
                    closest_vehicle = vehicle

        return closest_vehicle

class QLearningAgent:
    def __init__(self, env, learning_rate=0.1, discount_factor=0.9, exploration_rate=1.0, exploration_decay=0.995, exploration_min=0.01):
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
        #print(f"State index: {state_index}, Type: {type(state_index)}")  # 打印索引及类型
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


    def train(self, episodes=1000):
        """训练 Q-learning 模型"""
        for episode in range(episodes):
            state = self.env.reset()  # 获取初始状态
            done = False
            total_reward = 0  # 每个 episode 的奖励
            while not done:
                action = self.choose_action(state)  # 根据当前状态选择动作
                next_state, reward, done, _ = self.env.step(action)  # 执行动作并获取反馈
                self.update_q_table(state, action, reward, next_state, done)  # 更新 Q 表
                state = next_state  # 更新状态
                total_reward += reward

            completed_vehicles = sum(1 for car in self.env.vehicles if car.completed == 1)

            # 打印每个 episode 的奖励
            print(f"Episode {episode + 1}/{episodes}, Total Reward: {total_reward}, Completed Vehicles: {completed_vehicles}")
            
            # 降低探索率
            self.exploration_rate = max(self.exploration_rate * self.exploration_decay, self.exploration_min)

# 创建环境和 Q-learning 代理
env = ChargingEnv()
qlearning_agent = QLearningAgent(env)

# 训练 Q-learning 模型
qlearning_agent.train(episodes=1000)

# 保存 Q 表
# 如果需要保存 Q 表，下面的代码可以用于保存
pickle.dump(qlearning_agent.q_table, open("q_table.pkl", "wb"))
