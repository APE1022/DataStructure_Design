class Battery:
    def __init__(self, capacity=100, soc=100, voltage='800V', state='full'):
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

    def is_full(self):
        return self.soc == 100

    def is_empty(self):
        return self.soc <= 0

    def get_soc(self):
        return self.soc
