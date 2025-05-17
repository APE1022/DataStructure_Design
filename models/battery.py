class Battery:
    def __init__(self, capacity=100, soc=100, voltage=800, state='full'):
        self.voltage = voltage  # 电池架构，400V或800V
        self.capacity = capacity  # 电池容量kWh
        self.soc = soc   # 当前电量百分比
        self.state = state # full、nonfull

    def set_state(self, state):
        assert state in ['full', 'nonfull'], "Invalid state"
        self.state = state
    
    def charge_kwh(self,kwh):
        soc_delta = (kwh / self.capacity) * 100
        self.soc = min(100, self.soc + soc_delta)

    def discharge_kwh(self,kwh):
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
        return self.soc == 100

    def is_empty(self):
        return self.soc <= 0

    def get_soc(self):
        return self.soc
