import pygame
from pygame.locals import QUIT, KEYDOWN, K_ESCAPE, K_SPACE

class ParkEnvVisualizer:
    def __init__(self, env, cell_size=10):
        self.env = env
        self.cell_size = cell_size
        self.width, self.height = env.park_size
        self.screen_width = self.width * cell_size
        self.screen_height = self.height * cell_size + 100  # 额外空间显示信息
        pygame.init()
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("ParkEnv 可视化")
        self.font = pygame.font.SysFont("Arial", 16)
        self.paused = False
    def draw_grid(self):
        for x in range(self.width + 1):
            pygame.draw.line(self.screen, (200, 200, 200), (x * self.cell_size, 0), (x * self.cell_size, self.height * self.cell_size))
        for y in range(self.height + 1):
            pygame.draw.line(self.screen, (200, 200, 200), (0, y * self.cell_size), (self.width * self.cell_size, y * self.cell_size))

    def draw_robots(self):
        for robot in self.env.robots:
            x, y = int(robot.x * self.cell_size), int(robot.y * self.cell_size)
            color = (0, 0, 255) if robot.state == 'available' else (0, 255, 0)
            pygame.draw.circle(self.screen, color, (x, y), self.cell_size // 2)
            txt = self.font.render(f"R{getattr(robot, 'id', '?')}", True, (0, 0, 0))
            self.screen.blit(txt, (x - 10, y - 25))

    def draw_vehicles(self):
        for car in self.env.needcharge_vehicles + self.env.charging_vehicles + self.env.completed_vehicles + self.env.failed_vehicles:
            x, y = int(car.parking_spot[0] * self.cell_size), int(car.parking_spot[1] * self.cell_size)
            if car.state == 'needcharge':
                color = (255, 255, 0)
            elif car.state == 'charging':
                color = (0, 255, 255)
            elif car.state == 'completed':
                color = (0, 200, 0)
            else:
                color = (200, 0, 0)
            pygame.draw.rect(self.screen, color, (x, y, self.cell_size, self.cell_size))
            txt = self.font.render(f"C{getattr(car, 'id', '?')}", True, (0, 0, 0))
            self.screen.blit(txt, (x, y - 18))

    def draw_battery_station(self):
        if hasattr(self.env, "battery_station"):
            x, y = self.width // 2, self.height // 2
            px, py = x * self.cell_size, y * self.cell_size
            pygame.draw.rect(self.screen, (100, 255, 100), (px, py, self.cell_size, self.cell_size), 2)
            txt = self.font.render("电池站", True, (0, 100, 0))
            self.screen.blit(txt, (px, py + self.cell_size))

    def draw_info(self, step):
        info_y = self.height * self.cell_size + 10
        status = self.env.get_status()
        lines = [
            f"Step: {step}",
            f"Robots: {len(self.env.robots)}",
            f"NeedCharge: {len(self.env.needcharge_vehicles)}",
            f"Charging: {len(self.env.charging_vehicles)}",
            f"Completed: {len(self.env.completed_vehicles)}",
            f"Failed: {len(self.env.failed_vehicles)}",
        ]
        for i, line in enumerate(lines):
            txt = self.font.render(line, True, (0, 0, 0))
            self.screen.blit(txt, (10, info_y + i * 20))

    def render(self, step=0):
        self.screen.fill((255, 255, 255))
        self.draw_grid()
        self.draw_battery_station()
        self.draw_vehicles()
        self.draw_robots()
        self.draw_info(step)
        pygame.display.flip()

    def run(self, max_steps=10000, delay=50):
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
                self.env.update(self.env.time_step if hasattr(self.env, "time_step") else 1)
                self.render(step)
                step += 1
            clock.tick(1000 // delay if delay > 0 else 20)

# 用法示例（放在main.py或单独运行本文件）
if __name__ == "__main__":
    from envs import ParkEnv
    from strategy import TaskStrategy
    env = ParkEnv(park_size=(50, 50), n_robots=4, n_vehicles=10, n_batteries=8, time_step=1)
    strategy = TaskStrategy(env, time_step=1)
    visualizer = ParkEnvVisualizer(env, cell_size=12)
    visualizer.run(max_steps=10000, delay=50)