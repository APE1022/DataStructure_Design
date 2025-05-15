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
        self.state_size = 100  # 示例：可根据状态离散化方式调整
        self.action_size = len(env.robots)
        self.q_table = np.zeros((self.state_size, self.action_size))

    def discretize_state(self, state):
        """
        将环境状态离散化为整数索引
        这里可根据实际状态特征进行编码
        """
        # 示例：只用第一个机器人和第一个车辆的电量做离散化
        robot_battery = int(state["robots"][0][2])  # 机器人状态
        vehicle_battery = int(state["vehicles"][0][1])
        idx = (robot_battery // 10) * 10 + (vehicle_battery // 10)
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
                # 这里假设env.step(action)返回新状态、奖励、done
                self.env.step()  # 你可以根据实际需要传递action
                next_state = self.env.get_status()
                # 奖励函数可根据车辆服务完成数、能耗等自定义
                reward = self._calc_reward(next_state)
                done = all(v[3] for v in next_state["vehicles"])
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
        可根据README要求扩展为更复杂的奖励
        """
        return sum(1 for v in state["vehicles"] if v[3])