from models.battery_station import BatteryStation
from models.robot import Robot
from models.car import Car
from models.battery import Battery

class TaskStrategy:
    """
    调度策略类，支持最近任务优先和最大任务优先
    """

    def __init__(self, env):
        self.env = env

    def update(self, time_step, strategy='nearest'):
        """
        按时间步长更新调度与状态
        :param time_step: 步长（秒）
        :param strategy: 'nearest' 或 'max_demand'
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
        self.env.update(time_step)
    
    def nearest_task(self):
        """
        最近任务优先策略：为每个空闲机器人分配距离最近的未服务车辆
        """
        for robot in self.env.robots:
            if robot.state == 'available':

                min_dist = float('inf')
                target_vehicle = None
                for v in self.env.needcharge_vehicles:
                    if v.state == 'needcharge':
                        v.set_state('charging')
                        dist = abs(robot.x - v.parking_spot[0]) + abs(robot.y - v.parking_spot[1])
                        if dist < min_dist:
                            min_dist = dist
                            target_vehicle = v
                if target_vehicle:
                    robot.assign_task(target_vehicle)

    def max_demand_task(self):
        """
        最大任务优先策略：为每个空闲机器人分配电量缺口最大的未服务车辆
        """
        for robot in self.env.robots:
            if robot.state == 'available':
                max_gap = -float('-inf')
                target_vehicle = None
                for v in self.env.needcharge_vehicles:
                    if v.state == 'needcharge':
                        v.set_state('charging')
                        if v.battery_gap > max_gap:
                            max_gap = v.battery_gap
                            target_vehicle = v
                if target_vehicle:
                    robot.assign_task(target_vehicle)

    def max_priority_task(self):
        """
        最大优先级策略：为每个空闲机器人分配 battery_gap/离开时间 最大的未服务车辆
        """
        for robot in self.env.robots:
            if robot.state == 'available':
                max_priority = -float('inf')
                target_vehicle = None
                for v in self.env.needcharge_vehicles:
                    if v.state == 'needcharge':
                        v.set_state('charging')
                        # 优先级 = 电量缺口 / 剩余离开时间
                        time_left = max(1, v.departure_time - self.env.time)  # 防止除0
                        priority = v.battery_gap / time_left
                        if priority > max_priority:
                            max_priority = priority
                            target_vehicle = v
                if target_vehicle:
                    robot.assign_task(target_vehicle)