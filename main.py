from modules.envs import ParkEnv
from modules.strategy import TaskStrategy
from modules.visualization import ChargingVisualizer, StartupScreen
from modules.qlearning_agent import QLearningAgent
import pickle
import os
import sys
import pygame
from pygame.locals import QUIT, KEYDOWN, K_ESCAPE, K_SPACE, MOUSEBUTTONDOWN, K_RETURN


def create_environment(map_size, time_step=1.0):
    """根据地图大小创建环境"""
    config = {
        'small': {
            'park_size': (100, 100),
            'n_robots': 4,
            'n_vehicles': 10,
            'n_batteries': 3,
            'generate_vehicles_probability': 0.003056, # 以秒为单位，计算得每小时生成车辆的期望为11辆
            'cell_size': 11
        },
        'medium': {
            'park_size': (200, 200),
            'n_robots': 16,
            'n_vehicles': 40,
            'n_batteries': 10,
            'generate_vehicles_probability': 0.011667, # 以秒为单位，计算得每小时生成车辆的期望为42辆
            'cell_size': 5
        },
        'large': {
            'park_size': (500, 500),
            'n_robots': 40,
            'n_vehicles': 100,
            'n_batteries': 24,
            'generate_vehicles_probability': 0.029167, # 以秒为单位，计算得每小时生成车辆的期望为105辆
            'cell_size': 2
        }
    }
    
    settings = config.get(map_size, config['small'])
    
    env = ParkEnv(
        park_size=settings['park_size'],
        n_robots=settings['n_robots'],
        n_vehicles=settings['n_vehicles'],
        n_batteries=settings['n_batteries'],
        time_step=time_step,
        generate_vehicles_probability=settings['generate_vehicles_probability']
    )
    
    return env,settings['cell_size']

def main():
    """完全交互式主函数"""
    pygame.init()
    
    # 显示启动界面
    startup = StartupScreen()
    configs = startup.run()
    
    if configs is None:
        pygame.quit()
        return
    
    # 获取用户设置
    current_map_size = configs['map_size']
    current_strategy = configs['strategy']
    current_time_step = configs['time_step']
    step_speed = 11 - configs['speed']  # 转换为步长延迟：速度越大，延迟越小
    debug_mode = configs['debug']
    show_stats = configs['show_stats']
    
    # 创建初始环境
    env, cell_size = create_environment(current_map_size, current_time_step)

    # 创建 agent
    agent = QLearningAgent(env)
    # 动态选择 Q 表文件名
    q_table_path = f"config/q_table/{current_map_size}_most_q_table.pkl"
    if os.path.exists(q_table_path):
        with open(q_table_path, "rb") as f:
            agent.q_table = pickle.load(f)
    else:
        print(f"Q表文件不存在: {q_table_path}")
        agent.q_table = None  # 或者给出提示
    strategy = TaskStrategy(env, time_step=current_time_step, map_size=current_map_size, agent=agent)
    visualizer = ChargingVisualizer(env, cell_size=cell_size)
    
    # 设置初始UI状态
    visualizer.strategy = current_strategy
    visualizer.map_size = current_map_size
    visualizer.time_step = current_time_step
    visualizer.step_speed = step_speed
    
    # 仿真控制
    step = 0
    max_steps = 28800 // current_time_step
    running = True
    paused = False
    
    # 主循环
    clock = pygame.time.Clock()
    while running and step < max_steps:
        # 处理事件
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                elif event.key == K_SPACE:
                    paused = not paused
                    visualizer.paused = paused
            elif event.type == MOUSEBUTTONDOWN:
                result = visualizer.handle_mouse_click(event.pos)
                if visualizer.back_button.collidepoint(event.pos):
                    # 回到初始选择界面
                    configs = StartupScreen().run()
                    if configs is None:
                        pygame.quit()
                        return
                    # 重新初始化环境和可视化器
                    current_map_size = configs['map_size']
                    current_strategy = configs['strategy']
                    current_time_step = configs['time_step']
                    step_speed = 11 - configs['speed']
                    debug_mode = configs['debug']
                    show_stats = configs['show_stats']
                    env, cell_size = create_environment(current_map_size, current_time_step)
                    strategy = TaskStrategy(env, time_step=current_time_step, map_size=current_map_size)
                    visualizer = ChargingVisualizer(env, cell_size=cell_size)
                    visualizer.strategy = current_strategy
                    visualizer.map_size = current_map_size
                    visualizer.time_step = current_time_step
                    visualizer.step_speed = step_speed
                    step = 0
                    paused = False
                    continue
        if step == max_steps -1:
            paused = True
        # 更新仿真
        if not paused:
            strategy.update(strategy=current_strategy)
            
            if show_stats and step % 1000 == 0:
                status = env.get_status()
                if debug_mode:
                    print(f"Step {step}, 策略: {current_strategy}, 时间步长: {current_time_step}")
                    print(status)
                
            step += 1

        # 渲染
        visualizer.render(step, current_strategy)
        
        # 控制帧率
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()