from envs import ParkEnv
from strategy import TaskStrategy
from tqdm import tqdm
from qlearning_agent import QLearningAgent
from visualization_new import ChargingVisualizer

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
        park_size = (500, 500)
        n_robots = 40
        n_vehicles = 100
        n_batteries = 30
    else:
        print("输入无效，默认使用small规模")
        park_size = (50, 50)
        n_robots = 4
        n_vehicles = 10
        n_batteries = 8
    print("请选择调度策略：nearest（最近任务优先）、max_demand（最大需求优先）、max_priority（最大优先级）、genetic（遗传算法）")
    strat = input().strip().lower()
    if strat not in ['nearest', 'max_demand', 'max_priority', 'genetic']:
        strat = 'genetic'

    env = ParkEnv(park_size=park_size, n_robots=n_robots, n_vehicles=n_vehicles, n_batteries=n_batteries, time_step=0.1)
    strategy = TaskStrategy(env, time_step=1)
    visualizer = ChargingVisualizer(env, cell_size=12)


    steps = 20000  # 仿真步数
    import pygame
    from pygame.locals import QUIT, KEYDOWN, K_ESCAPE, K_SPACE
    paused = False

    for t in tqdm(range(steps), desc="Simulating"):
        # 处理可视化窗口事件
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                pygame.quit()
                return
            elif event.type == KEYDOWN and event.key == K_SPACE:
                paused = not paused
        if not paused:
            strategy.update(strategy=strat)
            env.update(env.time_step)
            visualizer.render(t)
            if t % 1000 == 0:
                print(f"Step {t}:")
                print(env.get_status())
        # pygame.time.delay(10)  # 控制可视化刷新速度

if __name__ == "__main__":
    main()