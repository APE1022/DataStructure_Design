from models.battery import Battery
from models.car import Car

class Robot:
    def __init__(self, id, home=(0, 0), speed=10, swap_time=120, target: Car = None):
        """
        :param id: 机器人编号
        :param home: 充电站/起点坐标
        :param speed: 移动速度 m/s
        :param swap_time: 换电时间（秒），默认2分钟
        :param battery: 初始携带的电池对象
        """
        self.id = id # 机器人编号
        self.x, self.y = home  # 当前位置
        self.home = home
        self.speed = speed
        self.swap_time = swap_time
        self.battery = Battery(
            voltage=800, # 电池架构：800V
            capacity_kwh=200, # 电池容量：200kWh，正态分布
            soc=100, # 初始电量：100%
            state='available' # 状态: 'charging', 'discharging', 'available', 'needswap'
        )
        self.state = 'available'  # available, moving, swapping, charging
        self.target = target  # 目标车辆或目标点
        self.swap_timer = 0  # 换电计时
        self.min_soc = self.cal_distance() * 100 / (5000 * self.battery.capacity)
    def set_state(self, state):
        assert state in ['charging', 'discharging', 'available', 'needcharge'], "Invalid state"
        self.state = state
    def update(self, time_step):
        """按步长更新机器人状态"""
        if self.state == 'moving' and self.target is not None:
            self.move_toward_target(self.target, time_step)
            if self.check_arrival(self.target):
                self.x, self.y = self.target.parking_spot  # 精确对齐
                self.state = 'charging'
            if self.battery.soc <= self.min_soc:
                self.state = 'moving'


        elif self.state == 'swapping':
            self.swap_timer += time_step
            if self.swap_timer >= self.swap_time:
                self.state = 'available'
                self.swap_timer = 0

        elif self.state == 'charging':
            if self.battery:
                self.target.battery.state = 'charging'
                self.battery.state = 'discharging'
                self.battery.update(time_step)
                self.target.battery.update(time_step)
            # 可根据需求判断是否充满自动切换状态

    def move_toward_target(self, target: Car = None, time_step=0.1):
        """按速度和步长向目标移动，并消耗电量"""
        dx = target.parking_spot[0] - self.x
        dy = target.parking_spot[1] - self.y
        distance = (dx ** 2 + dy ** 2) ** 0.5
        move_dist = min(self.speed * time_step, distance)
        if distance > 0:
            self.x += dx / distance * move_dist
            self.y += dy / distance * move_dist
            # 假设每千米消耗0.2度电
            if self.battery:
                self.battery.move_cost(move_dist  / 5000)
    

    def cal_distance(self,target: Car):
        dx = target.parking_spot[0] - self.x
        dy = target.parking_spot[1] - self.y
        distance = (dx ** 2 + dy ** 2) ** 0.5
        return distance

        
    def check_arrival(self, target: Car):
        """检查是否到达目标"""
        if self.cal_distance() < 1e-1:
            return True
        return False

    def update(self, time_step):
        """按步长更新机器人状态"""
        if self.state == 'moving' and self.target is not None:
            self.move_towards(self.target, time_step)
            if (abs(self.x - self.target[0]) < 1e-2) and (abs(self.y - self.target[1]) < 1e-2):
                self.x, self.y = self.target  # 精确对齐
                self.state = 'available'
        elif self.state == 'swapping':
            self.swap_timer += time_step
            if self.swap_timer >= self.swap_time:
                self.state = 'available'
        elif self.state == 'charging':
            if self.battery:
                self.battery.state = 'charging'
                self.battery.update(time_step)
            # 可根据需求判断是否充满自动切换状态
        else:
            pass

    def assign_task(self, target_vehicle):
        """分配服务车辆任务"""
        self.target_vehicle = target_vehicle
        self.target = (target_vehicle.x, target_vehicle.y)
        self.state = 'moving'
        self.in_action = True

    def go_home(self):
        """回到充电站"""
        self.target = self.home
        self.state = 'moving'
        self.in_action = True
