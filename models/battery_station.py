from models.battery import Battery

class BatteryStation:
    def __init__(self, batteries, location, robotsqueue):
        """
        batteries: List[Battery]，初始化电池站拥有的电池列表
        """
        self.batteries = batteries  # 电池池
        self.location = location  # 电池站位置
        self.robotsqueue = robotsqueue  # 机器人队列

    def receive_battery(self, battery):
        """
        收入机器人换下来的电池
        :param battery: Battery
        """
        battery.set_state('nonfull')
        self.batteries.append(battery)

    def get_status(self):
        """
        返回当前电池站所有电池的电量列表
        """
        return [b.soc for b in self.batteries]

    def get_maxsoc(self):
        """
        返回电池站内电量最多的电池的电量
        :return: 电量百分比
        """
        if not self.batteries:
            return None
        return max(self.batteries, key=lambda b: b.soc).soc
    
    def get_maxsoc_battery(self):
        """
        返回电池站内电量最多的电池
        :return: Battery
        """
        if not self.batteries:
            return None
        battery_out = max(self.batteries, key=lambda b: b.soc)
        battery_out.set_state('nonfull')
        self.batteries.remove(battery_out)
        return battery_out

    def update(self, time_step):
        """
        按时间步长更新电池站内所有电池的状态（如充电）
        :param time_step: 步长（秒）
        """
        for robot in self.robotsqueue:
            if robot.state == 'needswap':
                if self.get_maxsoc() > robot.battery.soc and self.get_maxsoc() > 50:
                    # 机器人需要换电，提供电池
                    self.receive_battery(robot.battery)
                    robot.battery = self.get_maxsoc_battery()
                    robot.state = 'swapping'

            else:
                pass
 
        for battery in self.batteries:
            # 只对空闲或充电状态的电池进行充电
            if battery.state == 'nonfull':
                self.charging(battery,time_step)
                if battery.is_full():
                    battery.set_state('full')
            else:
                pass

    def charging(self,battery:Battery,time_step):
        charging_power  = battery.get_charging_power()
        battery.charge_kwh(charging_power * time_step)