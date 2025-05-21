# -*- coding: utf-8 -*-
'''

'''
class TaskStrategy:
    """
    调度策略类，支持最近任务优先和最大任务优先
    """

    def __init__(self, env,time_step):
        self.env = env
        self.time_step = time_step

    def update(self,strategy='nearest'):
        """
        按时间步长更新调度与状态
        param :
        strategy: 调度策略
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
        self.env.update(self.time_step)
    
    def nearest_task(self):
        """
        最近任务优先策略：为每个空闲机器人分配距离最近的未服务车辆
        """
        for robot in self.env.robots:
            if robot.state == 'available':
                min_dist = 10000
                target_vehicle = None
                for v in self.env.needcharge_vehicles:
                    dist = (abs(robot.x - v.parking_spot[0])**2 + abs(robot.y - v.parking_spot[1])**2)**0.5
                    if dist < min_dist:
                        min_dist = dist
                        target_vehicle = v
                if target_vehicle:
                    target_vehicle.set_state('charging')
                    self.env.needcharge_vehicles.remove(target_vehicle)
                    self.env.charging_vehicles.append(target_vehicle)
                    robot.assign_task(target_vehicle)

    def max_demand_task(self):
        """
        最大任务优先策略：为电量缺口/离开时间最大的未服务车辆分配最近的空闲机器人
        """
        self.env.needcharge_vehicles.sort(key=lambda v: (v.battery_gap / v.departure_time), reverse=True)
        index = 0
        if index < len(self.env.needcharge_vehicles):
            for robot in self.env.robots:
                if robot.state == 'available':
                    target_vehicle = self.env.needcharge_vehicles[index]
                    target_vehicle.set_state('charging')
                    robot.assign_task(target_vehicle)
                    index += 1
                    if index >= len(self.env.needcharge_vehicles):
                        break

    def max_priority_task(self):
        """
        最大任务优先策略：为电量缺口/离开时间最大的未服务车辆分配最近的空闲机器人
        """
        # 计算每辆车的优先级指标 (电量缺口/离开时间)
        prioritized_vehicles = []
        for vehicle in self.env.needcharge_vehicles:
            priority = vehicle.battery_gap / max(0.1, vehicle.departure_time)  # 防止除以0
            prioritized_vehicles.append((priority, vehicle))
        
        # 按优先级从高到低排序
        prioritized_vehicles.sort(reverse=True)
        
        # 记录已分配的机器人和车辆
        assigned_robots = set()
        assigned_vehicles = set()
        
        # 遍历高优先级的车辆
        for _, vehicle in prioritized_vehicles:
            if vehicle in assigned_vehicles:
                continue
                
            # 找到距离该车辆最近的空闲机器人
            min_dist = float('inf')
            closest_robot = None
            
            for robot in self.env.robots:
                if robot.state == 'available' and robot not in assigned_robots:
                    # 计算距离
                    dist = ((robot.x - vehicle.parking_spot[0])**2 + 
                            (robot.y - vehicle.parking_spot[1])**2)**0.5
                    
                    if dist < min_dist:
                        min_dist = dist
                        closest_robot = robot
            
            # 如果找到适合的机器人，分配任务
            if closest_robot:
                vehicle.set_state('charging')
                closest_robot.assign_task(vehicle)
                
                # 标记已分配
                assigned_robots.add(closest_robot)
                assigned_vehicles.add(vehicle)
                
                # 从待充电车辆列表移到充电车辆列表
                if vehicle in self.env.needcharge_vehicles:
                    self.env.needcharge_vehicles.remove(vehicle)
                    self.env.charging_vehicles.append(vehicle)
            
            # 如果没有空闲机器人了，结束分配
            if len(assigned_robots) >= len([r for r in self.env.robots if r.state == 'available']):
                break

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
                dist = (abs(robot.x - vehicle.parking_spot[0])**2 + abs(robot.y - vehicle.parking_spot[1])**2)**0.5
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