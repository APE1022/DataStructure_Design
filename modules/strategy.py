from modules.qlearning_agent import QLearningAgent
import numpy as np
from scipy.optimize import linear_sum_assignment

"""
调度策略模块 (Task Strategy Module)
===================================
本模块实现了园区充电调度系统的多种任务分配与调度策略，支持不同规模和复杂度的调度需求。

主要功能：
- 最近任务优先（匈牙利算法）：全局最小化机器人到车辆的总距离
- 最大需求优先：优先为电量缺口最大的车辆分配最近机器人
- 最大优先级分配：综合电量缺口与离开时间，优先为高优先级车辆分配
- 遗传算法多目标优化：基于遗传算法优化权重的多目标分配
- 强化学习分配：基于Q-learning的智能分配策略
- 超启发式策略：根据环境状态动态选择最优底层调度策略

设计说明：
该模块通过面向对象方式封装了多种调度算法，便于灵活切换和扩展。支持静态启发式、元启发式、强化学习等多种分配方法，适用于不同规模和复杂度的仿真场景。

用法示例：
    strategy = TaskStrategy(env, time_step=1.0, map_size='medium')
    strategy.update(strategy='nearest')
    strategy.update(strategy='genetic')
    strategy.update(strategy='hyper_heuristic')

创建/维护者: 姚炜博、肖翔云（强化学习部分）
最后修改: 2025-05-23
版本: 1.0.0
"""

class TaskStrategy:
    def __init__(self, env, time_step, map_size='small', agent=None):
        self.env = env
        self.time_step = time_step
        self.map_size = map_size
        self.agent = agent 

    def update(self, strategy='nearest'):
        """
        按时间步长更新调度与状态
        param :
        strategy: 调度策略， 可选值为 'nearest', 'max_demand', 'max_priority', 'genetic', 'RL', 'multi_objective'
        agent: Q表策略需要传入agent参数
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
        elif strategy == 'RL':
            if self.agent is None:
                raise ValueError("Q表策略需要传入agent参数")
            self.q_table_task(self.agent)
        elif strategy == 'hyper_heuristic':
            self.hyper_heuristic_task()
        else:
            raise ValueError("Invalid strategy. Choose from available strategies.")
        # 更新环境状态
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

    def genetic_task(self):
        """
        使用遗传算法优化过的参数进行多目标任务分配
        根据不同地图大小自动选择对应的最佳参数配置
        """
        # 预先通过遗传算法优化得到的最佳权重参数
        optimized_weights = {
            'small': {  # 小地图最佳权重
                'urgency': 0.28,
                'distance': 0.25,
                'robot_energy': 0.08
            },
            'medium': {  # 中地图最佳权重
                'urgency': 0.25,
                'distance': 0.30,
                'robot_energy': 0.07
            },
            'large': {  # 大地图最佳权重
                'urgency': 0.47587022217849884,
                'distance': 0.5241297778215013,  # 大地图中距离因素更重要
                'robot_energy': 0
            }
        }
        
        # 根据当前地图大小确定使用的权重
        map_size = self.map_size
        weights = optimized_weights.get(map_size, optimized_weights['medium'])  # 默认使用中等地图权重
        
        # 获取可用机器人和需要服务的车辆
        available_robots = [r for r in self.env.robots if r.state == 'available']
        
        # 如果没有可用资源，直接返回
        if not available_robots or not self.env.needcharge_vehicles:
            return
        
        # 计算每辆车的紧急度指标 (电量缺口/离开时间)
        urgency_scores = {}
        for vehicle in self.env.needcharge_vehicles:
            urgency = vehicle.battery_gap / max(0.1, vehicle.departure_time)
            urgency_scores[vehicle] = urgency
        
        # 最大和最小值，用于标准化
        max_urgency = max(urgency_scores.values()) if urgency_scores else 1
               
        # 为每个机器人-车辆对计算综合分数
        assignments = []
        
        for robot in available_robots:
            for vehicle in self.env.needcharge_vehicles:
                # 计算因素并标准化到0-1范围

                # 2. 紧急程度 - 越紧急越优先
                urgency_score = urgency_scores[vehicle] / max_urgency
                
                # 3. 距离 - 越近越好（转换为1-距离的比例）
                distance = ((robot.x - vehicle.parking_spot[0])**2 + 
                        (robot.y - vehicle.parking_spot[1])**2)**0.5
                max_possible_dist = ((self.env.park_size[0])**2 + (self.env.park_size[1])**2)**0.5
                distance_score = 1 - (distance / max_possible_dist)
                
                # 4. 机器人电量 - 越高越好
                robot_energy_score = robot.battery.soc / 100
 
                # 综合评分，使用优化过的权重
                final_score = (
                    weights['urgency'] * urgency_score +
                    weights['distance'] * distance_score +
                    weights['robot_energy'] * robot_energy_score
                )
                
                # 存储评分和对应的机器人-车辆对
                assignments.append((final_score, robot, vehicle))
        
        # 按分数从高到低排序
        assignments = sorted(assignments, key=lambda x: x[0], reverse=True)
        
        # 记录已分配的资源
        assigned_robots = set()
        assigned_vehicles = set()
        
        # 执行分配
        for score, robot, vehicle in assignments:
            # 如果机器人或车辆已被分配，跳过
            if robot in assigned_robots or vehicle in assigned_vehicles:
                continue
                
            # 执行分配
            vehicle.set_state('charging')
            robot.assign_task(vehicle)
            
            # 标记为已分配
            assigned_robots.add(robot)
            assigned_vehicles.add(vehicle)
            
            # 更新环境中的车辆列表
            if vehicle in self.env.needcharge_vehicles:
                self.env.needcharge_vehicles.remove(vehicle)
                self.env.charging_vehicles.append(vehicle)
            
            # 如果所有机器人都已分配，结束
            if len(assigned_robots) >= len(available_robots):
                break
    
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

    # TODO：未完善
    def hyper_heuristic_task(self):
        """
        超启发式策略选择：根据环境状态动态选择最合适的底层调度策略
        可选策略包括最近任务优先、最大需求优先、最大优先级、遗传算法、强化学习等
        """
        # 示例：根据当前待充电车辆数量和机器人空闲比例动态选择策略
        n_vehicles = len(self.env.needcharge_vehicles)
        n_robots = len([r for r in self.env.robots if r.state == 'available'])

        # 简单规则：车辆多时用最高优先级，车辆少时用最近任务优先
        if n_vehicles > n_robots:
            self.max_priority_task()  # 匈牙利算法，全局最优分配
        else: 
            self.nearest_task()  # 多目标加权分配

