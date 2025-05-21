import pygame
from pygame.locals import QUIT, KEYDOWN, K_ESCAPE, K_SPACE, MOUSEBUTTONDOWN
from envs import ParkEnv
from strategy import TaskStrategy
from visualization_new import ChargingVisualizer

class SimulationManager:
    def __init__(self):
        pygame.init()
        self.screen_width = 800
        self.screen_height = 600
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("充电机器人仿真系统")
        
        # 尝试加载中文字体
        for font_name in ["hiraginosansgb", "songti", "stheitimedium", "simhei"]:
            try:
                self.font = pygame.font.SysFont(font_name, 18)
                self.title_font = pygame.font.SysFont(font_name, 32)
                break
            except:
                continue
        else:
            self.font = pygame.font.SysFont(None, 18)
            self.title_font = pygame.font.SysFont(None, 32)
        
        # 初始界面按钮
        self.buttons = {
            # 策略按钮
            "nearest": pygame.Rect(250, 200, 300, 40),
            "max_demand": pygame.Rect(250, 250, 300, 40),
            "max_priority": pygame.Rect(250, 300, 300, 40),
            "genetic": pygame.Rect(250, 350, 300, 40),
            
            # 地图大小按钮
            "small": pygame.Rect(250, 420, 90, 40),
            "medium": pygame.Rect(355, 420, 90, 40),
            "large": pygame.Rect(460, 420, 90, 40),
            
            # 开始按钮
            "start": pygame.Rect(300, 500, 200, 50),
        }
        
        # 初始化默认设置
        self.current_map_size = 'small'
        self.current_strategy = 'genetic'
        self.current_time_step = 1.0
        
    def show_selection_screen(self):
        """显示选择界面，返回是否进入仿真"""
        running = True
        
        while running:
            # 处理事件
            for event in pygame.event.get():
                if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                    return False
                elif event.type == MOUSEBUTTONDOWN:
                    pos = event.pos
                    for name, rect in self.buttons.items():
                        if rect.collidepoint(pos):
                            if name == "start":
                                return True  # 进入仿真
                            elif name in ["nearest", "max_demand", "max_priority", "genetic"]:
                                self.current_strategy = name
                            elif name in ["small", "medium", "large"]:
                                self.current_map_size = name
            
            # 绘制界面
            self.screen.fill((240, 240, 240))
            
            # 标题
            title = self.title_font.render("充电机器人仿真系统", True, (0, 0, 0))
            self.screen.blit(title, (self.screen_width//2 - title.get_width()//2, 50))
            
            # 策略选择标题
            subtitle = self.font.render("请选择调度策略:", True, (0, 0, 0))
            self.screen.blit(subtitle, (250, 170))
            
            # 地图大小标题
            map_title = self.font.render("请选择地图大小:", True, (0, 0, 0))
            self.screen.blit(map_title, (250, 390))
            
            # 绘制按钮
            button_labels = {
                "nearest": "最近任务优先",
                "max_demand": "最大需求优先",
                "max_priority": "最大优先级优先",
                "genetic": "遗传算法",
                "small": "小地图",
                "medium": "中地图", 
                "large": "大地图",
                "start": "开始仿真",
            }
            
            # 绘制所有按钮
            for name, rect in self.buttons.items():
                # 当前选中的按钮高亮显示
                if (name == self.current_strategy and name in ["nearest", "max_demand", "max_priority", "genetic"]) or \
                   (name == self.current_map_size and name in ["small", "medium", "large"]):
                    color = (100, 200, 100)
                elif name == "start":
                    color = (100, 150, 250)
                else:
                    color = (180, 180, 180)
                
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, (0, 0, 0), rect, 2)
                
                txt = self.font.render(button_labels.get(name, name), True, (0, 0, 0))
                self.screen.blit(txt, (rect.x + rect.width//2 - txt.get_width()//2, rect.y + rect.height//2 - txt.get_height()//2))
            
            pygame.display.flip()
        
        return False
    
    def start_simulation(self):
        """开始仿真"""
        # 创建环境
        env = self.create_environment(self.current_map_size, self.current_time_step)
        strategy = TaskStrategy(env, time_step=self.current_time_step)
        
        # 创建可视化器（简化后只包含重启按钮）
        visualizer = SimplifiedVisualizer(env, self.current_strategy)
        visualizer.strategy = self.current_strategy
        
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
                    return False
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        return False
                    elif event.key == K_SPACE:
                        paused = not paused
                elif event.type == MOUSEBUTTONDOWN:
                    action = visualizer.handle_mouse_click(event.pos)
                    if action == "restart":
                        return True  # 重启，返回到选择界面
            
            # 更新仿真
            if not paused:
                strategy.update(strategy=self.current_strategy)
                env.update(env.time_step)
                
                if step % 1000 == 0:
                    print(f"Step {step}, 策略: {self.current_strategy}")
                    print(env.get_status())
                    
                step += 1
            
            # 渲染
            visualizer.render(step, paused)
            
            # 控制帧率
            clock.tick(60)
        
        return False
    
    def create_environment(self, map_size, time_step=1.0):
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
            time_step=time_step,
            generate_vehicles_probability=settings['generate_vehicles_probability']
        )
        
        return env
    
    def run(self):
        """运行完整流程"""
        restart = True
        
        while restart:
            # 显示选择界面
            if self.show_selection_screen():
                # 进入仿真
                restart = self.start_simulation()
            else:
                restart = False
        
        pygame.quit()


class SimplifiedVisualizer(ChargingVisualizer):
    """简化版可视化器，只有重启按钮"""
    def __init__(self, env, strategy, cell_size=12, info_height=150):
        super().__init__(env, cell_size, info_height)
        self.strategy = strategy
        
        # 只保留重启按钮
        self.restart_button = pygame.Rect(self.screen_width - 120, 10, 100, 40)
    
    def draw_control_panel(self):
        # 绘制控制面板
        # 只保留重启按钮和当前策略信息
        strategy_names = {
            "nearest": "最近任务优先", 
            "max_demand": "最大需求优先", 
            "max_priority": "最大优先级优先",
            "genetic": "遗传算法"
        }
        
        # 显示当前策略
        strategy_txt = self.font.render(f"当前策略: {strategy_names.get(self.strategy, self.strategy)}", True, (0, 0, 0))
        self.screen.blit(strategy_txt, (10, 10))
        
        # 绘制重启按钮
        pygame.draw.rect(self.screen, (200, 100, 100), self.restart_button)
        pygame.draw.rect(self.screen, (0, 0, 0), self.restart_button, 2)
        restart_txt = self.font.render("重新选择", True, (0, 0, 0))
        self.screen.blit(restart_txt, (self.restart_button.x + 10, self.restart_button.y + 10))
    
    def handle_mouse_click(self, pos):
        if self.restart_button.collidepoint(pos):
            return "restart"
        return None
    
    def render(self, step, paused):
        # 清屏
        self.screen.fill((255, 255, 255))
        
        # 绘制网格
        self.draw_grid()
        
        # 绘制元素
        self.draw_battery_station()
        self.draw_vehicles()
        self.draw_robots()
        
        # 绘制状态信息
        self.draw_info(step)
        
        # 绘制暂停状态
        if paused:
            pause_font = pygame.font.SysFont(None, 72)
            pause_text = pause_font.render("PAUSED", True, (255, 0, 0))
            self.screen.blit(pause_text, (self.screen_width//2 - pause_text.get_width()//2, 
                                        self.screen_height//2 - pause_text.get_height()//2))
        
        # 绘制简化版控制面板
        self.draw_control_panel()
        
        # 更新显示
        pygame.display.flip()


def main():
    manager = SimulationManager()
    manager.run()

if __name__ == "__main__":
    main()