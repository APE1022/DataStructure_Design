from models.battery_station import BatteryStation
from models.robot import Robot
from models.car import Car
from models.battery import Battery

class TaskStrategy:
    """
    调度策略类，支持最近任务优先和最大任务优先
    """

    def __init__(self, env):
        self.env = env

    def update(self, time_step, strategy='nearest'):
        """
        按时间步长更新调度与状态
        :param time_step: 步长（秒）
        :param strategy: 'nearest' 或 'max_demand'
        """
        # 先分配任务
        if strategy == 'nearest':
            self.nearest_task()
        elif strategy == 'max_demand':
            self.max_demand_task()
        elif strategy == 'max_priority':
            self.max_priority_task()
        elif strategy == 'genetic':
            self.genetic_task()
        else:
            raise ValueError("Invalid strategy. Choose 'nearest', 'max_demand', or 'max_priority'.")
        self.env.update(time_step)
    
    def nearest_task(self):
        """
        最近任务优先策略：为每个空闲机器人分配距离最近的未服务车辆
        """
        for robot in self.env.robots:
            if robot.state == 'available':

                min_dist = float('inf')
                target_vehicle = None
                for v in self.env.needcharge_vehicles:
                    if v.state == 'needcharge':
                        dist = abs(robot.x - v.parking_spot[0]) + abs(robot.y - v.parking_spot[1])
                        if dist < min_dist:
                            min_dist = dist
                            target_vehicle = v
                if target_vehicle:
                    target_vehicle.set_state('charging')
                    robot.assign_task(target_vehicle)

    def max_demand_task(self):
        """
        最大任务优先策略：为每个空闲机器人分配电量缺口最大的未服务车辆
        """
        for robot in self.env.robots:
            if robot.state == 'available':
                max_gap = 0
                target_vehicle = None
                for v in self.env.needcharge_vehicles:
                    if v.state == 'needcharge':
                        if v.battery_gap > max_gap:
                            max_gap = v.battery_gap
                            target_vehicle = v
                if target_vehicle:
                    target_vehicle.set_state('charging')
                    robot.assign_task(target_vehicle)

    def max_priority_task(self):
        """
        最大优先级策略：为每个空闲机器人分配 battery_gap/离开时间 最大的未服务车辆
        """
        for robot in self.env.robots:
            if robot.state == 'available':
                max_priority = -float('inf')
                target_vehicle = None
                for v in self.env.needcharge_vehicles:
                    if v.state == 'needcharge':
                        # 优先级 = 电量缺口 / 剩余离开时间
                        time_left = max(1, v.departure_time - self.env.time)  # 防止除0
                        priority = v.battery_gap / time_left
                        if priority > max_priority:
                            max_priority = priority
                            target_vehicle = v
                if target_vehicle:
                    target_vehicle.set_state('charging')
                    robot.assign_task(target_vehicle)
    def genetic_task(self, population_size=20, generations=30, mutation_rate=0.1):
        """
        遗传算法分配策略：为所有空闲机器人分配车辆，优化全局分配效果
        """
        import random
        import copy

        robots = [r for r in self.env.robots if r.state == 'available']
        vehicles = [v for v in self.env.needcharge_vehicles if v.state == 'needcharge']
        n = min(len(robots), len(vehicles))
        if n == 0:
            return
        if n == 1:
            # 只有一个机器人和一个车辆，直接分配
            robots[0].assign_task(vehicles[0])
            vehicles[0].set_state('charging')
            return

        # 染色体：机器人与车辆的分配方案（车辆索引的排列）
        def fitness(chromosome):
            # 适应度函数：总距离和（距离越小越好）
            total_dist = 0
            for i, v_idx in enumerate(chromosome):
                robot = robots[i]
                vehicle = vehicles[v_idx]
                dist = abs(robot.x - vehicle.parking_spot[0]) + abs(robot.y - vehicle.parking_spot[1])
                total_dist += dist
            return -total_dist  # 距离越小适应度越高

        # 初始化种群
        population = []
        base = list(range(len(vehicles)))
        for _ in range(population_size):
            chromosome = random.sample(base, n)
            population.append(chromosome)

        for gen in range(generations):
            # 计算适应度
            scored = [(fitness(ch), ch) for ch in population]
            scored.sort(reverse=True)
            # 选择前一半
            selected = [ch for _, ch in scored[:population_size // 2]]

            # 交叉
            children = []
            while len(children) < population_size - len(selected):
                p1, p2 = random.sample(selected, 2)
                cut = random.randint(1, n - 1)
                child = p1[:cut] + [v for v in p2 if v not in p1[:cut]]
                children.append(child)

            # 变异
            for child in children:
                if random.random() < mutation_rate:
                    i, j = random.sample(range(n), 2)
                    child[i], child[j] = child[j], child[i]

            population = selected + children

        # 取最优解
        best_chromosome = max(population, key=fitness)
        # 分配任务
        for i, v_idx in enumerate(best_chromosome):
            robot = robots[i]
            vehicle = vehicles[v_idx]
            vehicle.set_state('charging')
            robot.assign_task(vehicle)