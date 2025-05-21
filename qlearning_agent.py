import numpy as np
import random
import copy

class QLearningAgent:
    """
    强化学习调度助手，适用于园区自动充电机器人调度
    """
    def __init__(self, env, learning_rate=0.1, discount_factor=0.9, exploration_rate=1.0, exploration_decay=0.995, exploration_min=0.01):
        self.env = env
        self.static_env = copy.deepcopy(env)
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate
        self.exploration_decay = exploration_decay
        self.exploration_min = exploration_min

        # 状态空间和动作空间大小可根据实际环境调整
        self.state_size = 100  # 可根据状态离散化方式调整
        self.action_size = len(self.env.robots) * self.env.max_vehicles  # 机器人数量 * 最大车辆数
        self.q_table = np.zeros((self.state_size, self.action_size))

    def discretize_state(self, state):
        # 以所有机器人和所有待充电车辆的 soc 平均值为特征
        robot_socs = [int(r.battery.soc) for r in self.env.robots]
        car_socs = [int(c.battery.soc) for c in self.env.needcharge_vehicles]
        avg_robot_soc = int(np.mean(robot_socs)) if robot_socs else 0
        avg_car_soc = int(np.mean(car_socs)) if car_socs else 0
        idx = (avg_robot_soc // 10) * 10 + (avg_car_soc // 10)
        return idx % self.state_size

    def choose_action(self, state):
        state_idx = self.discretize_state(state)
        valid_actions = []
        for robot_idx, robot in enumerate(self.env.robots):
            if robot.state != "available":
                continue
            for car_idx, car in enumerate(self.env.needcharge_vehicles):
                if car.state == "needcharge" and car_idx < self.env.max_vehicles:
                    action = robot_idx * self.env.max_vehicles + car_idx
                    if action < self.action_size:
                        valid_actions.append(action)
        if not valid_actions:
            return random.randint(0, self.action_size - 1)
        if random.random() < self.exploration_rate:
            return random.choice(valid_actions)
        else:
            q_values = self.q_table[state_idx, valid_actions]
            best_idx = np.argmax(q_values)
            return valid_actions[best_idx]

    def update_q_table(self, state, action, reward, next_state, done):
        state_idx = self.discretize_state(state)
        next_state_idx = self.discretize_state(next_state)
        if action >= self.action_size:
            action = self.action_size - 1  # 防止越界
        best_next_action = np.argmax(self.q_table[next_state_idx])
        td_target = reward + self.discount_factor * self.q_table[next_state_idx, best_next_action] * (not done)
        td_error = td_target - self.q_table[state_idx, action]
        self.q_table[state_idx, action] += self.learning_rate * td_error

    def decode_action(self, action):
        robot_idx = action // self.env.max_vehicles
        car_idx = action % self.env.max_vehicles
        return robot_idx, car_idx

    def assign_task(self, robot, car):
        """
        直接分配任务给机器人
        """
        if robot.state == "available" and car.state == "needcharge":
            robot.assign_task(car)
            # 机器人状态会自动变为gocar，car状态会在robot.update中变为charging

    def train(self, choice, episodes=1000, max_steps=1000, log_interval=1, debug=False):
        for ep in range(episodes):
            self.env = copy.deepcopy(self.static_env)
            # 保证每次重置后车辆生成概率仍为1
            state = self.env.get_status()
            total_reward = 0

            for step in range(max_steps):
                self.env.update(self.env.time_step)
                action = self.choose_action(state)
                robot_idx, car_idx = self.decode_action(action)
                if robot_idx < len(self.env.robots) and car_idx < len(self.env.needcharge_vehicles):
                    robot = self.env.robots[robot_idx]
                    car = self.env.needcharge_vehicles[car_idx]
                    if robot.state == "available" and car.state == "needcharge":
                        self.assign_task(robot, car)

                next_state = self.env.get_status()
                if choice == 1:
                    reward = self._calc_reward_most(debug=debug)
                else:
                    reward = self._calc_reward_nearest(debug=debug)
                # 判断所有车辆是否已完成或失败
                done = 0
                self.update_q_table(state, action, reward, next_state, done)
                state = next_state
                total_reward += reward
                if done:
                    break

            # if debug:
            #     # 打印所有车辆列表信息
            #     vehicle_lists = [
            #         ("needcharge_vehicles", self.env.needcharge_vehicles),
            #         ("charging_vehicles", self.env.charging_vehicles),
            #         ("completed_vehicles", self.env.completed_vehicles),
            #         ("failed_vehicles", self.env.failed_vehicles)
            #     ]
            #     for name, vlist in vehicle_lists:
            #         if vlist:
            #             print(f"{name}:")
            #             for car in vlist:
            #                 print(f"  id={car.id}, state={getattr(car, 'state', None)}, soc={getattr(car.battery, 'soc', None)}")
            #     # 打印所有机器人信息
            #     if self.env.robots:
            #         print("robots:")
            #         for robot in self.env.robots:
            #             print(f"  id={robot.id}, state={getattr(robot, 'state', None)}, soc={getattr(robot.battery, 'soc', None)}")

            self.exploration_rate = max(self.exploration_min, self.exploration_rate * self.exploration_decay)
            if (ep + 1) % log_interval == 0:
                completed_num = len(self.env.completed_vehicles)
                failed_num = len(self.env.failed_vehicles)
                total_generated = self.env.vehicles_index
                rgv_count = self.env.random_generate_vehicles_count  # 新增
                print(f"Episode {ep+1}, Total Reward: {total_reward:.2f}, Exploration Rate: {self.exploration_rate:.3f}, "
                    f"Completed: {completed_num}, Failed: {failed_num}, Total Generated: {total_generated}")

    def _calc_reward_most(self, debug=False):
        reward = 0
        for car in self.env.failed_vehicles:
            if not hasattr(car, "counted") or car.counted == 0:
                reward -= 50
                car.counted = 1
        for car in self.env.completed_vehicles:
            if not hasattr(car, "counted") or car.counted == 0:
                reward += 100
                car.counted = 1
        # 每有一个机器人正在服务奖励+1
        for robot in self.env.robots:
            if robot.state != "available":
                reward += 1
        return reward

    def _calc_distance_to_charge_station(self, car):
        return (abs(car.parking_spot[0] - self.env.battery_station.location[0])  
                + abs(car.parking_spot[1] - self.env.battery_station.location[1]))

    def _calc_reward_nearest(self, debug=False):
        completed_reward = 100
        failed_reward = -50
        largest_distance = self.env.park_size[0] / 2 + self.env.park_size[1] / 2
        reward = 0
        for car in self.env.failed_vehicles:
            if not hasattr(car, "counted") or car.counted == 0:
                reward += (failed_reward * self._calc_distance_to_charge_station(car) / largest_distance)
                car.counted = 1
        for car in self.env.completed_vehicles:
            if not hasattr(car, "counted") or car.counted == 0:
                reward += (completed_reward * self._calc_distance_to_charge_station(car) / largest_distance)
                car.counted = 1
        # for car in self.env.charging_vehicles:
        #     reward += ((car.battery.soc - (car.required_soc - car.battery_gap)) / car.battery_gap
        #                * self._calc_distance_to_charge_station(car) / largest_distance)
        return reward