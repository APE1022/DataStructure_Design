from envs import ParkEnv
from strategy import TaskStrategy
from tqdm import tqdm

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

    env = ParkEnv(park_size=park_size, n_robots=n_robots, n_vehicles=n_vehicles, n_batteries=n_batteries,time_step=1)
    strategy = TaskStrategy(env)

    print("请选择调度策略：nearest（最近任务优先）、max_demand（最大需求优先）、max_priority（最大优先级）")
    strat = input().strip().lower()
    if strat not in ['nearest', 'max_demand', 'max_priority']:
        strat = 'nearest'

    steps = 10000  # 仿真步数
    for t in tqdm(range(steps), desc="Simulating"):
        strategy.update(time_step=1, strategy=strat)
        if t % 1000 == 0:
            print(f"Step {t}:")
            print(env.get_status())

if __name__ == "__main__":
    main()