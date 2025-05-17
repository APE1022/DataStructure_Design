from models.battery import Battery
from models.car import Car

class Robot:
    def __init__(self, id, home_x=0, home_y=0, speed=10, swap_time=120, target: Car = None):
        """
        :param id: 机器人编号
        :param home: 充电站/起点坐标
        :param speed: 移动速度 m/s
        :param swap_time: 换电时间（秒），默认2分钟
        :param battery: 初始携带的电池对象
        """
        self.id = id # 机器人编号
        self.x = home_x  # 当前位置
        self.y = home_y
        self.home_x = home_x
        self.home_y = home_y
        self.speed = speed
        self.swap_time = swap_time
        self.battery = Battery(
            voltage=800, # 电池架构：800V
            capacity=200, # 电池容量：200kWh
            soc=100, # 初始电量：100%
            state='full' # 状态: full、nonfull
        )
        self.state = 'available'  # available, gocar, swapping, needswap, discharging, gohome
        self.target = target  # 目标车辆
        self.target_point = None  # 目标车辆停车点
        self.swap_timer = 0  # 换电计时
        self.min_soc = 15 # self.cal_distance() * 100 / (5000 * self.battery.capacity)

    def set_state(self, state):
        assert state in ['gocar', 'discharging', 'available', 'swapping', 'gohome','needswap'], "Invalid state"
        self.state = state

    def update(self, time_step):
        """按步长更新机器人状态"""
        if self.state == 'gocar' and self.target is not None:
            self.move_toward_target(self.target, time_step)
            if self.check_arrival(self.target_point):
                self.x, self.y = self.target.parking_spot  # 精确对齐
                self.state = 'discharging'
            if self.battery.soc <= self.min_soc:
                self.state = 'gohome'

        elif self.state == 'discharging':
            charge_power = self.target.battery.get_charging_power()
            self.battery.discharge_kwh(charge_power * time_step / 0.95) # 充电损耗
            self.target.battery.charge_kwh(charge_power * time_step)
            if self.target.battery.soc >= self.target.required_soc:
                self.target.set_state('completed')
                self.target = None
                self.target_point = None
                if self.battery.soc <= self.min_soc:
                    self.state = 'gohome'
                else:
                    self.state = 'available'

        elif self.state == 'gohome':
            self.go_home(time_step)
            if self.check_arrival((self.home_x,self.home_y)): 
                self.x, self.y = self.home_x, self.home_y
                self.state = 'needswap'
                self.target = None
                self.target_point = None
                self.battery.set_state('nonfull')
        
        elif self.state == 'swapping':
            self.swap_timer += time_step
            if self.swap_timer >= self.swap_time:
                self.state = 'available'
                self.swap_timer = 0

        else:
            pass

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
                self.battery.discharge_kwh(move_dist  / 5000)
    

    def cal_distance(self,target_point):
        dx = target_point[0] - self.x
        dy = target_point[1] - self.y
        distance = (dx ** 2 + dy ** 2) ** 0.5
        return distance

        
    def check_arrival(self, target_point):
        """检查是否到达目标"""
        if self.cal_distance(target_point) < self.speed * 1:
            return True
        return False

    def assign_task(self, target_vehicle):
        """分配服务车辆任务"""
        self.target = target_vehicle
        self.target_point = (target_vehicle.parking_spot[0], target_vehicle.parking_spot[1])
        self.state = 'gocar'

    def go_home(self,time_step):
        """回到充电站"""
        dx = self.home_x - self.x
        dy = self.home_y - self.y
        distance = (dx ** 2 + dy ** 2) ** 0.5
        move_dist = min(self.speed * time_step, distance)
        if distance > 0:
            self.x += dx / distance * move_dist
            self.y += dy / distance * move_dist
            # 假设每千米消耗0.2度电
            if self.battery:
                self.battery.discharge_kwh(move_dist  / 5000)
