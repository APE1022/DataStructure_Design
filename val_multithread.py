import os
import pickle
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.ticker as mtick
from concurrent.futures import ThreadPoolExecutor, as_completed
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', "hiraginosansgb", "songti", "stheitimedium", "simhei"]
matplotlib.rcParams['axes.unicode_minus'] = False
from modules.envs import ParkEnv
from modules.strategy import TaskStrategy
from modules.qlearning_agent import QLearningAgent

STRATEGIES = ['nearest', 'max_demand', 'max_priority', 'genetic', 'hyper_heuristic', 'RL']
N_TESTS = 100
MAP_SIZE = 'medium'
MAX_WORKERS = 8

def create_environment(map_size, time_step=10):
    config = {
        'small': {'park_size': (100, 100), 'n_robots': 4, 'n_vehicles': 10, 'n_batteries': 3, 'generate_vehicles_probability': 0.003056, 'cell_size': 7.4},
        'medium': {'park_size': (200, 200), 'n_robots': 16, 'n_vehicles': 40, 'n_batteries': 10, 'generate_vehicles_probability': 0.011667, 'cell_size': 3.7},
        'large': {'park_size': (500, 500), 'n_robots': 40, 'n_vehicles': 100, 'n_batteries': 24, 'generate_vehicles_probability': 0.029167, 'cell_size': 1.5}
    }
    settings = config.get(map_size, config['small'])
    env = ParkEnv(
        park_size=settings['park_size'],
        n_robots=settings['n_robots'],
        n_vehicles=settings['n_vehicles'],
        n_batteries=settings['n_batteries'],
        time_step=10,
        generate_vehicles_probability=settings['generate_vehicles_probability']
    )
    return env

def single_run(strategy_name, map_size='medium'):
    env = create_environment(map_size)
    agent = QLearningAgent(env)
    # 加载Q表（仅RL策略需要）
    if strategy_name == 'RL':
        q_table_path = f"config/q_table/{map_size}_most_q_table.pkl"
        if os.path.exists(q_table_path):
            with open(q_table_path, "rb") as f:
                agent.q_table = pickle.load(f)
        else:
            agent.q_table = None
    strategy = TaskStrategy(env, time_step=10, map_size=map_size, agent=agent)
    max_steps = 2880  # 8小时
    for step in range(max_steps):
        strategy.update(strategy=strategy_name)
        env.update(time_step=10)
    # 统计平均等待时间和成功率
    all_vehicles = env.charging_vehicles + env.completed_vehicles + env.failed_vehicles
    if all_vehicles:
        avg_wait = np.mean([getattr(v, "waittime", 0) for v in all_vehicles])
    else:
        avg_wait = 0
    total = len(env.completed_vehicles) + len(env.failed_vehicles)
    success_rate = len(env.completed_vehicles) / total if total > 0 else 0
    return avg_wait, success_rate

def evaluate_strategy_multithread(strategy_name, n_tests=10, map_size='medium'):
    avg_wait_list = []
    success_rate_list = []
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, n_tests)) as executor:
        futures = [executor.submit(single_run, strategy_name, map_size) for _ in range(n_tests)]
        for i, future in enumerate(as_completed(futures)):
            avg_wait, success_rate = future.result()
            avg_wait_list.append(avg_wait)
            success_rate_list.append(success_rate)
            print(f"{strategy_name} 第{i+1}次: 平均等待时间={avg_wait:.2f}, 成功率={success_rate:.2%}")
    return np.mean(avg_wait_list), np.mean(success_rate_list)

def main():
    avg_waits = []
    success_rates = []
    for strategy in STRATEGIES:
        avg_wait, success_rate = evaluate_strategy_multithread(strategy, N_TESTS, MAP_SIZE)
        avg_waits.append(avg_wait)
        success_rates.append(success_rate)
        print(f"策略: {strategy}, 平均等待时间: {avg_wait:.2f}, 成功率: {success_rate:.2%}")

    # 绘图
    x = np.arange(len(STRATEGIES))
    plt.figure(figsize=(10,4))
    plt.subplot(1,2,1)
    plt.bar(x, avg_waits, color='skyblue')
    plt.xticks(x, STRATEGIES, rotation=30)
    plt.ylabel("平均等待时间 (s)")
    plt.title("中等规模环境各算法平均等待时间对比（100轮）")

    plt.subplot(1,2,2)
    plt.bar(x, success_rates, color='orange')
    plt.xticks(x, STRATEGIES, rotation=30)
    plt.ylabel("成功率")
    plt.title("中等规模环境各算法成功率对比（100轮）")
    plt.ylim(0.9, 1.0)
    plt.gca().yaxis.set_major_formatter(mtick.PercentFormatter(1.0))

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()