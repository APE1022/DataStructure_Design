import pygame
import time
from pygame.locals import QUIT, KEYDOWN, K_ESCAPE, K_SPACE
from tqdm import tqdm
import random

# Pygame初始化与字体设置
pygame.init()
try:
    FONT = pygame.font.SysFont("SimHei", 14)  # 支持中文字体
except:
    FONT = pygame.font.Font(None, 14)

class Robot:
    def __init__(self, id, x=0, y=0):
        self.id = id
        self.x = x
        self.y = y
        self.battery_level = 100.0
        self.charging_at_home = False
        self.in_action = False
        self.target_vehicle = None
        self.last_x = x  # 新增：记录上一位置
        self.last_y = y  # 新增：记录上一位置
        self.stuck_count = 0  # 新增：记录停滞次数

class Vehicle:
    def __init__(self, id, x, y):
        self.id = id
        self.x = x
        self.y = y
        self.serviced = False
        self.remaining_battery = random.uniform(20, 80)
        self.required_battery = 100.0

class BatteryStation:
    def __init__(self, max_batteries=3):
        self.max_batteries = max_batteries
        self.batteries = [100.0] * max_batteries  # 初始化电池电量
    
    def get_status(self):
        """获取电池站状态"""
        return [f"{battery:.1f}%" for battery in self.batteries]
    
    def get_maxsoc(self):
        """获取最高电池电量"""
        return max(self.batteries)

class ParkEnv:
    def __init__(self, park_size=(50, 50), n_robots=4, n_vehicles=10, n_batteries=3, time_step=1):
        self.park_size = park_size
        self.time_step = time_step
        self.n_robots = n_robots
        self.n_vehicles = n_vehicles
        
        # 初始化机器人
        self.robots = [Robot(i) for i in range(n_robots)]
        
        # 初始化车辆
        self.needcharge_vehicles = []
        self.charging_vehicles = []
        self.completed_vehicles = []
        self.failed_vehicles = []
        
        # 添加电池站
        self.battery_station = BatteryStation(n_batteries)
        
        self.reset()
        
        # 仿真统计
        self.total_reward = 0
        self.step_count = 0

    def reset(self):
        """重置环境"""
        width, height = self.park_size
        
        # 随机放置机器人
        for robot in self.robots:
            robot.x = random.randint(0, width-1)
            robot.y = random.randint(0, height-1)
            robot.battery_level = 100.0
            robot.charging_at_home = False
            robot.in_action = False
            robot.target_vehicle = None
        
        # 随机生成车辆
        self.needcharge_vehicles = []
        self.charging_vehicles = []
        self.completed_vehicles = []
        self.failed_vehicles = []
        
        for i in range(self.n_vehicles):
            x = random.randint(0, width-1)
            y = random.randint(0, height-1)
            vehicle = Vehicle(i, x, y)
            self.needcharge_vehicles.append(vehicle)
        
        # 重置统计
        self.total_reward = 0
        self.step_count = 0

    def step(self, strategy):
        """环境步进"""
        self.step_count += 1
        
        # 简单模拟机器人移动和充电逻辑
        for robot in self.robots:
            if robot.charging_at_home:
                # 充电中
                robot.battery_level = min(100.0, robot.battery_level + 5.0)
                if robot.battery_level >= 100.0:
                    robot.charging_at_home = False
            elif robot.in_action and robot.target_vehicle:
                # 执行任务 - 向目标车辆移动
                if robot.x < robot.target_vehicle.x:
                    robot.x += 1
                elif robot.x > robot.target_vehicle.x:
                    robot.x -= 1
                elif robot.y < robot.target_vehicle.y:
                    robot.y += 1
                elif robot.y > robot.target_vehicle.y:
                    robot.y -= 1
                else:
                    # 到达目标车辆，开始充电
                    if robot.target_vehicle in self.needcharge_vehicles:
                        self.needcharge_vehicles.remove(robot.target_vehicle)
                        self.charging_vehicles.append(robot.target_vehicle)
                    
                    # 充电逻辑
                    if robot.target_vehicle in self.charging_vehicles:
                        charge_amount = min(10.0, robot.target_vehicle.required_battery - robot.target_vehicle.remaining_battery)
                        robot.target_vehicle.remaining_battery += charge_amount
                        robot.battery_level -= charge_amount * 0.2  # 充电消耗机器人电量
                        
                        # 检查是否充电完成
                        if robot.target_vehicle.remaining_battery >= robot.target_vehicle.required_battery:
                            robot.target_vehicle.serviced = True
                            self.charging_vehicles.remove(robot.target_vehicle)
                            self.completed_vehicles.append(robot.target_vehicle)
                            robot.in_action = False
                            robot.target_vehicle = None
                            self.total_reward += 10  # 完成充电获得奖励
                    
                    # 检查机器人电量是否过低，需要返回充电
                    if robot.battery_level < 20.0 and not robot.charging_at_home:
                        robot.in_action = False
                        robot.target_vehicle = None
                        # 返回到充电站 (0,0)
                        if robot.x != 0 or robot.y != 0:
                            if robot.x > 0:
                                robot.x -= 1
                            elif robot.y > 0:
                                robot.y -= 1
                        else:
                            robot.charging_at_home = True
            
            # 如果没有任务且电量低，返回充电站
            elif not robot.in_action and robot.battery_level < 50.0 and (robot.x != 0 or robot.y != 0):
                if robot.x > 0:
                    robot.x -= 1
                elif robot.y > 0:
                    robot.y -= 1
                if robot.x == 0 and robot.y == 0:
                    robot.charging_at_home = True

        # 简单奖励计算
        self.total_reward -= 0.1  # 每步时间成本
        
        return self.total_reward

class TaskStrategy:
    def __init__(self, env):
        self.env = env
    
    def update(self, time_step, strategy='nearest'):
        """
        按时间步长更新调度与状态
        :param time_step: 步长（秒）
        :param strategy: 'nearest' 或 'max_demand' 或 'max_priority'
        """
        # 先分配任务
        if strategy == 'nearest':
            self.nearest_task()
        elif strategy == 'max_demand':
            self.max_demand_task()
        elif strategy == 'max_priority':
            self.max_priority_task()
        else:
            raise ValueError("Invalid strategy. Choose 'nearest', 'max_demand', or 'max_priority'.")
        self.env.step(strategy)
    
    def nearest_task(self):
        """
        最近任务优先策略：为每个空闲机器人分配距离最近的未服务车辆
        """
        robots = self.env.robots
        needcharge_vehicles = self.env.needcharge_vehicles
        for robot in robots:
            if not robot.in_action and not robot.charging_at_home and robot.battery_level > 30.0 and needcharge_vehicles:
                min_dist = float('inf')
                target_vehicle = None
                for v in needcharge_vehicles:
                    dist = abs(robot.x - v.x) + abs(robot.y - v.y)
                    if dist < min_dist:
                        min_dist = dist
                        target_vehicle = v
                if target_vehicle:
                    robot.in_action = True
                    robot.target_vehicle = target_vehicle
    
    def max_demand_task(self):
        """
        最大任务优先策略：为每个空闲机器人分配电量缺口最大的未服务车辆
        """
        robots = self.env.robots
        needcharge_vehicles = self.env.needcharge_vehicles
        for robot in robots:
            if not robot.in_action and not robot.charging_at_home and robot.battery_level > 30.0 and needcharge_vehicles:
                max_gap = 0
                target_vehicle = None
                for v in needcharge_vehicles:
                    demand = v.required_battery - v.remaining_battery
                    if demand > max_gap:
                        max_gap = demand
                        target_vehicle = v
                if target_vehicle:
                    robot.in_action = True
                    robot.target_vehicle = target_vehicle
    
    def max_priority_task(self):
        """
        最大优先级策略：为每个空闲机器人分配 battery_gap/离开时间 最大的未服务车辆
        注：由于 visualization.py 中无 departure_time 和 env.time，暂时用随机值模拟剩余时间
        """
        import random
        robots = self.env.robots
        needcharge_vehicles = self.env.needcharge_vehicles
        for robot in robots:
            if not robot.in_action and not robot.charging_at_home and robot.battery_level > 30.0 and needcharge_vehicles:
                max_priority = -float('inf')
                target_vehicle = None
                for v in needcharge_vehicles:
                    # 优先级 = 电量缺口 / 剩余离开时间
                    time_left = max(1, random.randint(1, 100))  # 用随机值模拟剩余时间
                    demand = v.required_battery - v.remaining_battery
                    priority = demand / time_left
                    if priority > max_priority:
                        max_priority = priority
                        target_vehicle = v
                if target_vehicle:
                    robot.in_action = True
                    robot.target_vehicle = target_vehicle

class ChargingVisualizer:
    def __init__(self, park_size=(50, 50), info_height=300):
        self.park_size = park_size  # 停车场尺寸 (width, height)
        self.info_height = info_height  # 底部信息栏高度
        self.cell_size = 50  # 单元格默认大小
        self.screen = None
        self.setup_visualization()
        self.show_dropdown = False  # 停车场大小切换下拉菜单状态
        self.possible_sizes = [(50, 50), (100, 100), (200, 200)]  # 可选停车场尺寸
        self.selected_size_index = 0  # 默认小尺寸

    def setup_visualization(self):
        """创建可视化窗口，自适应调整单元格大小"""
        width, height = self.park_size
        # 计算自适应单元格大小（窗口最大宽度1200，高度800）
        max_width, max_height = 1200, 800 - self.info_height
        self.cell_size = min(max_width // width, max_height // height, 25)
        # 创建窗口
        self.screen_width = width * self.cell_size
        self.screen_height = height * self.cell_size + self.info_height
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("充电调度仿真")

    def render_grid(self):
        """绘制停车场网格和充电站"""
        width, height = self.park_size
        # 绘制网格线
        for i in range(width + 1):
            pygame.draw.line(self.screen, (200, 200, 200), 
                            (i*self.cell_size, 0), (i*self.cell_size, height*self.cell_size))
        for j in range(height + 1):
            pygame.draw.line(self.screen, (200, 200, 200), 
                            (0, j*self.cell_size), (width*self.cell_size, j*self.cell_size))
        # 标记充电站（假设原点为充电站位置）
        if FONT and self.cell_size >= 20:
            x, y = (0, 0)  # 充电站默认位于左上角
            pygame.draw.rect(self.screen, (220, 220, 255), 
                            (x*self.cell_size, y*self.cell_size, self.cell_size, self.cell_size), 2)
            self.screen.blit(FONT.render("充电站", True, (0, 0, 200)), 
                            (x*self.cell_size + 5, y*self.cell_size + 5))
        # 标记换电站（位于园区中心）
        station_x, station_y = self.park_size[0] // 2, self.park_size[1] // 2
        if FONT and self.cell_size >= 20:
            pygame.draw.rect(self.screen, (0, 0, 0), 
                            (station_x*self.cell_size, station_y*self.cell_size, self.cell_size, self.cell_size), 2)
            self.screen.blit(FONT.render("换电站", True, (200, 0, 0)), 
                            (station_x*self.cell_size + 5, station_y*self.cell_size + 5))
        # 绘制电池站
        battery_station_x, battery_station_y = int(width / 2), int(height / 2)
        if FONT and self.cell_size >= 20:
            pygame.draw.rect(self.screen, (220, 255, 220), 
                            (battery_station_x*self.cell_size, battery_station_y*self.cell_size, self.cell_size, self.cell_size), 2)
            self.screen.blit(FONT.render("电池站", True, (0, 200, 0)), 
                            (battery_station_x*self.cell_size + 5, battery_station_y*self.cell_size + 5))

    def render_robot(self, robot, cell_size):
        """绘制单个机器人"""
        x = robot.x * cell_size + cell_size // 2
        y = robot.y * cell_size + cell_size // 2
        # 根据状态设置颜色
        if robot.charging_at_home:
            color = (0, 255, 0)  # 鲜绿色：充电中
        elif robot.in_action and robot.target_vehicle:
            color = (0, 0, 255)  # 深蓝色：执行任务
        else:
            color = (255, 0, 0)  # 大红色：待机
        # 绘制圆形主体
        pygame.draw.circle(self.screen, color, (x, y), max(5, int(cell_size * 0.3)))
        # 显示ID和电量
        if FONT:
            text = FONT.render(f"R{robot.id}: {robot.battery_level:.0f}%", True, (0, 0, 0))
            self.screen.blit(text, (x - 25, y - 20))

    def render_vehicle(self, vehicle, cell_size):
        """绘制单个车辆"""
        x = vehicle.x * cell_size + cell_size // 2
        y = vehicle.y * cell_size + cell_size // 2
        # 根据充电状态设置颜色
        if vehicle.serviced:
            color = (0, 255, 0)  # 鲜绿色：已完成
        elif vehicle.remaining_battery < vehicle.required_battery * 0.3:
            color = (255, 0, 0)  # 大红色：电量不足
        else:
            color = (255, 255, 0)  # 明黄色：充电中
        # 绘制矩形主体
        size = max(5, int(cell_size * 0.4))
        pygame.draw.rect(self.screen, color, (x-size//2, y-size//2, size, size))
        # 显示ID和电量信息
        if FONT and cell_size >= 20:
            text = FONT.render(f"C{vehicle.id}: {vehicle.remaining_battery:.0f}/{vehicle.required_battery:.0f}", 
                            True, (0, 0, 0))
            self.screen.blit(text, (x - 40, y - 30))

    def render_info_bar(self, step, reward, completed, strategy):
        """绘制底部信息栏"""
        bg_color = (230, 230, 230)
        # 信息栏区域
        pygame.draw.rect(self.screen, bg_color, (0, self.screen_height - self.info_height, 
                                                self.screen_width, self.info_height))
        # 标题
        if FONT:
            title = FONT.render("充电调度仿真状态", True, (0, 0, 0))
            self.screen.blit(title, (self.screen_width//2 - title.get_width()//2, 
                                    self.screen_height - self.info_height + 20))
            # 关键信息
            self.screen.blit(FONT.render(f"步骤: {step}", True, (0, 0, 0)), (20, self.screen_height - self.info_height + 40))
            self.screen.blit(FONT.render(f"总奖励: {reward:.2f}", True, (0, 0, 0)), (150, self.screen_height - self.info_height + 40))
            self.screen.blit(FONT.render(f"已完成: {len(completed)}", True, (0, 0, 0)), (320, self.screen_height - self.info_height + 40))
            self.screen.blit(FONT.render(f"调度策略: {strategy}", True, (0, 0, 0)), (20, self.screen_height - self.info_height + 60))
            # 退出提示
            self.screen.blit(FONT.render("按ESC键退出", True, (100, 100, 100)), 
                            (self.screen_width - 180, self.screen_height - self.info_height + 80))
            # 暂停提示
            self.screen.blit(FONT.render("按空格键暂停/继续", True, (100, 100, 100)), 
                            (self.screen_width - 180, self.screen_height - self.info_height + 100))
            # 停车场大小切换按钮
            button_x = (self.screen_width - 150) // 2
            button_y = self.screen_height - 50
            pygame.draw.rect(self.screen, (0, 128, 255), (button_x, button_y, 150, 30))
            self.screen.blit(FONT.render(f"停车场大小: {self.park_size}", True, (255, 255, 255)), 
                            (button_x + 10, button_y + 5))
            # 下拉菜单
            if self.show_dropdown:
                for i, size in enumerate(self.possible_sizes):
                    option_y = button_y + (i+1)*30
                    pygame.draw.rect(self.screen, (0, 128, 255), (button_x, option_y, 150, 30))
                    self.screen.blit(FONT.render(str(size), True, (255, 255, 255)), 
                                    (button_x + 10, option_y + 5))

    def render_battery_station(self, env):
        """在换电站位置显示电池信息"""
        battery_status = env.battery_station.get_status()
        max_soc = env.battery_station.get_maxsoc()
        
        # 显示电池站信息
        station_x, station_y = self.park_size[0] // 2, self.park_size[1] // 2
        text_x = station_x * self.cell_size + 5
        text_y = station_y * self.cell_size + self.cell_size + 5
        
        # 显示电池状态
        if FONT:
            status_text = FONT.render(f'电池电量: {", ".join(battery_status)}', True, (0, 0, 0))
            max_text = FONT.render(f'最高电量: {max_soc:.1f}%', True, (0, 0, 0))
            self.screen.blit(status_text, (text_x, text_y))
            self.screen.blit(max_text, (text_x, text_y + 16))

    def render(self, robots, vehicles, step, reward, completed, strategy, env):
        """主渲染函数"""
        if not self.screen:
            return
        # 填充背景
        self.screen.fill((255, 255, 255))
        # 绘制网格和充电站
        self.render_grid()
        # 绘制所有车辆和机器人
        cell_size = self.cell_size
        for vehicle in vehicles:
            self.render_vehicle(vehicle, cell_size)
        for robot in robots:
            if robot.in_action and robot.target_vehicle:
                for vehicle in vehicles:
                    if vehicle == robot.target_vehicle and vehicle.remaining_battery >= vehicle.required_battery:
                        robot.in_action = False
                        robot.target_vehicle = None
            if not robot.charging_at_home and not (robot.in_action and robot.target_vehicle):
                robot.in_action = False
                robot.target_vehicle = None
            self.render_robot(robot, cell_size)
        # 绘制电池站信息
        self.render_battery_station(env)
        # 绘制信息栏
        self.render_info_bar(step, reward, completed, strategy)
        pygame.display.update()  # 更新画面

    def handle_events(self):
        """处理用户交互事件"""
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                pygame.quit()
                exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                # 处理停车场大小切换按钮
                button_x = (self.screen_width - 150) // 2
                button_y = self.screen_height - 50
                if button_x <= x <= button_x+150 and button_y <= y <= button_y+30:
                    self.show_dropdown = not self.show_dropdown
                # 处理下拉菜单选项
                elif self.show_dropdown:
                    for i, size in enumerate(self.possible_sizes):
                        option_y = button_y + (i+1)*30
                        if button_x <= x <= button_x+150 and option_y <= y <= option_y+30:
                            self.selected_size_index = i
                            self.park_size = size
                            self.setup_visualization()  # 重新初始化窗口
                            self.show_dropdown = False


def run_simulation():
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
        park_size = (200, 200)
        n_robots = 40
        n_vehicles = 100
        n_batteries = 30
    else:
        print("输入无效，默认使用small规模")
        park_size = (50, 50)
        n_robots = 4
        n_vehicles = 10
        n_batteries = 4

    env = ParkEnv(park_size=park_size, n_robots=n_robots, n_vehicles=n_vehicles, n_batteries=n_batteries, time_step=1)
    strategy = TaskStrategy(env)

    print("请选择调度策略：nearest（最近任务优先）、max_demand（最大需求优先）、max_priority（最大优先级）")
    strat = input().strip().lower()
    if strat not in ['nearest', 'max_demand', 'max_priority']:
        strat = 'nearest'

    visualizer = ChargingVisualizer(park_size=park_size)
    steps = 10000  # 仿真步数
    paused = False  # 添加暂停标志

    for t in tqdm(range(steps), desc="Simulating"):
        # 统一处理事件
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                pygame.quit()
                return
            elif event.type == KEYDOWN and event.key == K_SPACE:
                paused = not paused
                print(f"仿真已{'暂停' if paused else '继续'}")

        if not paused:
            strategy.update(time_step=env.time_step, strategy=strat)
            visualizer.render(env.robots, env.needcharge_vehicles + env.charging_vehicles + env.completed_vehicles, env.step_count, env.total_reward, env.completed_vehicles, strat, env)
            visualizer.handle_events()
            time.sleep(0.2)

if __name__ == "__main__":
    run_simulation()