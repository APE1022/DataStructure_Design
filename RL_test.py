from envs import ParkEnv
from strategy import TaskStrategy
from tqdm import tqdm
from qlearning_agent import QLearningAgent
import os
import pickle

def train_model(env, choice, episodes=1000, max_steps=100, log_interval=10):
    """训练模型并保存"""
    agent = QLearningAgent(env)
    print("开始训练模型...")
    agent.train(choice, episodes=episodes, max_steps=max_steps, log_interval=log_interval, debug=True)
    
    # 保存训练好的模型
    os.makedirs('models', exist_ok=True)
    model_name = 'nearest_q_table.pkl' if choice == 0 else 'most_q_table.pkl'
    with open(f'models/{model_name}', 'wb') as f:
        pickle.dump(agent.q_table, f)
    print("模型训练完成并保存")
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
        
        done = False
        state = env.get_status()
        
        while not done:
            action = agent.choose_action(state)
            env.update(0.1)  # 更新环境
            next_state = env.get_status()
            done = all(getattr(v, "state", "") == "completed" 
                      for v in getattr(env, "vehicles", []))
            state = next_state
        
        total_completed += len(env.completed_vehicles)
        total_failed += len(env.failed_vehicles)
    
    avg_completed = total_completed / n_episodes
    avg_failed = total_failed / n_episodes
    print(f"\n评估结果:")
    print(f"平均完成车辆数: {avg_completed:.2f}")
    print(f"平均失败车辆数: {avg_failed:.2f}")
    print(f"平均完成率: {(avg_completed/(avg_completed+avg_failed))*100:.2f}%")

def main():
    print("请选择场景规模：small, medium, large")
    scale = input().strip().lower()
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
        print("输入无效，默认使用small规模")
        park_size = (50, 50)
        n_robots = 4
        n_vehicles = 10
        n_batteries = 4

    env = ParkEnv(park_size=park_size, 
                  n_robots=n_robots, 
                  n_vehicles=n_vehicles, 
                  n_batteries=n_batteries,
                  time_step=1)

    print("请选择调度策略：0.最近任务优先 1.最大任务优先")
    strategy_choice = int(input().strip())
    if strategy_choice not in [0, 1]:
        print("输入无效，默认使用最近任务优先")
        strategy_choice = 0

    env = ParkEnv(park_size=park_size, 
                  n_robots=n_robots, 
                  n_vehicles=n_vehicles, 
                  n_batteries=n_batteries,
                  time_step=1)

    print("请选择操作：1.训练新模型 2.加载已有模型")
    choice = input().strip()

    model_name = 'nearest_q_table.pkl' if strategy_choice == 0 else 'most_q_table.pkl'

    if choice == '1':
        agent = train_model(env, strategy_choice, episodes=1000, max_steps=10000, log_interval=10)
        evaluate_model(env, agent)
    elif choice == '2':
        if os.path.exists(f'models/{model_name}'):
            agent = QLearningAgent(env)
            with open(f'models/{model_name}', 'rb') as f:
                agent.q_table = pickle.load(f)
            evaluate_model(env, agent)
        else:
            print(f"未找到已训练的模型{model_name}，将训练新模型")
            agent = train_model(env, strategy_choice, episodes=1000, max_steps=100, log_interval=10)
            evaluate_model(env, agent)
if __name__ == "__main__":
    main()