from models.battery import Battery

"""
电池站模块(Battery Station Module)
====================================
本模块实现了电池交换站的核心功能，用于管理和分配电池资源，为充电机器人提供电池更换与充电服务。

主要功能：
- 维护电池库存池，管理电池状态
- 提供机器人电池交换服务
- 电池充电管理与状态更新
- 机器人换电队列管理

设计说明：
电池站作为集中式资源节点，协调多个机器人的电池需求，通过优先分配高电量电池，实现资源优化利用。

用法示例：
    station = BatteryStation(
        batteries=[Battery(capacity=200, soc=100) for _ in range(5)],
        location=(50, 50),
        robotsqueue=[]
    )

创建/维护者: 姚炜博
最后修改: 2025-05-23
版本: 1.0.0
"""

class BatteryStation:
    def __init__(self, batteries, location, robotsqueue):
        """
        batteries: List[Battery]，初始化电池站拥有的电池列表
        location: Tuple[float, float]，电池站位置坐标
        robotsqueue: List[Robot]，换电机器人队列
        """
        self.batteries = batteries  # 电池池
        self.location = location  # 电池站位置
        self.robotsqueue = robotsqueue  # 换电机器人队列

    def receive_battery(self, battery):
        """
        收入机器人换下来的电池
        battery: Battery 对象
        """
        battery.set_state('nonfull')
        self.batteries.append(battery)

    def get_status(self):
        """
        返回当前电池站所有电池的电量列表
        return: List[float]，电池电量列表
        """
        return [b.soc for b in self.batteries]

    def get_maxsoc(self):
        """
        返回电池站内电量最多的电池的电量
        return: float, 电池电量
        """
        if not self.batteries:
            return None
        return max(self.batteries, key=lambda b: b.soc).soc
    
    def get_maxsoc_battery(self):
        """
        返回电池站内电量最多的电池
        return: Battery
        """
        if not self.batteries:
            return None
        battery_out = max(self.batteries, key=lambda b: b.soc)
        # battery_out.set_state('nonfull')
        self.batteries.remove(battery_out)
        return battery_out

    def update(self, time_step):
        """
        按时间步长更新电池站内所有电池的状态, 并给机器人换电
        time_step: 步长（秒）
        """
        for robot in self.robotsqueue:
            # 机器人需要换电，提供电池
            if robot.state == 'needswap':
                if self.get_maxsoc() > robot.battery.soc and self.get_maxsoc() > 50:
                    self.receive_battery(robot.battery)
                    robot.battery = self.get_maxsoc_battery()
                    robot.state = 'swapping'
            else:
                pass
 
        for battery in self.batteries:
            # 只对未满的电池进行充电
            if battery.state == 'nonfull':
                self.__charging(battery,time_step)
                if battery.is_full():
                    battery.set_state('full')
            else:
                pass

    def __charging(self,battery:Battery,time_step):
        """
        私有方法: 给电池充电, 充电功率参考充电曲线
        battery: Battery 对象
        time_step: 步长（秒）
        """
        charging_power  = battery.get_charging_power()
        battery.charge_kwh(charging_power * time_step)