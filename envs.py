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
    def __init__(self, park_size=(100, 100), n_robots=4, n_vehicles=10, n_batteries=3):
        self.park_size = park_size  # 场地大小
        self.max_robots = n_robots  # 最大机器人数量
        self.max_vehicles = n_vehicles
        self.n_robots = 0
        self.n_vehicles = 0
        self.n_batteries = n_batteries

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
                home_x=park_size[0],  # 假设机器人从园区中心出发
                home_y=park_size[1],
                speed=10,
                swap_time=120
            ) for i in range(n_robots)
        ]

        # 初始化车辆
        self.vehicles_index = 1
        self.needcharge_vehicles = []
        self.charging_vehicles = []
        self.completed_vehicles = []
        self.failed_vehicles = []

        self.time = 0  # 当前仿真时间（秒）
        self.time_step = 0.1  # 时间步长（秒）

    def random_generate_vehicles(self, index):
        if random.random() < 0.01 and self.n_vehicles < self.max_vehicles:
            # 到达时间
            arrival = random.randint(0, 600)
            # 离开时间（45~120min，高斯分布）
            stay = int(np.clip(np.random.normal(90, 20), 45, 120))
            departure = arrival + stay
            # 停车点
            spot = (random.randint(0, self.park_size[0]), random.randint(0, self.park_size[1]))
            # 电池架构
            voltage = random.choice([400, 800])
            # 电池容量
            capacity_kwh = np.clip(np.random.normal(90, 10), 65, 115)
            # 到达电量
            remaining = np.random.uniform(5, 50)
            # 离开所需电量
            required = np.clip(np.random.normal(85, 10), 70, 100)
            car = Car(
                id=index,
                arrival_time=arrival,
                departure_time=departure,
                parking_spot=spot,
                )
            self.needcharge_vehicles.append(car)
            index += 1
        else:
            pass


    def update(self, time_step):
        """
        执行一步仿真：更新机器人、车辆、电池站状态
        """
        self.random_generate_vehicles(self.vehicles_index)
        # 更新所有机器人
    
        for robot in self.robots:
            if robot.state == 'needswap':
                self.battery_station.robotsqueue.append(robot)
            robot.update(time_step)
        # 更新所有车辆（如有需要）
        for car in self.needcharge_vehicles:
            car.update(self.time_step)
        for car in self.charging_vehicles:
            car.update(self.time_step)
        # 电池站为所有电池充电
        self.battery_station.update(time_step)
        self.time += self.time_step

    def get_status(self):
        """
        返回当前环境状态
        """
        return {
            "time": self.time,
            "robots": [(r.x, r.y, r.state,r.battery.soc) for r in self.robots],
            "completed_vehicles": [(v.parking_spot, v.battery.soc, v.required_soc, v.state) for v in self.completed_vehicles],
            # "needcharge_vehicles": [(v.parking_spot, v.battery.soc, v.required_soc, v.state) for v in self.needcharge_vehicles],
            # "charging_vehicles": [(v.parking_spot, v.battery.soc, v.required_soc, v.state) for v in self.charging_vehicles],
            "battery_station": self.battery_station.get_status()
        }