from envs import ParkEnv
from strategy import TaskStrategy
from visualization_new2 import ChargingVisualizer
import pygame
from pygame.locals import QUIT, KEYDOWN, K_ESCAPE, K_SPACE, MOUSEBUTTONDOWN
import sys

def create_environment(map_size):
    """根据地图大小创建环境"""
    config = {
        'small': {
            'park_size': (50, 50),
            'n_robots': 4,
            'n_vehicles': 10,
            'n_batteries': 3,
            'generate_vehicles_probability': 0.001
        },
        'medium': {
            'park_size': (100, 100),
            'n_robots': 16,
            'n_vehicles': 40,
            'n_batteries': 12,
            'generate_vehicles_probability': 0.005
        },
        'large': {
            'park_size': (500, 500),
            'n_robots': 40,
            'n_vehicles': 100,
            'n_batteries': 30,
            'generate_vehicles_probability': 0.012
        }
    }
    
    settings = config.get(map_size, config['small'])
    
    env = ParkEnv(
        park_size=settings['park_size'],
        n_robots=settings['n_robots'],
        n_vehicles=settings['n_vehicles'],
        n_batteries=settings['n_batteries'],
        time_step=0.1,
        generate_vehicles_probability=settings['generate_vehicles_probability']
    )
    
    return env

def main():
    """主函数 - 运行交互式仿真"""
    pygame.init()
    
    # 初始化默认设置
    current_map_size = 'small'
    current_strategy = 'genetic'
    
    # 创建初始环境和控制器
    env = create_environment(current_map_size)
    strategy = TaskStrategy(env, time_step=1)
    
    # 创建可视化器，设置初始状态
    visualizer = ChargingVisualizer(env, cell_size=12)  # 自动适应屏幕
    visualizer.strategy = current_strategy
    visualizer.map_size = current_map_size
    
    # 仿真控制参数
    running = True
    paused = False
    step = 0
    max_steps = 10000
    
    # 主循环
    clock = pygame.time.Clock()
    while running and step < max_steps:
        # 1. 处理事件
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                elif event.key == K_SPACE:
                    paused = not paused
                    print("仿真已" + ("暂停" if paused else "继续"))
            elif event.type == MOUSEBUTTONDOWN:
                result = visualizer.handle_mouse_click(event.pos)
                if result:
                    if result["type"] == "strategy":
                        current_strategy = result["value"]
                        print(f"更改策略: {current_strategy}")
                    elif result["type"] == "map_size":
                        print(f"选择地图大小: {result['value']}，点击重启按钮生效")
                    elif result["type"] == "restart":
                        print(f"重建环境: {result['value']}")
                        # 保存当前设置
                        old_strategy = visualizer.strategy
                        old_map_size = visualizer.map_size
                        
                        # 重建环境
                        current_map_size = result["value"]
                        env = create_environment(current_map_size)
                        strategy = TaskStrategy(env, time_step=1)
                        
                        # 创建新的可视化器并恢复设置
                        visualizer = ChargingVisualizer(env, cell_size=None)
                        visualizer.strategy = old_strategy
                        visualizer.map_size = old_map_size
                        
                        # 重置计数
                        step = 0
        
        # 2. 更新仿真（非暂停状态）
        if not paused:
            strategy.update(strategy=current_strategy)
            env.update(env.time_step)
            
            # 定期输出状态
            if step % 1000 == 0:
                print(f"Step {step}:")
                print(env.get_status())
            
            step += 1
        
        # 3. 渲染界面
        visualizer.render(step)
        
        # 4. 控制帧率
        clock.tick(60)  # 限制最高60帧/秒
    
    # 清理
    pygame.quit()
    print("仿真结束")

if __name__ == "__main__":
    main()