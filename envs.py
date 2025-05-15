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
    def __init__(self, park_size=(100, 100), n_robots=4, n_vehicles=10, n_batteries=4):
        self.park_size = park_size  # 场地大小
        self.n_robots = n_robots
        self.n_vehicles = n_vehicles
        self.n_batteries = n_batteries

        # 初始化电池站
        self.battery_station = BatteryStation([
            Battery(
                capacity=100,  # 假设固定容量
                soc=100,
                architecture=random.choice([400, 800])
            ) for _ in range(n_batteries)
        ])

        # 初始化机器人
        self.robots = [
            Robot(
                id=i,
                home=(0, 0),
                speed=10,
                swap_time=120,
                battery=self.battery_station.provide_battery()
            ) for i in range(n_robots)
        ]

        # 初始化车辆
        self.vehicles = self._generate_vehicles(n_vehicles)

        self.time = 0  # 当前仿真时间（秒）
        self.time_step = 0.1  # 时间步长（秒）

    def _generate_vehicles(self, count):
        vehicles = []
        for i in range(count):
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
            vehicles.append(Car(
                id=i,
                arrival_time=arrival,
                departure_time=departure,
                parking_spot=spot,
                remaining_battery=remaining,
                required_soc=required,
                voltage=voltage,
                capacity_kwh=capacity_kwh
            ))
        return vehicles

    def step(self):
        """
        执行一步仿真：更新机器人、车辆、电池站状态
        """
        # 更新所有机器人
        for robot in self.robots:
            robot.update(self.time_step)
        # 更新所有车辆（如有需要）
        # for car in self.vehicles:
        #     car.update(self.time_step)
        # 电池站为所有电池充电
        self.battery_station.update(self.time_step)
        self.time += self.time_step

    def get_status(self):
        """
        返回当前环境状态
        """
        return {
            "time": self.time,
            "robots": [(r.x, r.y, r.state) for r in self.robots],
            "vehicles": [(v.parking_spot, v.remaining_battery, v.required_battery, v.serviced) for v in self.vehicles],
            "battery_station": self.battery_station.get_status()
        }