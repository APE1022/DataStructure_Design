import numpy as np
import random

class QLearningAgent:
    """
    强化学习调度助手，适用于园区自动充电机器人调度
    """
    def __init__(self, env, learning_rate=0.1, discount_factor=0.9, exploration_rate=1.0, exploration_decay=0.995, exploration_min=0.01):
        self.env = env
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate
        self.exploration_decay = exploration_decay
        self.exploration_min = exploration_min

        # 状态空间和动作空间大小可根据实际环境调整
        self.state_size = 100  # 可根据状态离散化方式调整
        self.action_size = len(env.robots)
        self.q_table = np.zeros((self.state_size, self.action_size))

    def discretize_state(self, state):
        """
        将环境状态离散化为整数索引
        这里只用第一个机器人和第一个待充电车辆的电量做离散化
        """
        # 假设env.get_status()返回有"robots"和"needcharge_vehicles"等
        robot_soc = int(self.env.robots[0].battery.soc)
        if self.env.needcharge_vehicles:
            vehicle_soc = int(self.env.needcharge_vehicles[0].battery.soc)
        else:
            vehicle_soc = 0
        idx = (robot_soc // 10) * 10 + (vehicle_soc // 10)
        return idx % self.state_size

    def choose_action(self, state):
        """
        ε-greedy 策略选择动作
        """
        state_idx = self.discretize_state(state)
        if random.random() < self.exploration_rate:
            return random.randint(0, self.action_size - 1)
        else:
            return np.argmax(self.q_table[state_idx])

    def update_q_table(self, state, action, reward, next_state, done):
        state_idx = self.discretize_state(state)
        next_state_idx = self.discretize_state(next_state)
        best_next_action = np.argmax(self.q_table[next_state_idx])
        td_target = reward + self.discount_factor * self.q_table[next_state_idx, best_next_action] * (not done)
        td_error = td_target - self.q_table[state_idx, action]
        self.q_table[state_idx, action] += self.learning_rate * td_error

    def train(self, episodes=1000, max_steps=1000, log_interval=100):
        for ep in range(episodes):
            state = self.env.get_status()
            total_reward = 0
            for step in range(max_steps):
                action = self.choose_action(state)
                # 假设env.step(action)能处理动作，否则可只用env.step()
                self.env.update(0.1)
                next_state = self.env.get_status()
                reward = self._calc_reward(next_state)
                # 判断所有车辆是否已完成
                done = all(getattr(v, "state", "") == "completed" for v in getattr(self.env, "vehicles", []))
                self.update_q_table(state, action, reward, next_state, done)
                state = next_state
                total_reward += reward
                if done:
                    break
            self.exploration_rate = max(self.exploration_min, self.exploration_rate * self.exploration_decay)
            if (ep + 1) % log_interval == 0:
                print(f"Episode {ep+1}, Total Reward: {total_reward:.2f}, Exploration Rate: {self.exploration_rate:.3f}")

    def _calc_reward(self, state):
        """
        简单奖励函数：已服务车辆数
        """
        # 假设env有completed_vehicles列表
        return len(self.env.completed_vehicles)