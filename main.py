from envs import ParkEnv
from strategy import TaskStrategy
from visualization_stable import ChargingVisualizer, StartupScreen
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
            'generate_vehicles_probability': 0.1,
            'cell_size': 11
        },
        'medium': {
            'park_size': (200, 200),
            'n_robots': 16,
            'n_vehicles': 40,
            'n_batteries': 12,
            'generate_vehicles_probability': 0.005,
            'cell_size': 5
        },
        'large': {
            'park_size': (500, 500),
            'n_robots': 40,
            'n_vehicles': 100,
            'n_batteries': 30,
            'generate_vehicles_probability': 0.5,
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
    strategy = TaskStrategy(env, time_step=current_time_step)
    visualizer = ChargingVisualizer(env, cell_size=cell_size)
    
    # 设置初始UI状态
    visualizer.strategy = current_strategy
    visualizer.map_size = current_map_size
    visualizer.time_step = current_time_step
    visualizer.step_speed = step_speed
    
    # 仿真控制
    step = 0
    max_steps = 20000
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
                if result:
                    if result["type"] == "strategy":
                        current_strategy = result["value"]
                        if debug_mode:
                            print(f"策略变更: {current_strategy}")
                        
                    elif result["type"] == "time_step":
                        current_time_step = result["value"]
                        strategy.time_step = current_time_step
                        env.time_step = current_time_step
                        if debug_mode:
                            print(f"时间步长变更: {current_time_step}")
                        
                    elif result["type"] == "pause":
                        paused = result["value"]
                        if debug_mode:
                            print("仿真已" + ("暂停" if paused else "继续"))
                        
                    elif result["type"] == "restart":
                        if debug_mode:
                            print(f"重建环境: {result['value']}，时间步长: {current_time_step}")
                        
                        # 保存当前设置
                        old_strategy = visualizer.strategy
                        old_map_size = result["value"]
                        old_time_step = visualizer.time_step
                        old_speed = visualizer.step_speed
                        
                        # 重建环境
                        current_map_size = old_map_size
                        env = create_environment(current_map_size, old_time_step)
                        strategy = TaskStrategy(env, time_step=old_time_step)
                        
                        # 创建新的可视化器并恢复设置
                        visualizer = ChargingVisualizer(env)
                        visualizer.strategy = old_strategy
                        visualizer.map_size = old_map_size
                        visualizer.time_step = old_time_step
                        visualizer.step_speed = old_speed
                        
                        # 重置计数和状态
                        step = 0
                        current_strategy = old_strategy
                        current_time_step = old_time_step
                        visualizer.paused = paused
        
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