"""
电池模块 (Battery Module)
=========================
本模块实现了电池对象的核心功能，用于描述和管理电池的状态、充放电行为及充电功率曲线。

主要功能：
- 电池状态（SOC、电压、容量、是否满电/空电）管理
- 支持电池充电与放电操作
- 提供真实的充电功率曲线模拟
- 支持电池状态的查询与设置

设计说明：
电池对象用于模拟园区内机器人和车辆的电池行为，支持不同电压平台（如400V/800V），并根据SOC动态调整充电功率，贴合实际充电过程。

用法示例：
    battery = Battery(capacity=200, soc=50, voltage=800)
    battery.charge_kwh(10)
    print(battery.get_soc())
    power = battery.get_charging_power()

创建/维护者: 姚炜博
最后修改: 2025-05-23
版本: 1.0.0
"""

class Battery:
    def __init__(self, capacity=100, soc=100, voltage=800, state='full'):
        self.voltage = voltage  # 电池架构，400V或800V
        self.capacity = capacity  # 电池容量kWh
        self.soc = soc   # 当前电量百分比
        self.state = state # full、nonfull

    def set_state(self, state):
        """
        设置电池状态
        state: str, 'full' 或 'nonfull'
        """
        assert state in ['full', 'nonfull'], "Invalid state"
        self.state = state
    
    def charge_kwh(self,kwh):
        """
        充电操作
        kwh: float, 充电量（kWh）
        """
        soc_delta = (kwh / self.capacity) * 100
        self.soc = min(100, self.soc + soc_delta)

    def discharge_kwh(self,kwh):
        """
        放电操作
        kwh: float, 放电量（kWh）
        """
        soc_delta = (kwh / self.capacity) * 100
        self.soc = max(0, self.soc - soc_delta)
    
    def get_charging_power(self):
        """
        更真实的充电功率曲线，参考 charging_curve.py 的逻辑：
        - 低SOC时最大功率
        - 50%-80%逐渐降低
        - 80%以上快速下降
        - 800V系统在高SOC时功率更高
        """
        soc = self.soc  # 当前SOC百分比
        if self.voltage == 800:
            max_power = 350
        else:
            max_power = 150

        # 功率因子随SOC变化
        if soc < 50:
            power_factor = 1.0
        elif soc < 80:
            power_factor = 1.0 - (soc - 50) / 30 * 0.5
        else:
            power_factor = 0.5 - (soc - 80) / 20 * 0.45

        # 800V系统在高SOC时保持更高功率
        if self.voltage == 800 and soc > 50:
            power_factor += 0.15

        power_factor = max(0.05, min(1.0, power_factor))
        return max_power * power_factor /3600

    def is_full(self):
        """
        检查电池是否充满
        return: bool, True if full, False otherwise
        """
        return self.soc == 100

    def is_empty(self):
        """
        检查电池是否空电
        return: bool, True if empty, False otherwise
        """
        return self.soc <= 0

    def get_soc(self):
        """
        获取当前电池SOC
        return: float, 当前电量百分比
        """
        return self.soc
