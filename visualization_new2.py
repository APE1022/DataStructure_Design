import pygame
from pygame.locals import QUIT, KEYDOWN, K_ESCAPE, K_SPACE, MOUSEBUTTONDOWN
import os

pygame.init()

class ChargingVisualizer:
    def __init__(self, env, cell_size=None, info_height=150, window_width=1024, window_height=768):
        self.env = env
        self.info_height = info_height
        self.width, self.height = env.park_size
        
        # 自动计算 cell_size
        if cell_size is None:
            # 计算可用绘图区域
            available_width = window_width
            available_height = window_height - info_height
            
            # 根据可用空间和网格数量计算合适的 cell_size
            width_cell_size = available_width / self.width
            height_cell_size = available_height / self.height
            
            # 取较小值确保完全显示，并设置最小值
            self.cell_size = max(8, min(width_cell_size, height_cell_size))
        else:
            self.cell_size = cell_size
        
        # 基于计算出的 cell_size 设置屏幕尺寸
        self.screen_width = int(self.width * self.cell_size)
        self.screen_height = int(self.height * self.cell_size) + info_height
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        
        # 尝试多种中文字体
        for font_name in ["hiraginosansgb", "songti", "stheitimedium", "simhei"]:
            try:
                self.font = pygame.font.SysFont(font_name, 14)
                break
            except:
                continue
        else:
            # 如果都失败，使用默认字体
            self.font = pygame.font.SysFont(None, 14)
            
        pygame.display.set_caption("ParkEnv 可视化")
        
        # 交互控制参数
        self.strategy = "genetic"  # 默认策略
        self.step_speed = 10      # 控制速度，数值越大越慢
        self.map_size = "small"   # 默认地图大小
        self.paused = False
        
        # 添加按钮区域
        self.buttons = {
            # 策略按钮
            "nearest": pygame.Rect(20, self.screen_height - 80, 100, 30),
            "max_demand": pygame.Rect(130, self.screen_height - 80, 120, 30),
            "max_priority": pygame.Rect(260, self.screen_height - 80, 120, 30),
            "genetic": pygame.Rect(390, self.screen_height - 80, 100, 30),
            
            # 速度控制按钮
            "speed_up": pygame.Rect(520, self.screen_height - 80, 80, 30),
            "speed_down": pygame.Rect(610, self.screen_height - 80, 80, 30),
            
            # 地图大小按钮
            "small": pygame.Rect(20, self.screen_height - 40, 80, 30),
            "medium": pygame.Rect(110, self.screen_height - 40, 80, 30),
            "large": pygame.Rect(200, self.screen_height - 40, 80, 30),
            "restart": pygame.Rect(290, self.screen_height - 40, 80, 30),
        }

    def draw_grid(self):
        for x in range(self.width + 1):
            pygame.draw.line(self.screen, (200, 200, 200), 
                           (x * self.cell_size, 0), 
                           (x * self.cell_size, self.height * self.cell_size))
        for y in range(self.height + 1):
            pygame.draw.line(self.screen, (200, 200, 200), 
                           (0, y * self.cell_size), 
                           (self.width * self.cell_size, y * self.cell_size))

    def draw_robots(self):
        for robot in self.env.robots:
            x, y = int(robot.x * self.cell_size), int(robot.y * self.cell_size)
            if getattr(robot, "charging_at_home", False):
                color = (0, 255, 0)
            elif getattr(robot, "in_action", False) and getattr(robot, "target_vehicle", None):
                color = (0, 0, 255)
            else:
                color = (255, 0, 0)
            pygame.draw.circle(self.screen, color, (x, y), max(5, self.cell_size // 2))
            txt = self.font.render(f"R{getattr(robot, 'id', '?')}:{getattr(robot, 'battery_level', 0):.0f}%", True, (0, 0, 0))
            self.screen.blit(txt, (x - 20, y + self.cell_size // 2))

    def draw_legend(self):
        # 图例区域右下角
        legend_x = self.screen_width - 180  # 距右边180像素
        legend_y = self.screen_height - 130  # 调整位置，避免与控制面板重叠
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
            if getattr(vehicle, "serviced", False):
                color = (0, 255, 0)
            elif getattr(vehicle, "remaining_battery", 100) < getattr(vehicle, "required_battery", 100) * 0.3:
                color = (255, 0, 0)
            else:
                color = (255, 255, 0)
            size = max(5, int(self.cell_size * 0.4))
            pygame.draw.rect(self.screen, color, (x - size // 2, y - size // 2, size, size))
            txt = self.font.render(f"C{getattr(vehicle, 'id', '?')}:{getattr(vehicle, 'remaining_battery', 0):.0f}", True, (0, 0, 0))
            self.screen.blit(txt, (x - 20, y - 25))

    def draw_battery_station(self):
        if hasattr(self.env, "battery_station"):
            # 电池站本体
            x, y = self.width // 2, self.height // 2
            px, py = x * self.cell_size, y * self.cell_size
            pygame.draw.rect(self.screen, (100, 255, 100), (px - self.cell_size, py - self.cell_size, self.cell_size * 2, self.cell_size * 2), 2)

            # 电池信息（右上角）
            battery_status = self.env.battery_station.get_status()
            max_soc = self.env.battery_station.get_maxsoc()
            icon_x = self.screen_width - 160
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

    def draw_robot_battery_info(self):
        # 左上角显示机器人电量
        icon_x = 20
        icon_y = 20
        icon_w, icon_h = 30, 14
        gap = 10

        self.screen.blit(self.font.render("机器人电量", True, (0, 100, 200)), (icon_x, icon_y - 20))
        
        # 计算平均电量和最低电量
        batteries = [getattr(robot, "battery_level", 0) for robot in self.env.robots]
        avg_battery = sum(batteries) / len(batteries) if batteries else 0
        min_battery = min(batteries) if batteries else 0
        
        # 显示统计信息
        self.screen.blit(self.font.render(f"平均: {avg_battery:.1f}% 最低: {min_battery:.1f}%", 
                                        True, (0, 0, 0)), (icon_x, icon_y))
        
        # 显示各机器人电量
        for i, robot in enumerate(self.env.robots):
            if i >= 10:  # 最多显示10个机器人，避免界面过于拥挤
                break
                
            soc_val = getattr(robot, "battery_level", 0)
            # 电池外框
            rect = pygame.Rect(icon_x, icon_y + (i+1) * (icon_h + gap), icon_w, icon_h)
            pygame.draw.rect(self.screen, (50, 50, 50), rect, 2)
            # 电池头
            pygame.draw.rect(self.screen, (50, 50, 50), 
                           (icon_x + icon_w, icon_y + (i+1) * (icon_h + gap) + icon_h // 4, 4, icon_h // 2))
            # 电量条
            fill_w = int((icon_w - 4) * soc_val / 100)
            if soc_val > 60:
                fill_color = (80, 200, 80)
            elif soc_val > 30:
                fill_color = (255, 200, 40)
            else:
                fill_color = (220, 60, 60)
            pygame.draw.rect(self.screen, fill_color, 
                           (icon_x + 2, icon_y + (i+1) * (icon_h + gap) + 2, fill_w, icon_h - 4))
            # 百分比文字和编号
            soc_text = self.font.render(f"R{getattr(robot, 'id', '?')}:{soc_val:.0f}%", True, (0, 0, 0))
            self.screen.blit(soc_text, (icon_x + icon_w + 10, icon_y + (i+1) * (icon_h + gap)))

    def draw_info(self, step):
        info_y = self.height * self.cell_size + 10
        
        # 计算统计信息
        served = len([v for v in self.env.charging_vehicles if getattr(v, "serviced", False)])
        total = len(self.env.charging_vehicles) + len(self.env.needcharge_vehicles)
        waiting = len(self.env.needcharge_vehicles)
        completed = len(getattr(self.env, "completed_vehicles", []))
        
        lines = [
            f"步数: {step}",
            f"机器人: {len(self.env.robots)}",
            f"待充电车辆: {waiting}",
            f"正在充电: {len(self.env.charging_vehicles)}",
            f"已完成: {completed}",
            f"服务率: {served/(total if total > 0 else 1)*100:.1f}%",
            f"当前策略: {self.strategy}"
        ]
        
        for i, line in enumerate(lines):
            txt = self.font.render(line, True, (0, 0, 0))
            self.screen.blit(txt, (10, info_y + i * 20))

    def draw_control_panel(self):
        # 绘制控制面板背景
        pygame.draw.rect(self.screen, (200, 200, 200), 
                        (10, self.screen_height - 90, self.screen_width - 20, 80))
        
        # 绘制策略按钮组
        pygame.draw.rect(self.screen, (220, 220, 220), 
                        (15, self.screen_height - 85, 480, 35))
        self.screen.blit(self.font.render("调度策略:", True, (0, 0, 0)), 
                        (20, self.screen_height - 85))
        
        # 绘制地图尺寸按钮组
        pygame.draw.rect(self.screen, (220, 220, 220), 
                        (15, self.screen_height - 45, 360, 35))
        self.screen.blit(self.font.render("地图尺寸:", True, (0, 0, 0)), 
                        (20, self.screen_height - 45))
        
        # 绘制所有按钮
        for name, rect in self.buttons.items():
            # 当前选中的按钮高亮显示
            if (name == self.strategy and name in ["nearest", "max_demand", "max_priority", "genetic"]) or \
               (name == self.map_size and name in ["small", "medium", "large"]):
                color = (100, 200, 100)
            elif name == "restart":
                color = (200, 100, 100)  # 重启按钮显示红色
            else:
                color = (150, 150, 150)
            
            pygame.draw.rect(self.screen, color, rect)
            
            # 按钮文字
            button_labels = {
                "nearest": "最近任务",
                "max_demand": "最大需求",
                "max_priority": "最大优先级",
                "genetic": "遗传算法",
                "speed_up": "加速",
                "speed_down": "减速",
                "small": "小地图",
                "medium": "中地图",
                "large": "大地图",
                "restart": "重启",
            }
            
            txt = self.font.render(button_labels.get(name, name), True, (0, 0, 0))
            self.screen.blit(txt, (rect.x + 5, rect.y + 5))
        
        # 显示当前速度
        speed_txt = self.font.render(f"当前速度: {11-self.step_speed}", True, (0, 0, 0))
        self.screen.blit(speed_txt, (700, self.screen_height - 65))

    def handle_mouse_click(self, pos):
        # 处理鼠标点击事件
        for name, rect in self.buttons.items():
            if rect.collidepoint(pos):
                if name in ["nearest", "max_demand", "max_priority", "genetic"]:
                    self.strategy = name
                    return {"type": "strategy", "value": name}
                    
                elif name in ["small", "medium", "large"]:
                    self.map_size = name
                    # 不立即重启，等待用户确认
                    return {"type": "map_size", "value": name}
                    
                elif name == "speed_up":
                    self.step_speed = max(1, self.step_speed - 1)
                    
                elif name == "speed_down":
                    self.step_speed = min(20, self.step_speed + 1)
                    
                elif name == "restart":
                    return {"type": "restart", "value": self.map_size}
                
                break
        return None

    def render(self, step=0):
        # 清屏
        self.screen.fill((255, 255, 255))
        
        # 绘制各种元素
        self.draw_grid()
        self.draw_robot_battery_info()
        self.draw_battery_station()
        self.draw_vehicles()
        self.draw_robots()
        self.draw_info(step)
        self.draw_legend()
        
        # 绘制控制面板
        self.draw_control_panel()
        
        # 更新显示
        pygame.display.flip()
        
        # 控制帧率
        pygame.time.delay(self.step_speed * 10)