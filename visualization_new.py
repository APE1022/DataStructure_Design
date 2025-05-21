import pygame
from pygame.locals import QUIT, KEYDOWN, K_ESCAPE, K_SPACE

pygame.init()
import os
# print(pygame.font.get_fonts())

class ChargingVisualizer:
    def __init__(self, env, cell_size=12, info_height=100):
        self.env = env
        self.cell_size = cell_size
        self.width, self.height = env.park_size
        self.screen_width = self.width * cell_size
        self.screen_height = self.height * cell_size + info_height
        self.info_height = info_height
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        # MacOS下字体设置: "hiraginosansgb"、"stheitimedium" Windows下字体设置: "SimHei"
        self.font = pygame.font.SysFont("hiraginosansgb", 14)
        pygame.display.set_caption("ParkEnv 可视化")
        self.paused = False

    def draw_grid(self):
        for x in range(self.width + 1):
            pygame.draw.line(self.screen, (200, 200, 200), (x * self.cell_size, 0), (x * self.cell_size, self.height * self.cell_size))
        for y in range(self.height + 1):
            pygame.draw.line(self.screen, (200, 200, 200), (0, y * self.cell_size), (self.width * self.cell_size, y * self.cell_size))

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
        legend_y = self.screen_height - 90  # 距下边90像素
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
            gap = 40

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
            soc_text = self.font.render(f"R{getattr(robot, 'id', '?')}:{soc_val:.0f}%", True, (0, 0, 0))
            self.screen.blit(soc_text, (icon_x + icon_w + 10, icon_y + i * (icon_h + gap)))

    def draw_info(self, step, strategy="nearest"):
        info_y = self.height * self.cell_size + 10
        lines = [
            f"Step: {step}",
            f"Robots: {len(self.env.robots)}",
            f"NeedCharge: {len(self.env.needcharge_vehicles)}",
            f"Charging: {len(self.env.charging_vehicles)}",
            f"Completed: {len(self.env.completed_vehicles)}",
            f"TotalReward: {getattr(self.env, 'total_reward', 0):.1f}",
            f"Strategy: {strategy}"
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
        pygame.display.flip()

    def run(self, max_steps=10000, delay=2, strategy="nearest", task_strategy=None):
        step = 0
        clock = pygame.time.Clock()
        while step < max_steps:
            for event in pygame.event.get():
                if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                    pygame.quit()
                    return
                elif event.type == KEYDOWN and event.key == K_SPACE:
                    self.paused = not self.paused
            if not self.paused:
                if task_strategy:
                    task_strategy.update(time_step=self.env.time_step, strategy=strategy)
                else:
                    self.env.step(strategy)
                self.render(step, strategy)
                step += 1
                if delay > 0:
                    clock.tick(int(1 / delay))