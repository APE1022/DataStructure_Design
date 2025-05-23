import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.envs import ParkEnv
from modules.strategy import TaskStrategy
from tqdm import tqdm
from modules.qlearning_agent import QLearningAgent
import pickle
print("当前工作目录:", os.getcwd())
def train_model(env, choice, scale, episodes=1000, max_steps=100, log_interval=10):
    """训练模型并保存"""
    agent = QLearningAgent(env)
    print("开始训练模型...")
    agent.train(choice, episodes=episodes, max_steps=max_steps, log_interval=log_interval, debug=False)
    
    # 保存训练好的模型
    os.makedirs('q_table', exist_ok=True)
    strategy_name = 'nearest' if choice == 0 else 'most'
    model_name = f'q_table/{scale}_{strategy_name}_q_table.pkl'
    with open(model_name, 'wb') as f:
        pickle.dump(agent.q_table, f)
    print(f"模型训练完成并保存为 {model_name}")
    return agent

def evaluate_model(env, agent, n_episodes=100):
    """评估模型性能"""
    print("\n开始评估模型...")
    total_completed = 0
    total_failed = 0

    for episode in tqdm(range(n_episodes)):
        env = ParkEnv(park_size=env.park_size, 
                     n_robots=len(env.robots), 
                     n_vehicles=env.max_vehicles,
                     n_batteries=len(env.battery_station.batteries),
                     time_step=env.time_step)
        
        state = env.get_status()
        done = False
        max_steps = 10000  # 防止死循环

        for _ in range(max_steps):
            env.update(0.1)
            action = agent.choose_action(state)
            robot_idx, car_idx = agent.decode_action(action)
            if robot_idx < len(env.robots) and car_idx < len(env.needcharge_vehicles):
                robot = env.robots[robot_idx]
                car = env.needcharge_vehicles[car_idx]
                if robot.state == "available" and car.state == "needcharge":
                    agent.assign_task(robot, car)
            next_state = env.get_status()
            # 判断所有车辆是否已完成或失败
            done = (len(env.completed_vehicles) + len(env.failed_vehicles)) >= env.max_vehicles
            state = next_state
            if done:
                break

        total_completed += len(env.completed_vehicles)
        total_failed += len(env.failed_vehicles)

    avg_completed = total_completed / n_episodes
    avg_failed = total_failed / n_episodes
    print(f"\n评估结果:")
    print(f"平均完成车辆数: {avg_completed:.2f}")
    print(f"平均失败车辆数: {avg_failed:.2f}")
    if (avg_completed + avg_failed) == 0:
        print("平均完成率: 无法计算（无完成或失败车辆）")
    else:
        print(f"平均完成率: {(avg_completed/(avg_completed+avg_failed))*100:.2f}%")

def train_single_episode(args):
    env_params, strategy_choice, max_steps = args
    # 重新创建环境和 agent，避免进程间冲突
    env = ParkEnv(**env_params)
    agent = QLearningAgent(env)
    agent.train(strategy_choice, episodes=1, max_steps=max_steps, log_interval=0, debug=False)
    return agent.q_table

def main():
    print("请选择场景规模：small, medium, large")
    scale = input().strip().lower()
    if scale == 'small':
        park_size = (50, 50)
        n_robots = 4
        n_vehicles = 10
        n_batteries = 3
        generate_vehicles_probability = 0.005 # 以秒为单位，计算得每小时生成车辆的期望为 0.005 * 3600 = 18辆
    elif scale == 'medium':
        park_size = (100, 100)
        n_robots = 16
        n_vehicles = 40
        n_batteries = 12
        generate_vehicles_probability = 0.02
    elif scale == 'large':
        park_size = (200, 200)
        n_robots = 40
        n_vehicles = 100
        n_batteries = 30
        generate_vehicles_probability = 0.05
    else:
        print("输入无效，默认使用small规模")
        scale = 'small'
        park_size = (50, 50)
        n_robots = 4
        n_vehicles = 10
        n_batteries = 4

    env = ParkEnv(park_size=park_size, 
                  n_robots=n_robots, 
                  n_vehicles=n_vehicles, 
                  n_batteries=n_batteries,
                  time_step=0.1,
                  generate_vehicles_probability=generate_vehicles_probability)

    print("请选择调度策略：0.最近任务优先 1.最大任务优先")
    strategy_choice = int(input().strip())
    if strategy_choice not in [0, 1]:
        print("输入无效，默认使用最近任务优先")
        strategy_choice = 0

    print("请选择操作：1.训练新模型 2.加载已有模型")
    choice = input().strip()

    strategy_name = 'nearest' if strategy_choice == 0 else 'most'
    model_name = f'q_table/{scale}_{strategy_name}_q_table.pkl'

    if choice == '1':
        agent = train_model(env, strategy_choice, scale, episodes=100, max_steps=100000, log_interval=10)
        evaluate_model(env, agent)
    elif choice == '2':
        if os.path.exists(model_name):
            agent = QLearningAgent(env)
            with open(model_name, 'rb') as f:
                agent.q_table = pickle.load(f)
            evaluate_model(env, agent)
        else:
            print(f"未找到已训练的模型{model_name}，将训练新模型")
            agent = train_model(env, strategy_choice, scale, episodes=100, max_steps=100000, log_interval=10)
            evaluate_model(env, agent)
if __name__ == "__main__":
    main()