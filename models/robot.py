from models.battery import Battery
from models.car import Car

"""
机器人模块 (Robot Module)
=========================
本模块实现了园区自动充电机器人的核心功能，用于描述机器人属性、运动、换电行为及与车辆的交互。

主要功能：
- 机器人位置、速度、状态管理
- 支持机器人移动、换电、回库等行为
- 管理机器人携带的电池对象
- 与车辆对象的任务分配与充电协作
- 能耗与换电流程模拟

设计说明：
机器人对象用于模拟园区内自动充电机器人的实际运行过程，支持多种状态切换（如前往车辆、放电、回库、换电等），并与车辆、电池对象紧密协作，实现智能调度与能量管理。

用法示例：
    robot = Robot(id=1, home_x=0, home_y=0)
    robot.assign_task(car)
    robot.update(time_step=1.0)
    print(robot.state, robot.x, robot.y)

创建/维护者: 姚炜博
最后修改: 2025-05-23
版本: 1.0.0
"""

class Robot:
    def __init__(self, id, home_x=0, home_y=0, speed=10, swap_time=120, target: Car = None):
        """
        param：
        id: 机器人编号
        home: 充电站/起点坐标
        speed: 移动速度 m/s
        swap_time: 换电时间（秒），默认2分钟
        battery: 初始携带的电池对象
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
        if self.target is not None:
            if self.target.state == 'completed':
                self.target = None
                self.target_point = None
                self.state = 'available'
            if self.target and self.target.state == 'failed':
                self.target = None
                self.target_point = None
                self.state = 'available'
        if self.battery.soc <= self.cal_distance((self.home_x,self.home_y)) * 100 / (5000 * self.battery.capacity) and self.state == 'discharging':
            self.state = 'gohome'
            self.target_point = (self.home_x,self.home_y)
            self.target.state = 'needcharge'
        elif self.battery.soc <= self.min_soc and self.state == 'available':
            self.state = 'gohome'
            self.target_point = (self.home_x,self.home_y)


        if self.state == 'gocar':
            assert self.target_point is not None, "目标点不能为空"
            self.target_point = (self.target.parking_spot[0], self.target.parking_spot[1])
            self.move_toward_target(self.target_point, time_step)
            if self.check_arrival(self.target_point):
                self.x, self.y = self.target.parking_spot  # 精确对齐
                self.state = 'discharging'
                self.target.set_state('charging')

        elif self.state == 'discharging':
            if self.target.state == 'charging':
                charge_power = self.target.battery.get_charging_power()
                self.battery.discharge_kwh(charge_power * time_step / 0.95) # 充电损耗
                self.target.battery.charge_kwh(charge_power * time_step)
            else:
                self.target = None
                self.target_point = None
                self.state = 'available'
            
        elif self.state == 'gohome':
            self.target = None
            self.target
            self.move_toward_target(self.target_point, time_step)
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


    def move_toward_target(self, targetpoint=None, time_step=0.1):
        """按速度和步长向目标移动，并消耗电量"""
        dx = targetpoint[0] - self.x
        dy = targetpoint[1] - self.y
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
        if self.cal_distance(target_point) < 1:
            return True
        return False

    def assign_task(self, target_vehicle):
        """分配服务车辆任务"""
        self.target = target_vehicle
        self.target_point = (target_vehicle.parking_spot[0], target_vehicle.parking_spot[1])
        self.state = 'gocar'
