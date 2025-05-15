from models.battery import Battery

class BatteryStation:
    def __init__(self, batteries, robotsqueue):
        """
        batteries: List[Battery]，初始化电池站拥有的电池列表
        """
        self.batteries = batteries  # 电池池
        self.location = None  # 电池站位置
        self.robotsqueue = robotsqueue  # 机器人队列

    def receive_battery(self, battery):
        """
        收入机器人换下来的电池
        :param battery: Battery
        """
        self.batteries.append(battery)

    def get_status(self):
        """
        返回当前电池站所有电池的电量列表
        """
        return [b.level for b in self.batteries]
    
    def get_maxsoc_battery(self):
        """
        返回电池站内电量最多的电池
        :return: Battery
        """
        if not self.batteries:
            return None
        return max(self.batteries, key=lambda b: b.soc)

    def update(self, time_step):
        """
        按时间步长更新电池站内所有电池的状态（如充电）
        :param time_step: 步长（秒）
        """
        for robot in self.robotsqueue:
            if robot.state == 'needswap':
                battery = self.get_maxsoc_battery()
                if battery.soc > robot.battery.soc:
                    # 机器人需要换电，提供电池
                    self.receive_battery(robot.battery)
                    robot.battery = battery
                    robot.state = 'swapping'
                    self.batteries.remove(battery)
            if robot.state == 'needswap':
                if robot.swap_timer >= robot.swap_time:
                    # 换电完成
                    robot.state = 'idle'
                    robot.swap_timer = 0
                else:
                    # 继续换电
                    robot.swap_timer += time_step
 
        for battery in self.batteries:
            # 只对空闲或充电状态的电池进行充电
            if battery.state == 'nonfull':
                self.charging(battery)
                if battery.is_full():
                    battery.set_state('full')

    def charging(self,battery:Battery = None):
        battery.charge(0.1)