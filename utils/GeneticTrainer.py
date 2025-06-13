import numpy as np
import random
import copy
import matplotlib.pyplot as plt
import time
from datetime import datetime
import os
import json
import pickle

import sys
import os
import multiprocessing
from functools import partial
# 将项目根目录添加到路径中
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 现在可以正常导入了
from modules.envs import ParkEnv
from modules.strategy import TaskStrategy

class GeneticOptimizer:
    """遗传算法优化器，用于寻找多目标任务调度的最优权重参数"""
    
    def __init__(self, population_size=300, generations=100, 
                 mutation_rate=0.2, crossover_rate=0.7,
                 elite_size=5, tournament_size=3):
        """
        初始化遗传算法优化器
        
        参数:
            population_size: 种群大小
            generations: 迭代代数
            mutation_rate: 变异率
            crossover_rate: 交叉率
            elite_size: 精英个体数量
            tournament_size: 锦标赛选择的参赛者数量
        """
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_size = elite_size
        self.tournament_size = tournament_size
        
        # 权重键和范围定义
        self.weight_keys = [
            'urgency',        # 紧急程度权重
            'distance',       # 距离权重
        ]
        
        # 每个权重的取值范围
        self.weight_ranges = {
            'urgency': (0.1, 1),
            'distance': (0.1, 1),
        }
        
        # 用于可视化的历史记录
        self.history = {
            'best_fitness': [],
            'avg_fitness': [],
            'best_weights': [],
            'population': []
        }
    
    def create_individual(self):
        """创建一个随机个体（权重组合）"""
        # 生成随机权重
        weights = {}
        for key in self.weight_keys:
            min_val, max_val = self.weight_ranges[key]
            weights[key] = random.uniform(min_val, max_val)
        
        # 归一化权重，使总和为1
        total = sum(weights.values())
        for key in weights:
            weights[key] /= total
            
        return weights
    
    def create_initial_population(self):
        """创建初始种群"""
        return [self.create_individual() for _ in range(self.population_size)]
    
    def evaluate_fitness(self, weights, env_config, num_steps=2000, num_runs=3):
        """
        评估权重组合的适应度
        
        参数:
            weights: 权重字典
            env_config: 环境配置
            num_steps: 每次仿真的步数
            num_runs: 仿真运行次数 (取平均结果)
        
        返回:
            fitness_score: 适应度评分 (越高越好)
        """
        total_fitness = 0
        
        for run in range(num_runs):
            # 创建环境和策略
            env = ParkEnv(**env_config)
            strategy = TaskStrategy(env, time_step=env_config['time_step'])
            
            # 设置策略权重
            strategy.weights = copy.deepcopy(weights)
            
            # 初始状态统计
            initial_stats = {
                'completed': 0,
                'failed': 0,
            }
            
            # 运行仿真
            for step in range(num_steps):
                strategy.update(strategy='genetic')
            
            # 最终状态统计
            final_stats = {
                'completed': len(env.completed_vehicles),
                'failed': len(env.failed_vehicles),
                'needcharge': len(env.needcharge_vehicles),
                'charging': len(env.charging_vehicles),
                'time': env.time
            }
            
            # 计算性能指标
            completed_count = final_stats['completed']
            failed_count = final_stats['failed']
            
            # 计算平均等待时间
            wait_times = []
            for vehicle in env.completed_vehicles + env.charging_vehicles:
                if hasattr(vehicle, 'wait_time') and vehicle.wait_time is not None:
                    wait_times.append(vehicle.wait_time)
            
            avg_wait_time = np.mean(wait_times) if wait_times else 1000
            
            # 计算完成率
            completion_rate = completed_count / max(1, completed_count + failed_count)
            
            # 综合评分 (可根据需要调整各指标权重)
            fitness = (
                100 * completion_rate   # 完成率
                # (avg_wait_time / 60)   # 平均等待时间
            )
            
            total_fitness += fitness
        
        # 取平均
        return total_fitness / num_runs
    
    def evaluate_individual(self, individual, env_config, num_steps=2000, num_runs=3):
        """
        评估单个个体的适应度 (供并行计算使用)
        """
        return individual, self.evaluate_fitness(individual, env_config, num_steps, num_runs)
    
    def evaluate_population(self, population, env_config):
        """评估整个种群的适应度 (使用多核并行)"""
        fitness_scores = []
        
        print(f"评估种群适应度 ({len(population)} 个体)...")
        
        # 确定可用的CPU核心数，预留一个核心给系统
        num_cores = max(1, multiprocessing.cpu_count() - 1)
        print(f"使用 {num_cores} 个CPU核心进行并行计算...")
        
        # 创建进程池
        with multiprocessing.Pool(processes=num_cores) as pool:
            # 创建一个偏函数，固定除个体外的其他参数
            eval_func = partial(self.evaluate_individual, 
                               env_config=env_config, 
                               num_steps=2000, 
                               num_runs=3)
            
            # 使用进程池并行评估所有个体
            results = []
            for i, result in enumerate(pool.imap(eval_func, population)):
                individual, fitness = result
                results.append((individual, fitness))
                print(f"  个体 {i+1}/{len(population)}, 适应度: {fitness:.2f}")
        
        # 按适应度从高到低排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def select_parent(self, fitness_scores):
        """使用锦标赛选择法选择父本"""
        # 随机选择几个个体参加锦标赛
        tournament = random.sample(fitness_scores, min(self.tournament_size, len(fitness_scores)))
        # 选出适应度最高的个体
        tournament.sort(key=lambda x: x[1], reverse=True)
        return tournament[0][0]
    
    def crossover(self, parent1, parent2):
        """对两个父本进行交叉操作"""
        if random.random() > self.crossover_rate:
            return copy.deepcopy(parent1)
        
        # 使用均匀交叉或混合(blend)交叉
        child = {}
        for key in self.weight_keys:
            # 混合交叉：在父本权重之间插值
            alpha = random.random()
            child[key] = alpha * parent1[key] + (1-alpha) * parent2[key]
        
        # 归一化权重，使总和为1
        total = sum(child.values())
        for key in child:
            child[key] /= total
            
        return child
    
    def mutate(self, individual):
        """对个体进行变异操作"""
        mutated = copy.deepcopy(individual)
        
        # 对每个权重有一定概率进行变异
        for key in self.weight_keys:
            if random.random() < self.mutation_rate:
                min_val, max_val = self.weight_ranges[key]
                # 在当前值附近变异
                delta = random.uniform(-0.1, 0.1)
                mutated[key] = max(min_val, min(max_val, mutated[key] + delta))
        
        # 归一化权重，使总和为1
        total = sum(mutated.values())
        for key in mutated:
            mutated[key] /= total
            
        return mutated
    
    def create_next_generation(self, fitness_scores):
        """创建下一代种群"""
        sorted_population = [x[0] for x in fitness_scores]
        next_generation = []
        
        # 精英保留：直接将最优的几个个体保留到下一代
        elites = sorted_population[:self.elite_size]
        next_generation.extend(elites)
        
        # 生成剩余个体
        while len(next_generation) < self.population_size:
            # 选择父本
            parent1 = self.select_parent(fitness_scores)
            parent2 = self.select_parent(fitness_scores)
            
            # 交叉
            child = self.crossover(parent1, parent2)
            
            # 变异
            child = self.mutate(child)
            
            next_generation.append(child)
        
        return next_generation
    
    def run(self, env_config, save_dir="optimization_results"):
        """
        运行遗传算法优化
        
        参数:
            env_config: 环境配置字典
            save_dir: 保存结果的目录
        
        返回:
            best_weights: 找到的最佳权重
            best_fitness: 最佳适应度分数
            history: 优化过程的历史记录
        """
        # 创建保存结果的目录
        os.makedirs(save_dir, exist_ok=True)
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(save_dir, f"run_{run_id}")
        os.makedirs(run_dir, exist_ok=True)
        
        # 初始化种群
        print("创建初始种群...")
        population = self.create_initial_population()
        
        best_individual = None
        best_fitness = float('-inf')
        
        print(f"开始遗传算法优化，共 {self.generations} 代...")
        start_time = time.time()
        
        for generation in range(self.generations):
            gen_start_time = time.time()
            print(f"\n第 {generation+1}/{self.generations} 代")
            
            # 评估种群
            fitness_scores = self.evaluate_population(population, env_config)
            
            # 记录当前代的最佳个体
            current_best_individual, current_best_fitness = fitness_scores[0]
            avg_fitness = np.mean([score for _, score in fitness_scores])
            
            # 更新全局最佳
            if current_best_fitness > best_fitness:
                best_individual = copy.deepcopy(current_best_individual)
                best_fitness = current_best_fitness
                print(f"发现更好的解！适应度: {best_fitness:.2f}")
                print(f"权重: {best_individual}")
            
            # 保存历史记录
            self.history['best_fitness'].append(current_best_fitness)
            self.history['avg_fitness'].append(avg_fitness)
            self.history['best_weights'].append(current_best_individual)
            self.history['population'].append([ind for ind, _ in fitness_scores])
            
            # 在每代结束时保存中间结果
            generation_data = {
                'generation': generation + 1,
                'best_fitness': current_best_fitness,
                'avg_fitness': avg_fitness,
                'best_weights': current_best_individual,
                'population_fitness': [(ind, score) for ind, score in fitness_scores]
            }
            
            with open(os.path.join(run_dir, f"generation_{generation+1}.json"), 'w') as f:
                json.dump(generation_data, f, indent=2)
            
            # 创建下一代
            if generation < self.generations - 1:  # 最后一代无需创建下一代
                population = self.create_next_generation(fitness_scores)
            
            gen_elapsed = time.time() - gen_start_time
            print(f"第 {generation+1} 代完成，耗时 {gen_elapsed:.2f} 秒")
            print(f"当前最佳适应度: {current_best_fitness:.2f}, 平均适应度: {avg_fitness:.2f}")
            print(f"最佳权重: {current_best_individual}")
            
            # 生成并保存当前代的可视化结果
            self.visualize_generation(generation + 1, run_dir)
        
        total_elapsed = time.time() - start_time
        print(f"\n优化完成，总耗时 {total_elapsed:.2f} 秒")
        print(f"最佳适应度: {best_fitness:.2f}")
        print(f"最佳权重: {best_individual}")
        
        # 保存最终结果
        final_results = {
            'best_weights': best_individual,
            'best_fitness': best_fitness,
            'parameters': {
                'population_size': self.population_size,
                'generations': self.generations,
                'mutation_rate': self.mutation_rate,
                'crossover_rate': self.crossover_rate,
                'elite_size': self.elite_size,
                'tournament_size': self.tournament_size,
            },
            'env_config': env_config,
            'runtime_seconds': total_elapsed
        }
        
        with open(os.path.join(run_dir, "final_results.json"), 'w') as f:
            json.dump(final_results, f, indent=2)
        
        # 保存完整的历史记录
        with open(os.path.join(run_dir, "history.pkl"), 'wb') as f:
            pickle.dump(self.history, f)
        
        # 生成并保存最终的可视化结果
        self.visualize_optimization(run_dir)
        
        return best_individual, best_fitness, self.history
    
    def visualize_generation(self, generation, save_dir):
        """可视化当前代的结果"""
        plt.figure(figsize=(12, 8))
        
        # 适应度历史
        plt.subplot(2, 1, 1)
        plt.plot(self.history['best_fitness'], 'b-', label='最佳适应度')
        plt.plot(self.history['avg_fitness'], 'r-', label='平均适应度')
        plt.title(f'遗传算法优化 - 第 {generation} 代')
        plt.xlabel('代数')
        plt.ylabel('适应度')
        plt.legend()
        plt.grid(True)
        
        # 最佳权重演变
        plt.subplot(2, 1, 2)
        for key in self.weight_keys:
            weights = [ind[key] for ind in self.history['best_weights']]
            plt.plot(weights, label=key)
        plt.title('最佳权重演变')
        plt.xlabel('代数')
        plt.ylabel('权重值')
        plt.legend()
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig(os.path.join(save_dir, f"generation_{generation}.png"))
        plt.close()
    
    def visualize_optimization(self, save_dir):
        """生成优化过程的可视化结果"""
        # 创建图表
        plt.figure(figsize=(15, 10))
        
        # 适应度历史
        plt.subplot(2, 2, 1)
        plt.plot(self.history['best_fitness'], 'b-', label='最佳适应度')
        plt.plot(self.history['avg_fitness'], 'r-', label='平均适应度')
        plt.title('适应度历史')
        plt.xlabel('代数')
        plt.ylabel('适应度')
        plt.legend()
        plt.grid(True)
        
        # 权重演变
        plt.subplot(2, 2, 2)
        for key in self.weight_keys:
            weights = [ind[key] for ind in self.history['best_weights']]
            plt.plot(weights, label=key)
        plt.title('最佳权重演变')
        plt.xlabel('代数')
        plt.ylabel('权重值')
        plt.legend()
        plt.grid(True)
        
        # 散点图展示种群分布
        plt.subplot(2, 2, 3)
        latest_population = self.history['population'][-1]
        x = [ind['battery_gap'] for ind in latest_population]
        y = [ind['urgency'] for ind in latest_population]
        plt.scatter(x, y, alpha=0.7)
        plt.title('最终种群分布 (battery_gap vs urgency)')
        plt.xlabel('battery_gap')
        plt.ylabel('urgency')
        plt.grid(True)
        
        # 散点图展示种群分布
        plt.subplot(2, 2, 4)
        x = [ind['distance'] for ind in latest_population]
        y = [ind['robot_energy'] for ind in latest_population]
        plt.scatter(x, y, alpha=0.7)
        plt.title('最终种群分布 (distance vs robot_energy)')
        plt.xlabel('distance')
        plt.ylabel('robot_energy')
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig(os.path.join(save_dir, "optimization_summary.png"))
        plt.close()
        
        # 生成每个权重对的分布热图
        self.visualize_weight_heatmaps(save_dir)
    
    def visualize_weight_heatmaps(self, save_dir):
        """生成权重对的分布热图"""
        # 取最后一代的种群
        latest_population = self.history['population'][-1]
        
        # 为每对权重生成热图
        weight_pairs = [(a, b) for a in self.weight_keys for b in self.weight_keys if a < b]
        
        for weight1, weight2 in weight_pairs:
            plt.figure(figsize=(8, 6))
            x = [ind[weight1] for ind in latest_population]
            y = [ind[weight2] for ind in latest_population]
            
            # 创建散点图
            plt.scatter(x, y, alpha=0.7)
            plt.title(f'权重分布: {weight1} vs {weight2}')
            plt.xlabel(weight1)
            plt.ylabel(weight2)
            plt.grid(True)
            
            # 添加最佳个体的位置
            best_ind = self.history['best_weights'][-1]
            plt.scatter([best_ind[weight1]], [best_ind[weight2]], 
                      color='red', s=100, marker='*', label='最佳解')
            plt.legend()
            
            plt.tight_layout()
            plt.savefig(os.path.join(save_dir, f"weights_{weight1}_vs_{weight2}.png"))
            plt.close()


def main():
    """主函数：运行遗传算法优化权重参数"""
    # 多进程支持在Windows下需要保护入口点
    if __name__ == "__main__":
        # 定义环境配置
        env_config = {
            'park_size': (200, 200),
            'n_robots': 16,
            'n_vehicles': 40,
            'n_batteries': 10,
            'generate_vehicles_probability': 0.011667, # 以秒为单位，计算得每小时生成车辆的期望为42辆
            'time_step': 10,         # 时间步长(秒)
        }
        
        # 遗传算法参数
        ga_params = {
            'population_size': 200,    # 种群规模
            'generations': 15,        # 迭代代数
            'mutation_rate': 0.3,     # 变异率
            'crossover_rate': 0.7,    # 交叉率
            'elite_size': 3,          # 精英保留数量
            'tournament_size': 3      # 锦标赛规模
        }
        
        # 创建并运行优化器
        optimizer = GeneticOptimizer(**ga_params)
        best_weights, best_fitness, _ = optimizer.run(env_config)
        
        print("\n优化结果：")
        print(f"最佳适应度: {best_fitness:.4f}")
        print("最佳权重组合:")
        for key, value in best_weights.items():
            print(f"  {key}: {value:.4f}")


if __name__ == "__main__":
    # 使用freeze_support解决Windows下多进程可能的问题
    multiprocessing.freeze_support()
    main()