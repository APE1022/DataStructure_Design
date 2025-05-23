import random
import numpy as np
from models.car import Car
from models.robot import Robot
from models.battery import Battery
from models.battery_station import BatteryStation

"""
园区充电调度环境模块 (ParkEnv Module)
====================================
本模块实现了园区自动充电机器人调度的核心环境类 ParkEnv，负责管理机器人、车辆、电池站等对象，并提供环境状态的更新与查询接口。

主要功能：
- 初始化园区环境，包括机器人、电池站、车辆等对象的创建与管理
- 支持车辆的随机生成与状态转移（待充电、充电中、完成、失败等）
- 管理机器人与车辆的任务分配、状态更新与交互
- 电池站的充电与换电流程模拟
- 提供环境状态的查询接口，便于与调度策略、强化学习等模块集成

设计说明：
本模块采用面向对象设计，所有实体对象（机器人、车辆、电池站）均为独立类，环境负责统一调度和状态管理。支持灵活扩展不同规模和复杂度的仿真场景，便于与可视化、策略、智能体等模块协同工作。

用法示例：
    env = ParkEnv(park_size=(100, 100), n_robots=4, n_vehicles=10, n_batteries=3, time_step=1.0, generate_vehicles_probability=0.01)
    env.update(time_step=1.0)
    status = env.get_status()

创建/维护者: 姚炜博
最后修改: 2025-05-23
版本: 1.0.0
"""

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
        self.generate_vehicles_probability = generate_vehicles_probability * time_step # 车辆生成概率
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
                speed=10,
                swap_time=120
            ) for i in range(n_robots)
        ]


    def random_generate_vehicles(self, probability=0.001):
        if random.random() < probability and self.n_vehicles < self.max_vehicles:
            # 离开时间（45~120min，高斯分布）
            car = Car(id=self.vehicles_index, park_size=self.park_size)
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
        for robot in self.robots[:]:
            if robot.state == 'needswap':
                self.battery_station.robotsqueue.append(robot)
                robot.set_state('swapping')
            robot.update(time_step)

        for car in self.needcharge_vehicles[:]:
            car.update(self.time_step)
            if car.state == 'charging':
                self.charging_vehicles.append(car)
                self.needcharge_vehicles.remove(car)
            elif car.state == 'failed':
                self.failed_vehicles.append(car)
                self.needcharge_vehicles.remove(car)
                self.n_vehicles -= 1
        
        for car in self.charging_vehicles[:]:
            car.update(self.time_step)
            if car.state == 'completed':
                self.completed_vehicles.append(car)
                self.charging_vehicles.remove(car)
                self.n_vehicles -= 1
            elif car.state == 'failed':
                self.failed_vehicles.append(car)
                self.charging_vehicles.remove(car)
                self.n_vehicles -= 1
            elif car.state == 'needcharge':
                self.needcharge_vehicles.append(car)
                self.charging_vehicles.remove(car)
            
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