import random
import numpy as np
from models.car import Car
from models.robot import Robot
from models.battery import Battery
from models.battery_station import BatteryStation

class ParkEnv:
    """
    园区自动充电机器人调度环境
    """
    def __init__(self, park_size, n_robots, n_vehicles, n_batteries, time_step, generate_vehicles_probability):
        self.park_size = park_size  # 场地大小
        self.n_robots = n_robots  # 最大机器人数量
        self.n_batteries = n_batteries
        self.max_vehicles = n_vehicles # 最大同时在场车辆
        self.n_vehicles = 0 # 在场车辆计数器
        self.generate_vehicles_probability = generate_vehicles_probability  # 车辆生成概率
        # 初始化车辆
        self.vehicles_index = 1
        self.needcharge_vehicles = []
        self.charging_vehicles = []
        self.completed_vehicles = []
        self.failed_vehicles = []
        self.robot_to_car = {}  # 机器人与车辆的映射关系
        self.time = 0  # 当前仿真时间（秒）
        self.time_step = time_step  # 时间步长（秒）

        # 初始化电池站
        self.battery_station = BatteryStation([
            Battery(
                capacity=200,  # 假设固定容量
                soc=100,
                voltage=800,  # 假设800V电池
            ) for _ in range(n_batteries)
        ],location=(park_size[0] / 2, park_size[1] / 2),robotsqueue=[])  # 假设电池站在园区中心

        # 初始化机器人
        self.robots = [
            Robot(
                id=i + 1,
                home_x=park_size[0] / 2,  # 假设机器人从园区中心出发
                home_y=park_size[1] / 2,
                speed=2,
                swap_time=120
            ) for i in range(n_robots)
        ]


    def random_generate_vehicles(self, probability=0.001):
        if random.random() < probability and self.n_vehicles < self.max_vehicles:
            # 离开时间（45~120min，高斯分布）
            stay = int(np.clip(np.random.normal(90, 20), 60, 120)) * 60
            # 停车点
            spot = (random.randint(0, self.park_size[0]), random.randint(0, self.park_size[1]))
            car = Car(
                id=self.vehicles_index,
                departure_time=stay,
                parking_spot=spot,
                )
            self.needcharge_vehicles.append(car)
            self.vehicles_index += 1
            self.n_vehicles += 1
        else:
            pass


    def update(self, time_step):
        """
        主程序逻辑：

        """
        self.time += self.time_step
        # 随机生成车辆
        self.random_generate_vehicles(self.generate_vehicles_probability)

        # 更新所有机器人
        for robot in self.robots:
            if robot.state == 'needswap':
                self.battery_station.robotsqueue.append(robot)
                robot.set_state('swapping')
            robot.update(time_step)

        for car in self.needcharge_vehicles:
            car.update(self.time_step)
            if car.state == 'charging':
                self.charging_vehicles.append(car)
                self.needcharge_vehicles.remove(car)
                # self.n_vehicles -= 1
            elif car.state == 'failed':
                self.failed_vehicles.append(car)
                self.needcharge_vehicles.remove(car)
                self.n_vehicles -= 1

        for car in self.charging_vehicles:
            car.update(self.time_step)
            if car.state == 'completed':
                self.completed_vehicles.append(car)
                self.charging_vehicles.remove(car)
                self.n_vehicles -= 1
            elif car.state == 'failed':
                self.failed_vehicles.append(car)
                self.charging_vehicles.remove(car)
                self.n_vehicles -= 1
            
        # 电池站为所有电池充电
        self.battery_station.update(time_step)
    

    def get_status(self):
        """
        返回当前环境状态
        """
        return {
            "time": self.time,
            "robots": [(r.x, r.y, r.state,r.battery.soc) for r in self.robots],
            "completed_vehicles_num": len(self.completed_vehicles),
            "failed_vehicles_num": len(self.failed_vehicles),
            "needcharge_vehicles_num": len(self.needcharge_vehicles),
            "charging_vehicles_num": len(self.charging_vehicles),
            # "completed_vehicles_num": [(v.parking_spot, v.battery.soc, v.required_soc, v.state) for v in self.completed_vehicles.count()],
            # "needcharge_vehicles_num": [(v.parking_spot, v.battery.soc, v.required_soc, v.state) for v in self.needcharge_vehicles],
            # "charging_vehicles_num": [(v.parking_spot, v.battery.soc, v.required_soc, v.state) for v in self.charging_vehicles],
            "battery_station": self.battery_station.get_status()
        }
    def update_new(self):
        """
        更新环境状态
        """
        # 查找字典，让