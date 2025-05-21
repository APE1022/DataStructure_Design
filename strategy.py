# -*- coding: utf-8 -*-
from qlearning_agent import QLearningAgent
import numpy as np
from scipy.optimize import linear_sum_assignment

class TaskStrategy:
    """
    调度策略类，支持最近任务优先和最大任务优先
    """

    def __init__(self, env,time_step):
        self.env = env
        self.time_step = time_step
        self.agent = QLearningAgent(env)

    def update(self, strategy='nearest', agent=None):
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
        elif strategy == 'q_table':
            if self.agent is None:
                raise ValueError("Q表策略需要传入agent参数")
            self.q_table_task(self.agent)
        elif strategy == 'battery_management':
            self.battery_management_task()
        elif strategy == 'cluster_service':
            self.cluster_service_task()
        elif strategy == 'multi_objective':
            self.multi_objective_task()
        elif strategy == 'reinforcement_learning':
            self.reinforcement_learning_task()
        elif strategy == 'dynamic':
            self.dynamic_strategy_task()
        else:
            raise ValueError("Invalid strategy. Choose from available strategies.")
        self.env.update(self.time_step)

    def nearest_task(self):
        """
        最近任务优先策略：为所有空闲机器人分配未服务车辆，使得总距离最小
        使用匈牙利算法求解最优分配
        """
        # 获取可用的机器人和车辆
        available_robots = [r for r in self.env.robots if r.state == 'available']
        vehicles = self.env.needcharge_vehicles
        
        # 如果没有可用资源，直接返回
        if not available_robots or not vehicles:
            return
        
        # 构建成本矩阵（距离矩阵）
        cost_matrix = []
        for robot in available_robots:
            row = []
            for vehicle in vehicles:
                # 计算欧氏距离作为成本
                dist = ((robot.x - vehicle.parking_spot[0])**2 + 
                    (robot.y - vehicle.parking_spot[1])**2)**0.5
                row.append(dist)
            cost_matrix.append(row)
        
        # 使用匈牙利算法求解最优分配
        # 转换为numpy数组
        cost_matrix = np.array(cost_matrix)
        
        # 求解最小成本分配问题
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        
        # 根据分配结果执行任务分配
        for i, robot_idx in enumerate(row_ind):
            if i < len(col_ind):  # 确保有匹配的车辆
                vehicle_idx = col_ind[i]
                
                # 确保索引有效
                if robot_idx < len(available_robots) and vehicle_idx < len(vehicles):
                    robot = available_robots[robot_idx]
                    vehicle = vehicles[vehicle_idx]
                    
                    # 分配任务
                    vehicle.set_state('charging')
                    robot.assign_task(vehicle)
                    
                    # 从待充电列表移动到充电列表 TODO
                    if vehicle in self.env.needcharge_vehicles:
                        self.env.needcharge_vehicles.remove(vehicle)
                        self.env.charging_vehicles.append(vehicle)
                    
    def max_demand_task(self):
        """
        最大任务优先策略：为电量缺口最大的未服务车辆分配最近的空闲机器人
        """
        # 如果没有需要分配的资源，直接返回
        if not self.env.needcharge_vehicles or not any(r.state == 'available' for r in self.env.robots):
            return
        
        # 按电量缺口从大到小排序车辆
        prioritized_vehicles = sorted(self.env.needcharge_vehicles, 
                                    key=lambda v: v.battery_gap, 
                                    reverse=True)
        
        # 记录已分配的机器人和车辆
        assigned_robots = set()
        assigned_vehicles = set()
        
        # 为每辆高需求车辆分配最近的机器人
        for vehicle in prioritized_vehicles:
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

        # 获取可用机器人和需要服务的车辆
        robots = [r for r in self.env.robots if r.state == 'available']
        vehicles = self.env.needcharge_vehicles
        
        # 如果没有需要分配的资源，直接返回
        if not robots or not vehicles:
            return
        
        # 定义染色体长度为机器人数量和车辆数量中的较小值
        chrom_length = min(len(robots), len(vehicles))
        
        # 如果染色体长度太小，不适合遗传算法，直接用贪心算法
        if chrom_length <= 1:
            # 使用最近任务策略作为备选
            for robot in robots:
                if robot.state == 'available' and vehicles:
                    # 找到最近的车辆
                    min_dist = float('inf')
                    closest_vehicle = None
                    for vehicle in vehicles:
                        dist = ((robot.x - vehicle.parking_spot[0])**2 + 
                            (robot.y - vehicle.parking_spot[1])**2)**0.5
                        if dist < min_dist:
                            min_dist = dist
                            closest_vehicle = vehicle
                    
                    if closest_vehicle:
                        closest_vehicle.set_state('charging')
                        robot.assign_task(closest_vehicle)
                        vehicles.remove(closest_vehicle)
            return
        
        # 正常的遗传算法流程
        def create_chromosome():
            return random.sample(range(len(vehicles)), chrom_length)
        
        def fitness(chromosome):
            total_fitness = 0
            for i, vehicle_idx in enumerate(chromosome):
                if i < len(robots) and vehicle_idx < len(vehicles):
                    robot = robots[i]
                    vehicle = vehicles[vehicle_idx]
                    
                    dist = ((robot.x - vehicle.parking_spot[0])**2 + 
                            (robot.y - vehicle.parking_spot[1])**2)**0.5
                    
                    urgency = vehicle.battery_gap / max(0.1, vehicle.departure_time)
                    
                    score = urgency / (dist + 1)
                    total_fitness += score
            return total_fitness

        # 初始化种群
        population = []
        base = list(range(len(vehicles)))
        for _ in range(population_size):
            chromosome = random.sample(base, chrom_length)
            population.append(chromosome)

        for gen in range(generations):
            # 计算适应度
            scored = [(fitness(ch), ch) for ch in population]
            scored.sort(reverse=True)
            selected = [ch for _, ch in scored[:population_size // 2]]

            # 交叉
            children = []
            while len(children) < population_size - len(selected):
                p1, p2 = random.sample(selected, 2)
                
                # 修复：确保切分点在有效范围内
                if chrom_length > 2:
                    cut = random.randint(1, chrom_length - 1)
                    child = p1[:cut] + [v for v in p2 if v not in p1[:cut]]
                else:
                    # 染色体长度为2，使用简单交换
                    child = p2.copy()  # 直接使用另一个父本
                
                # 确保子代长度正确
                while len(child) < chrom_length:
                    new_gene = random.choice(base)
                    if new_gene not in child:
                        child.append(new_gene)
                        
                # 如果子代过长，截断
                if len(child) > chrom_length:
                    child = child[:chrom_length]
                    
                children.append(child)

            # 变异
            for child in children:
                if random.random() < mutation_rate:
                    if chrom_length >= 2:  # 确保有足够的基因可以交换
                        i, j = random.sample(range(chrom_length), 2)
                        child[i], child[j] = child[j], child[i]

            population = selected + children

        # 取最优解
        best_chromosome = max(population, key=fitness)
        
        # 分配任务
        for i, v_idx in enumerate(best_chromosome):
            if i < len(robots) and v_idx < len(vehicles):  # 确保索引有效
                robot = robots[i]
                vehicle = vehicles[v_idx]
                vehicle.set_state('charging')
                robot.assign_task(vehicle)
    
    def q_table_task(self, agent):
        """
        基于Q表的推理分配策略：每步直接选择Q值最大的动作（机器人-车辆对）
        """
        state = self.env.get_status()
        state_idx = agent.discretize_state(state)
        assigned_robots = set()
        assigned_vehicles = set()

        # 动作空间大小 = 机器人数量 * 最大车辆数
        for _ in range(len(self.env.robots)):
            # 获取当前状态下所有动作的Q值
            q_values = agent.q_table[state_idx].copy()

            # 屏蔽已分配的机器人和车辆的动作
            for action in range(len(q_values)):
                robot_idx = action // self.env.max_vehicles
                car_idx = action % self.env.max_vehicles
                if (robot_idx >= len(self.env.robots) or
                    car_idx >= len(self.env.needcharge_vehicles) or
                    self.env.robots[robot_idx] in assigned_robots or
                    self.env.needcharge_vehicles[car_idx] in assigned_vehicles or
                    self.env.robots[robot_idx].state != "available" or
                    self.env.needcharge_vehicles[car_idx].state != "needcharge"):
                    q_values[action] = -float('inf')  # 使其不会被选中

            # 选择Q值最大的动作
            best_action = q_values.argmax()
            if q_values[best_action] == -float('inf'):
                break  # 没有可用动作

            robot_idx = best_action // self.env.max_vehicles
            car_idx = best_action % self.env.max_vehicles
            robot = self.env.robots[robot_idx]
            car = self.env.needcharge_vehicles[car_idx]

            # 分配任务
            car.set_state('charging')
            robot.assign_task(car)
            assigned_robots.add(robot)
            assigned_vehicles.add(car)
            if car in self.env.needcharge_vehicles:
                self.env.needcharge_vehicles.remove(car)
                self.env.charging_vehicles.append(car)