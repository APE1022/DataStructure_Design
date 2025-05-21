from envs import ParkEnv
from strategy import TaskStrategy
from visualization_stable import ChargingVisualizer
import pygame
from pygame.locals import QUIT, KEYDOWN, K_ESCAPE, K_SPACE, MOUSEBUTTONDOWN, K_RETURN
import sys
import os

# 初始化pygame
pygame.init()

# 颜色定义
COLORS = {
    'white': (255, 255, 255),
    'black': (0, 0, 0),
    'light_grey': (220, 220, 220),
    'dark_grey': (100, 100, 100),
    'button_normal': (150, 150, 150),
    'button_hover': (180, 180, 180),
    'button_selected': (100, 200, 100),
    'button_start': (100, 150, 250),
    'text_normal': (0, 0, 0),
    'text_highlight': (0, 0, 200),
    'background': (240, 240, 240),
    'title': (50, 50, 120)
}

class StartupScreen:
    """启动界面类，处理所有参数设置"""
    def __init__(self, screen_width=800, screen_height=600):
        # 设置屏幕
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("充电机器人仿真系统")
        
        # 尝试加载中文字体
        for font_name in ["hiraginosansgb", "songti", "stheitimedium", "simhei"]:
            try:
                self.font_normal = pygame.font.SysFont(font_name, 18)
                self.font_title = pygame.font.SysFont(font_name, 32, bold=True)
                self.font_subtitle = pygame.font.SysFont(font_name, 22, bold=True)
                break
            except:
                continue
        else:
            self.font_normal = pygame.font.SysFont(None, 18)
            self.font_title = pygame.font.SysFont(None, 32, bold=True)
            self.font_subtitle = pygame.font.SysFont(None, 22, bold=True)
        
        # 默认设置
        self.configs = {
            'map_size': 'small',
            'strategy': 'max_priority',
            'time_step': 1.0,
            'speed': 5,
            'debug': False,
            'show_stats': True
        }
        
        # 激活的输入框
        self.active_input = None
        self.input_text = ""
        
        # 按钮区域定义
        self.buttons = {
            # 地图大小按钮
            'small': pygame.Rect(250, 150, 90, 40),
            'medium': pygame.Rect(355, 150, 90, 40),
            'large': pygame.Rect(460, 150, 90, 40),
            
            # 策略按钮 - 第一行
            'nearest': pygame.Rect(250, 220, 145, 40),
            'max_demand': pygame.Rect(405, 220, 145, 40),
            
            # 策略按钮 - 第二行
            'max_priority': pygame.Rect(250, 270, 145, 40),
            'genetic': pygame.Rect(405, 270, 145, 40),
            
            # 策略按钮 - 第三行 (新增)
            'multi_objective': pygame.Rect(250, 320, 145, 40),
            'battery_management': pygame.Rect(405, 320, 145, 40),
            
            # 时间步长按钮和输入框
            'time_dec': pygame.Rect(300, 390, 40, 40),
            'time_inc': pygame.Rect(440, 390, 40, 40),
            'time_input': pygame.Rect(350, 390, 80, 40),  # 新增时间步长输入框
            
            # 速度按钮 (下移)
            'speed_dec': pygame.Rect(320, 450, 40, 40),
            'speed_inc': pygame.Rect(440, 450, 40, 40),
            
            # 调试选项 (下移)
            'debug_toggle': pygame.Rect(270, 510, 30, 30),
            'stats_toggle': pygame.Rect(480, 510, 30, 30),
            
            # 开始按钮 (下移)
            'start': pygame.Rect(300, 570, 200, 50)
        }
        
        # 定义标签
        self.labels = {
            'title': '充电机器人仿真系统',
            'map_size': '地图大小：',
            'strategy': '调度策略：',
            'time_step': '仿真时间步长：',
            'speed': '仿真速度：',
            'debug': '调试模式：',
            'show_stats': '显示统计信息：',
            'start': '开始仿真'
        }
    
    def draw(self):
        """绘制界面"""
        # 填充背景
        self.screen.fill(COLORS['background'])
        
        # 绘制标题
        title = self.font_title.render(self.labels['title'], True, COLORS['title'])
        self.screen.blit(title, (self.screen_width//2 - title.get_width()//2, 50))
        
        # 绘制地图大小选择
        map_label = self.font_subtitle.render(self.labels['map_size'], True, COLORS['black'])
        self.screen.blit(map_label, (120, 160))
        self._draw_button_group(['small', 'medium', 'large'], self.configs['map_size'], 
                               {'small': '小地图', 'medium': '中地图', 'large': '大地图'})
        
        # 绘制策略选择
        strategy_label = self.font_subtitle.render(self.labels['strategy'], True, COLORS['black'])
        self.screen.blit(strategy_label, (120, 240))
        self._draw_button_group(
            ['nearest', 'max_demand', 'max_priority', 'genetic', 'multi_objective', 'battery_management'], 
            self.configs['strategy'],
            {'nearest': '最近任务', 'max_demand': '最大需求', 
             'max_priority': '最高优先级', 'genetic': '遗传算法', 
             'multi_objective': '多目标优化', 'battery_management': '电池管理'}
        )
        
        # 绘制时间步长选择
        time_label = self.font_subtitle.render(self.labels['time_step'], True, COLORS['black'])
        self.screen.blit(time_label, (120, 400))
        
        # 减少按钮
        pygame.draw.rect(self.screen, COLORS['button_normal'], self.buttons['time_dec'])
        pygame.draw.rect(self.screen, COLORS['black'], self.buttons['time_dec'], 2)
        dec_text = self.font_normal.render('-', True, COLORS['black'])
        self.screen.blit(dec_text, (self.buttons['time_dec'].centerx - dec_text.get_width()//2, 
                                   self.buttons['time_dec'].centery - dec_text.get_height()//2))
        
        # 时间步长输入框
        input_color = COLORS['button_selected'] if self.active_input == 'time_step' else COLORS['white']
        pygame.draw.rect(self.screen, input_color, self.buttons['time_input'])
        pygame.draw.rect(self.screen, COLORS['black'], self.buttons['time_input'], 2)
        
        # 显示当前输入或配置值
        if self.active_input == 'time_step':
            time_value_text = self.input_text + '|' if pygame.time.get_ticks() % 1000 < 500 else self.input_text + ' '
        else:
            time_value_text = f"{self.configs['time_step']:.1f}"
            
        time_value = self.font_normal.render(time_value_text, True, COLORS['black'])
        self.screen.blit(time_value, (self.buttons['time_input'].centerx - time_value.get_width()//2, 
                                    self.buttons['time_input'].centery - time_value.get_height()//2))
        
        # 增加按钮
        pygame.draw.rect(self.screen, COLORS['button_normal'], self.buttons['time_inc'])
        pygame.draw.rect(self.screen, COLORS['black'], self.buttons['time_inc'], 2)
        inc_text = self.font_normal.render('+', True, COLORS['black'])
        self.screen.blit(inc_text, (self.buttons['time_inc'].centerx - inc_text.get_width()//2, 
                                   self.buttons['time_inc'].centery - inc_text.get_height()//2))
        
        # 提示文字
        tip_text = self.font_normal.render("点击输入框可直接输入步长值", True, COLORS['dark_grey'])
        self.screen.blit(tip_text, (300, 370))
        
        # 绘制速度选择
        speed_label = self.font_subtitle.render(self.labels['speed'], True, COLORS['black'])
        self.screen.blit(speed_label, (120, 460))
        pygame.draw.rect(self.screen, COLORS['button_normal'], self.buttons['speed_dec'])
        pygame.draw.rect(self.screen, COLORS['black'], self.buttons['speed_dec'], 2)
        dec_text = self.font_normal.render('-', True, COLORS['black'])
        self.screen.blit(dec_text, (self.buttons['speed_dec'].centerx - dec_text.get_width()//2, 
                                   self.buttons['speed_dec'].centery - dec_text.get_height()//2))
        
        speed_value = self.font_normal.render(f"{self.configs['speed']}", True, COLORS['black'])
        self.screen.blit(speed_value, (380 - speed_value.get_width()//2, 460))
        
        pygame.draw.rect(self.screen, COLORS['button_normal'], self.buttons['speed_inc'])
        pygame.draw.rect(self.screen, COLORS['black'], self.buttons['speed_inc'], 2)
        inc_text = self.font_normal.render('+', True, COLORS['black'])
        self.screen.blit(inc_text, (self.buttons['speed_inc'].centerx - inc_text.get_width()//2, 
                                   self.buttons['speed_inc'].centery - inc_text.get_height()//2))
        
        # 绘制调试选项
        debug_label = self.font_subtitle.render(self.labels['debug'], True, COLORS['black'])
        self.screen.blit(debug_label, (120, 520))
        pygame.draw.rect(self.screen, COLORS['white'], self.buttons['debug_toggle'])
        pygame.draw.rect(self.screen, COLORS['black'], self.buttons['debug_toggle'], 2)
        if self.configs['debug']:
            pygame.draw.line(self.screen, COLORS['black'], 
                           (self.buttons['debug_toggle'].left + 5, self.buttons['debug_toggle'].top + 15),
                           (self.buttons['debug_toggle'].left + 15, self.buttons['debug_toggle'].bottom - 5), 3)
            pygame.draw.line(self.screen, COLORS['black'], 
                           (self.buttons['debug_toggle'].left + 15, self.buttons['debug_toggle'].top + 5),
                           (self.buttons['debug_toggle'].right - 5, self.buttons['debug_toggle'].bottom - 5), 3)
        
        # 绘制统计信息选项
        stats_label = self.font_subtitle.render(self.labels['show_stats'], True, COLORS['black'])
        self.screen.blit(stats_label, (320, 520))
        pygame.draw.rect(self.screen, COLORS['white'], self.buttons['stats_toggle'])
        pygame.draw.rect(self.screen, COLORS['black'], self.buttons['stats_toggle'], 2)
        if self.configs['show_stats']:
            pygame.draw.line(self.screen, COLORS['black'], 
                           (self.buttons['stats_toggle'].left + 5, self.buttons['stats_toggle'].top + 15),
                           (self.buttons['stats_toggle'].left + 15, self.buttons['stats_toggle'].bottom - 5), 3)
            pygame.draw.line(self.screen, COLORS['black'], 
                           (self.buttons['stats_toggle'].left + 15, self.buttons['stats_toggle'].top + 5),
                           (self.buttons['stats_toggle'].right - 5, self.buttons['stats_toggle'].bottom - 5), 3)
        
        # 绘制开始按钮
        pygame.draw.rect(self.screen, COLORS['button_start'], self.buttons['start'])
        pygame.draw.rect(self.screen, COLORS['black'], self.buttons['start'], 2)
        start_text = self.font_subtitle.render(self.labels['start'], True, COLORS['black'])
        self.screen.blit(start_text, (self.buttons['start'].centerx - start_text.get_width()//2, 
                                    self.buttons['start'].centery - start_text.get_height()//2))
        
        # 更新屏幕
        pygame.display.flip()
    
    def _draw_button_group(self, button_names, selected, labels=None):
        """绘制按钮组"""
        if labels is None:
            labels = {name: name for name in button_names}
            
        for name in button_names:
            # 按钮底色
            color = COLORS['button_selected'] if name == selected else COLORS['button_normal']
            pygame.draw.rect(self.screen, color, self.buttons[name])
            pygame.draw.rect(self.screen, COLORS['black'], self.buttons[name], 2)
            
            # 按钮文字
            text = self.font_normal.render(labels[name], True, COLORS['black'])
            self.screen.blit(text, (self.buttons[name].centerx - text.get_width()//2, 
                                   self.buttons[name].centery - text.get_height()//2))
    
    def handle_key_input(self, event):
        """处理键盘输入"""
        if self.active_input == 'time_step':
            if event.key == pygame.K_BACKSPACE:
                # 删除字符
                self.input_text = self.input_text[:-1]
            elif event.key == pygame.K_RETURN:
                # 完成输入，更新配置
                try:
                    value = float(self.input_text)
                    # 限制在合理范围内
                    if 0.1 <= value <= 10.0:
                        self.configs['time_step'] = value
                    self.active_input = None
                    self.input_text = ""
                except ValueError:
                    # 输入无效，恢复原值
                    self.active_input = None
                    self.input_text = ""
            elif event.unicode.isnumeric() or event.unicode == '.':
                # 只允许输入数字和小数点
                if event.unicode == '.' and '.' in self.input_text:
                    return  # 已有小数点，不再添加
                if len(self.input_text) < 5:  # 限制长度
                    self.input_text += event.unicode
    
    def run(self):
        """运行启动界面，返回用户设置的参数"""
        running = True
        result = None
        
        while running:
            # 处理事件
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                    
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    elif event.key == K_RETURN and self.active_input is None:
                        result = self.configs.copy()
                        running = False
                    else:
                        self.handle_key_input(event)
                        
                elif event.type == MOUSEBUTTONDOWN:
                    pos = event.pos
                    
                    # 检查是否点击了输入框
                    if self.buttons['time_input'].collidepoint(pos):
                        self.active_input = 'time_step'
                        self.input_text = str(self.configs['time_step'])
                        continue
                    else:
                        self.active_input = None
                    
                    # 处理地图大小按钮
                    for size in ['small', 'medium', 'large']:
                        if self.buttons[size].collidepoint(pos):
                            self.configs['map_size'] = size
                    
                    # 处理策略按钮
                    for strategy in ['nearest', 'max_demand', 'max_priority', 'genetic', 
                                    'multi_objective', 'battery_management']:
                        if strategy in self.buttons and self.buttons[strategy].collidepoint(pos):
                            self.configs['strategy'] = strategy
                    
                    # 处理时间步长按钮
                    if self.buttons['time_dec'].collidepoint(pos):
                        self.configs['time_step'] = max(0.1, self.configs['time_step'] - 0.1)
                    elif self.buttons['time_inc'].collidepoint(pos):
                        self.configs['time_step'] = min(10.0, self.configs['time_step'] + 0.1)
                    
                    # 处理速度按钮
                    if self.buttons['speed_dec'].collidepoint(pos):
                        self.configs['speed'] = max(1, self.configs['speed'] - 1)
                    elif self.buttons['speed_inc'].collidepoint(pos):
                        self.configs['speed'] = min(10, self.configs['speed'] + 1)
                    
                    # 处理复选框
                    if self.buttons['debug_toggle'].collidepoint(pos):
                        self.configs['debug'] = not self.configs['debug']
                    elif self.buttons['stats_toggle'].collidepoint(pos):
                        self.configs['show_stats'] = not self.configs['show_stats']
                    
                    # 处理开始按钮
                    if self.buttons['start'].collidepoint(pos):
                        result = self.configs.copy()
                        running = False
            
            # 绘制界面
            self.draw()
            
            # 控制帧率
            pygame.time.Clock().tick(60)
        
        return result


# 添加在 main 函数之前

def create_environment(map_size, time_step=1.0):
    """根据地图大小创建环境"""
    config = {
        'small': {
            'park_size': (50, 50),
            'n_robots': 4,
            'n_vehicles': 10,
            'n_batteries': 3,
            'generate_vehicles_probability': 0.1
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
    env = create_environment(current_map_size, current_time_step)
    strategy = TaskStrategy(env, time_step=current_time_step)
    visualizer = ChargingVisualizer(env)
    
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
            # 注意：不要重复调用 env.update()，因为 strategy.update() 已经在内部更新了环境
            
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