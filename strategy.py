def nearest_task_strategy(robots, vehicles):
    """
    最近任务优先策略：为每个空闲机器人分配距离最近的未服务车辆
    :param robots: 机器人列表
    :param vehicles: 车辆列表
    """
    for robot in robots:
        if robot.is_idle():
            min_dist = float('inf')
            target_vehicle = None
            for v in vehicles:
                if not v.serviced:
                    dist = abs(robot.x - v.parking_spot[0]) + abs(robot.y - v.parking_spot[1])
                    if dist < min_dist:
                        min_dist = dist
                        target_vehicle = v
            if target_vehicle:
                robot.assign_task(target_vehicle)

def max_demand_task_strategy(robots, vehicles):
    """
    最大任务优先策略：为每个空闲机器人分配电量缺口最大的未服务车辆
    :param robots: 机器人列表
    :param vehicles: 车辆列表
    """
    for robot in robots:
        if robot.is_idle():
            max_gap = -float('inf')
            target_vehicle = None
            for v in vehicles:
                if not v.serviced:
                    v.calculate_battery_gap()
                    if v.battery_gap > max_gap:
                        max_gap = v.battery_gap
                        target_vehicle = v
            if target_vehicle:
                robot.assign_task(target_vehicle)