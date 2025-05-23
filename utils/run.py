import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.envs import ParkEnv
from modules.qlearning_agent import QLearningAgent
import pickle

def run_q_table_model(scale='small', strategy_choice=0, episodes=10):
    # 场景参数
    if scale == 'small':
        park_size = (50, 50)
        n_robots = 4
        n_vehicles = 10
        n_batteries = 3
    elif scale == 'medium':
        park_size = (100, 100)
        n_robots = 16
        n_vehicles = 40
        n_batteries = 12
    elif scale == 'large':
        park_size = (200, 200)
        n_robots = 40
        n_vehicles = 100
        n_batteries = 30
    else:
        raise ValueError("Unknown scale")

    env = ParkEnv(park_size=park_size, 
                  n_robots=n_robots, 
                  n_vehicles=n_vehicles, 
                  n_batteries=n_batteries,
                  time_step=0.1)

    strategy_name = 'nearest' if strategy_choice == 0 else 'most'
    model_name = f'q_table/{scale}_{strategy_name}_q_table.pkl'

    if not os.path.exists(model_name):
        raise FileNotFoundError(f"Q表文件不存在: {model_name}")

    agent = QLearningAgent(env)
    with open(model_name, 'rb') as f:
        agent.q_table = pickle.load(f)

    print(f"加载模型: {model_name}")

    # 简单评估
    total_completed = 0
    total_failed = 0
    for episode in range(episodes):
        env = ParkEnv(park_size=park_size, 
                      n_robots=n_robots, 
                      n_vehicles=n_vehicles, 
                      n_batteries=n_batteries,
                      time_step=0.1)
        state = env.get_status()
        max_steps = 10000
        for _ in range(max_steps):
            env.update(0.1)
            action = agent.choose_action(state)
            robot_idx, car_idx = agent.decode_action(action)
            if robot_idx < len(env.robots) and car_idx < len(env.needcharge_vehicles):
                robot = env.robots[robot_idx]
                car = env.needcharge_vehicles[car_idx]
                if robot.state == "available" and car.state == "needcharge":
                    agent.assign_task(robot, car)
            state = env.get_status()
            if (len(env.completed_vehicles) + len(env.failed_vehicles)) >= env.max_vehicles:
                break
        total_completed += len(env.completed_vehicles)
        total_failed += len(env.failed_vehicles)
        print(f"Episode {episode+1}: 完成 {len(env.completed_vehicles)}, 失败 {len(env.failed_vehicles)}")

    print(f"\n平均完成车辆数: {total_completed/episodes:.2f}")
    print(f"平均失败车辆数: {total_failed/episodes:.2f}")

if __name__ == "__main__":
    # 可根据需要修改参数
    run_q_table_model(scale='small', strategy_choice=0, episodes=10)