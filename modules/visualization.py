import pygame
from pygame.locals import QUIT, KEYDOWN, K_ESCAPE, K_SPACE, MOUSEBUTTONDOWN, K_RETURN
import sys
pygame.init()

"""
可视化与启动界面模块 (Visualization & StartupScreen Module)
===========================================================
本模块基于 pygame 实现了园区充电调度仿真系统的图形化界面，包含仿真参数设置的启动界面（StartupScreen）和主仿真可视化界面（ChargingVisualizer）。

主要功能：
- 启动界面支持地图大小、调度策略、时间步长、仿真速度、调试模式等参数的可视化选择与输入
- 主仿真界面动态显示机器人、车辆、电池站的状态与分布
- 支持机器人电量、电池站电量、车辆状态等信息的实时展示
- 提供“重新开始”按钮，可在仿真过程中返回初始设置界面
- 支持多种调度策略的可视化切换与参数调整
- 交互友好，支持鼠标点击与键盘输入

设计说明：
本模块采用面向对象设计，StartupScreen 用于仿真参数的初始化选择，ChargingVisualizer 用于仿真过程的动态可视化。界面布局自适应不同地图和信息栏尺寸，支持多平台中文字体显示。

用法示例：
    # 启动参数设置界面
    configs = StartupScreen().run()
    # 创建环境与可视化器
    visualizer = ChargingVisualizer(env, cell_size=cell_size)
    # 主循环中调用 visualizer.render(step, strategy)

创建/维护者: 姚炜博、李喆葳
最后修改: 2025-05-23
版本: 1.0.0
"""

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

# TODO：未检查
class StartupScreen:
    """启动界面类，处理所有参数设置"""
    def __init__(self, screen_width=800, screen_height=700):
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
            'show_stats': False
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
            'hyper_heuristic': pygame.Rect(250, 320, 145, 40),
            'RL': pygame.Rect(405, 320, 145, 40),
            
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
            ['nearest', 'max_demand', 'max_priority', 'genetic', 'hyper_heuristic', 'RL'], 
            self.configs['strategy'],
            {'nearest': '最近任务', 'max_demand': '最大需求', 
             'max_priority': '最高优先级', 'genetic': '遗传算法', 
             'hyper_heuristic': '多目标优化', 'RL': '强化学习'}
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
                                    'hyper_heuristic', 'RL']:
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
    
class ChargingVisualizer:
    def __init__(self, env, cell_size, info_height=200 ,info_width=400):
        self.env = env
        if cell_size is None:
        # 提供一个默认值
            self.cell_size = 10
        else:
            self.cell_size = cell_size
        self.width, self.height = env.park_size
        self.screen_width = self.width * cell_size + info_width
        self.screen_height = self.height * cell_size + info_height
        self.info_height = info_height
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        # MacOS下字体设置: "hiraginosansgb"、"stheitimedium" Windows下字体设置: "SimHei"
        self.font = pygame.font.SysFont("hiraginosansgb", 14)
        pygame.display.set_caption("ParkEnv 可视化")
        self.paused = False
        # 交互控制参数
        self.strategy = "genetic"  # 默认策略
        self.step_speed = 10      # 控制显示速度 (1-20, 越小越快)
        self.map_size = "large"   # 默认地图大小
        self.time_step = 1.0      # 仿真物理时间步长
        self.paused = False
        self.need_restart = False
        self.back_button = pygame.Rect((self.screen_width // 2 - 50), self.height * self.cell_size, 100, 50)  # “重新开始”按钮
    
    def draw_grid(self):
        for x in range(self.width + 1):
            pygame.draw.line(self.screen, (200, 200, 200), (x * self.cell_size, 0), (x * self.cell_size, self.height * self.cell_size))
        for y in range(self.height + 1):
            pygame.draw.line(self.screen, (200, 200, 200), (0, y * self.cell_size), (self.width * self.cell_size, y * self.cell_size))

    # Completed
    def draw_robots(self):
        for robot in self.env.robots:
            x, y = int(robot.x * self.cell_size), int(robot.y * self.cell_size)
            state = getattr(robot, "state")
            # 根据状态设置颜色
            if state == 'available':
                color = (0, 255, 0)  # 绿色 - 空闲
            elif state == 'discharging':
                color = (255, 0, 0)  # 红色 - 充电中
            elif state == 'swapping':
                color = (255, 255, 0)  # 黄色 - 交换电池中
            else:
                color = (0, 0, 255)  # 蓝色 - 其他状态
            pygame.draw.circle(self.screen, color, (x, y), max(5, self.cell_size // 2))
            txt = self.font.render(f"R{getattr(robot, 'id', '?')}", True, (0, 0, 0))
            self.screen.blit(txt, (x - self.cell_size, y + self.cell_size // 2))

    def draw_legend(self):
        # 图例区域右下角
        legend_x = self.screen_width - 90  # 距右边180像素
        legend_y = self.screen_height - 180  # 距下边90像素
        spacing = 35

        # 电池站图标
        pygame.draw.rect(self.screen, (100, 255, 100), (legend_x, legend_y, 24, 24), 2)
        txt = self.font.render("电池站", True, (0, 100, 0))
        self.screen.blit(txt, (legend_x + 30, legend_y + 2))

        # 机器人图标
        pygame.draw.circle(self.screen, (0, 0, 255), (legend_x + 12, legend_y + spacing + 12), 12)
        txt = self.font.render("机器人", True, (0, 0, 255))
        self.screen.blit(txt, (legend_x + 30, legend_y + spacing + 2))

        # 车辆图标
        pygame.draw.rect(self.screen, (255, 255, 0), (legend_x, legend_y + 2 * spacing, 24, 24))
        txt = self.font.render("车辆", True, (180, 180, 0))
        self.screen.blit(txt, (legend_x + 30, legend_y + 2 * spacing + 2))

    def draw_vehicles(self):
        for vehicle in self.env.needcharge_vehicles + self.env.charging_vehicles:
            x, y = int(vehicle.parking_spot[0] * self.cell_size), int(vehicle.parking_spot[1] * self.cell_size)
            if getattr(vehicle, "state") == 'charging':
                color = (0, 255, 0) # 绿色 - 充电中
            elif getattr(vehicle, "state") == 'needcharge':
                color = (0, 0, 255) # 蓝色 - 需要充电
            elif getattr(vehicle, "state") == 'failed':
                color = (255, 0, 0) # 红色 - 充电失败
            else:
                color = (255, 255, 0)
            size = max(5, int(self.cell_size * 0.4))
            pygame.draw.rect(self.screen, color, (x - size // 2, y - size // 2, size, size))
            txt = self.font.render(f"C{getattr(vehicle, 'id', '?')}", True, (0, 0, 0))
            self.screen.blit(txt, (x - self.cell_size, y - self.cell_size // 2))

    # TODO: 需要改变显示位置，电池多了可能需要只显示nonfull
    def draw_battery_station(self):
        if hasattr(self.env, "battery_station"):
            # 电池站本体
            x, y = self.width // 2, self.height // 2
            px, py = x * self.cell_size, y * self.cell_size
            pygame.draw.rect(self.screen, (100, 255, 100), (px - self.cell_size, py - self.cell_size, self.cell_size * 2, self.cell_size * 2), 2)

            # 电池信息（右上角）
            battery_status = self.env.battery_station.get_status()
            max_soc = self.env.battery_station.get_maxsoc()
            icon_x = self.screen_width - 120
            icon_y = 20
            icon_w, icon_h = 30, 14
            gap = 10

            self.screen.blit(self.font.render("电池站电池", True, (0, 100, 0)), (icon_x, icon_y - 20))
            for i, soc in enumerate(battery_status):
                # 电池外框
                rect = pygame.Rect(icon_x, icon_y + i * (icon_h + gap), icon_w, icon_h)
                pygame.draw.rect(self.screen, (50, 50, 50), rect, 2)
                # 电池头
                pygame.draw.rect(self.screen, (50, 50, 50), (icon_x + icon_w, icon_y + i * (icon_h + gap) + icon_h // 4, 4, icon_h // 2))
                # 电量条
                try:
                    soc_val = float(soc)
                except:
                    soc_val = float(str(soc).replace('%',''))
                fill_w = int((icon_w - 4) * soc_val / 100)
                # 颜色渐变
                if soc_val > 60:
                    fill_color = (80, 200, 80)
                elif soc_val > 30:
                    fill_color = (255, 200, 40)
                else:
                    fill_color = (220, 60, 60)
                pygame.draw.rect(self.screen, fill_color, (icon_x + 2, icon_y + i * (icon_h + gap) + 2, fill_w, icon_h - 4))
                # 百分比文字
                soc_text = self.font.render(f"{soc_val:.0f}%", True, (0, 0, 0))
                self.screen.blit(soc_text, (icon_x + icon_w + 10, icon_y + i * (icon_h + gap)))

            # 显示最高电量
            max_text = self.font.render(f'最高: {max_soc:.1f}%', True, (0, 0, 0))
            self.screen.blit(max_text, (icon_x, icon_y + len(battery_status) * (icon_h + gap) + 5))

    # Temp Completed，TODO: 需要改变显示位置
    def draw_robot_battery_info(self):
        # 左上角显示机器人电量
        icon_x = self.screen_width - 360
        icon_y = 20
        icon_w, icon_h = 30, 14
        gap = 10

        self.screen.blit(self.font.render("机器人电量", True, (0, 100, 200)), (icon_x, icon_y - 20))
        for i, robot in enumerate(self.env.robots):
            soc_val = robot.battery.soc
            # 电池外框
            rect = pygame.Rect(icon_x, icon_y + i * (icon_h + gap), icon_w, icon_h)
            pygame.draw.rect(self.screen, (50, 50, 50), rect, 2)
            # 电池头
            pygame.draw.rect(self.screen, (50, 50, 50), (icon_x + icon_w, icon_y + i * (icon_h + gap) + icon_h // 4, 4, icon_h // 2))
            # 电量条
            fill_w = int((icon_w - 4) * soc_val / 100)
            if soc_val > 60:
                fill_color = (80, 200, 80)
            elif soc_val > 30:
                fill_color = (255, 200, 40)
            else:
                fill_color = (220, 60, 60)
            pygame.draw.rect(self.screen, fill_color, (icon_x + 2, icon_y + i * (icon_h + gap) + 2, fill_w, icon_h - 4))
            # 百分比文字和编号
            soc_text = self.font.render(f"R{getattr(robot, 'id', '?')}:{soc_val:.0f}% state:{getattr(robot, 'state')}", True, (0, 0, 0))
            self.screen.blit(soc_text, (icon_x + icon_w + 10, icon_y + i * (icon_h + gap)))

    def draw_info(self, step, strategy="nearest"):
        info_y = self.height * self.cell_size + 10
        lines = [
            f"Strategy: {strategy}",
            f"Time: {self.env.time:.1f}s",
            f"TotalVehicles: {self.env.vehicles_index}",
            f"NeedCharge: {len(self.env.needcharge_vehicles)}",
            f"Charging: {len(self.env.charging_vehicles)}",
            f"Completed: {len(self.env.completed_vehicles)}",
            f"Failed: {len(self.env.failed_vehicles)}",
            f"TotalVehicles: {self.env.vehicles_index}",
            # f"TotalReward: {getattr(self.env, 'total_reward', 0):.1f}",
        ]
        for i, line in enumerate(lines):
            txt = self.font.render(line, True, (0, 0, 0))
            self.screen.blit(txt, (10, info_y + i * 20))

    def render(self, step=0, strategy="nearest"):
        self.screen.fill((255, 255, 255))
        self.draw_grid()
        self.draw_robot_battery_info()
        self.draw_battery_station()
        self.draw_vehicles()
        self.draw_robots()
        self.draw_info(step, strategy)
        self.draw_legend()  # 新增图例
        # 绘制重新开始按钮
        pygame.draw.rect(self.screen, (180, 180, 180), self.back_button)
        pygame.draw.rect(self.screen, (0, 0, 0), self.back_button, 2)
        font = pygame.font.SysFont("hiraginosansgb", 18)
        txt = font.render("重新开始", True, (0, 0, 0))
        self.screen.blit(txt, (self.back_button.centerx - txt.get_width()//2, self.back_button.centery - txt.get_height()//2))
        pygame.display.flip()
    
    def handle_mouse_click(self, pos):
        if self.back_button.collidepoint(pos):
            return {"type": "back"}