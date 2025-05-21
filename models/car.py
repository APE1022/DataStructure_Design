import numpy as np
import random
from models.battery import Battery

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
        # 离开所需电量：70-100%，正态分布
        self.required_soc = np.clip(np.random.normal(80, 10), 65, 100)
        # 所需电量
        self.battery_gap = (self.required_soc - self.battery.soc) * self.battery.capacity / 100
        self.static_battery_gap = self.battery_gap 
        self.time = 0
        self.waittime = 0
        self.static_battery_gap = 0

        
    def set_state(self, state):
        assert state in ['charging', 'completed', 'needcharge', 'failed'], "Invalid state"
        self.state = state

    def update(self, step_time=0.1):
        '''
        更新逻辑：
        1. 更新当前时间
        2. 更新离开时间
        3. 如果离开时间小于等于0，设置状态为failed
        4. 如果状态为needcharge，更新等待时间
        5. 检查电池是否充满
        6. 其他状态下不更新电池状态
        '''
        self.time += step_time
        self.departure_time -= step_time
        if (self.departure_time <= 0):
            self.set_state('failed')
        if self.state == 'needcharge':
            self.waittime += step_time
        if self.battery.soc >= self.required_soc:
            self.set_state('completed')


