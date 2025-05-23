import numpy as np
import random
from models.battery import Battery

"""
车辆模块 (Car Module)
=====================
本模块实现了园区内车辆对象的核心功能，用于描述车辆的基本属性、停车行为、电池状态及充电需求。

主要功能：
- 随机生成车辆的停车位置、离开时间、电池参数
- 管理车辆的电池对象及充电需求
- 跟踪车辆的充电状态、等待时间和离开状态
- 支持车辆状态的更新与变更

设计说明：
车辆对象用于模拟园区内真实车辆的充电行为，结合电池对象，动态反映车辆的电量缺口、充电完成与失败等状态，便于调度系统进行任务分配和性能评估。

用法示例：
    car = Car(id=1, park_size=(100, 100))

创建/维护者: 姚炜博
最后修改: 2025-05-23
版本: 1.0.0
"""

class Car:
    def __init__(self, id, park_size):
        self.id = id  # 车辆编号
        self.departure_time = int(np.clip(np.random.normal(60, 10), 40, 100)) * 60  # 离开时间
        self.parking_spot = (random.randint(0, park_size[0]), random.randint(0, park_size[1]))  # 停车位置 (x, y)
        self.battery = Battery(
            voltage=np.random.choice([400, 800]), # 电池架构：400V或800V
            capacity=np.clip(np.random.normal(90, 10), 65, 115), # 电池容量：65-115kWh，正态分布
            soc=np.clip(np.random.normal(15, 10), 0, 64), # 到达电量：0-64%，正态分布，中心点15
            state='nonfull' 
        )
        self.state = 'needcharge' # 'charging', 'completed', 'needcharge', 'failed'
        self.required_soc = np.clip(np.random.normal(80, 10), 65, 100) # 离开所需电量：70-100%，正态分布
        self.battery_gap = (self.required_soc - self.battery.soc) * self.battery.capacity / 100 # 所需电量
        self.time = 0 # 当前时间
        self.waittime = 0 # 等待时间
        
    def set_state(self, state):
        """
        设置车辆状态
        state: str, 'charging', 'completed', 'needcharge', 'failed'
        """
        assert state in ['charging', 'completed', 'needcharge', 'failed'], "Invalid state"
        self.state = state

    def update(self, step_time=0.1):
        """
        更新逻辑：
        1. 更新当前时间
        2. 更新离开时间
        3. 如果离开时间小于等于0，设置状态为failed
        4. 如果状态为needcharge，累计等待时间
        5. 检查电池是否充满，若是，设置状态为completed
        step_time: float, 时间步长（秒）
        """
        self.time += step_time
        self.departure_time -= step_time
        if (self.departure_time <= 0):
            self.set_state('failed')
        if self.state == 'needcharge':
            self.waittime += step_time
        if self.battery.soc >= self.required_soc:
            self.set_state('completed')


