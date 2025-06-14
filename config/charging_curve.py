import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', "hiraginosansgb", "songti", "stheitimedium", "simhei"]
matplotlib.rcParams['axes.unicode_minus'] = False


def simulate_charging_curve(voltage, capacity_kwh=100, initial_soc=10, max_c_rate=3):
    """
    模拟电动汽车电池充电曲线
    
    参数:
    voltage - 电池系统电压 (V)
    capacity_kwh - 电池容量 (kWh)
    initial_soc - 初始电量百分比 (%)
    max_c_rate - 最大充电倍率 (C)
    """
    # 时间点 (0-60分钟，步长为1分钟)
    time = np.linspace(0, 60, 61)
    
    # 根据电压计算最大充电功率
    if voltage == 800:
        max_power = 350  # 800V系统最大充电功率 (kW)
    else:  # 400V
        max_power = 150  # 400V系统最大充电功率 (kW)
    
    # 电池容量 (Ah)
    capacity_ah = capacity_kwh * 1000 / voltage
    
    # 初始SOC
    soc = np.zeros_like(time)
    soc[0] = initial_soc
    
    # 充电功率
    power = np.zeros_like(time)
    
    # 模拟充电过程
    for i in range(1, len(time)):
        # 当前SOC条件下的充电功率计算
        current_soc = soc[i-1]
        
        # 功率随SOC变化
        if current_soc < 50:
            # 在低SOC下可以达到最大功率
            power_factor = 1.0
        elif current_soc < 80:
            # 中等SOC开始逐渐降低功率
            power_factor = 1.0 - (current_soc - 50) / 30 * 0.5
        else:
            # 高SOC下功率迅速下降
            power_factor = 0.5 - (current_soc - 80) / 20 * 0.45
        
        # 800V系统在高SOC时保持更高的充电功率
        if voltage == 800 and current_soc > 50:
            power_factor += 0.15
        
        # 确保功率因子在合理范围内
        power_factor = max(0.05, min(1.0, power_factor))
        
        # 当前充电功率
        power[i] = max_power * power_factor
        
        # 充电量计算 (功率×时间/容量)
        delta_soc = (power[i] * (time[i] - time[i-1]) / 60) / capacity_kwh * 100
        
        # 更新SOC
        soc[i] = min(100, soc[i-1] + delta_soc)
        
        # 如果已充满，调整最后一个功率点
        if soc[i] >= 99.9:
            power[i] = 0.05 * max_power  # 极低的维持充电功率
            soc[i] = 100.0
            break
    
    return time, soc, power

# 创建800V和400V的充电曲线
time_800v, soc_800v, power_800v = simulate_charging_curve(800)
time_400v, soc_400v, power_400v = simulate_charging_curve(400)

# 创建图表
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

# 绘制SOC曲线
ax1.plot(time_800v, soc_800v, 'b-', linewidth=2.5, label='800V系统')
ax1.plot(time_400v, soc_400v, 'r-', linewidth=2.5, label='400V系统')
ax1.set_xlabel('充电时间 (分钟)', fontsize=12)
ax1.set_ylabel('电池电量 SOC (%)', fontsize=12)
ax1.set_title('电动汽车电池充电曲线 - SOC变化', fontsize=16)
ax1.grid(True, linestyle='--', alpha=0.7)
ax1.legend(fontsize=12)
ax1.set_xlim(0, 60)
ax1.set_ylim(0, 105)
ax1.yaxis.set_major_formatter(mtick.PercentFormatter())

# 添加10分钟间隔的垂直点线
for t in range(0, 61, 10):
    ax1.axvline(x=t, color='gray', linestyle=':', alpha=0.5)

# 绘制充电功率曲线
ax2.plot(time_800v, power_800v, 'b-', linewidth=2.5, label='800V系统')
ax2.plot(time_400v, power_400v, 'r-', linewidth=2.5, label='400V系统')
ax2.set_xlabel('充电时间 (分钟)', fontsize=12)
ax2.set_ylabel('充电功率 (kW)', fontsize=12)
ax2.set_title('电动汽车电池充电曲线 - 充电功率变化', fontsize=16)
ax2.grid(True, linestyle='--', alpha=0.7)
ax2.legend(fontsize=12)
ax2.set_xlim(0, 60)
ax2.set_ylim(0, 380)

# 添加10分钟间隔的垂直点线
for t in range(0, 61, 10):
    ax2.axvline(x=t, color='gray', linestyle=':', alpha=0.5)

# 计算10%-80%充电时间
def find_charging_time(soc, time, start_soc=10, end_soc=80):
    start_idx = np.where(soc >= start_soc)[0][0]
    end_idx = np.where(soc >= end_soc)[0][0]
    return time[end_idx] - time[start_idx]

time_800v_10_80 = find_charging_time(soc_800v, time_800v)
time_400v_10_80 = find_charging_time(soc_400v, time_400v)

# 添加10%-80%充电时间注释
ax1.annotate(f'800V系统: 10%-80% 充电时间 = {time_800v_10_80:.1f}分钟',
            xy=(30, 45), xytext=(5, 65),
            fontsize=11, color='blue')
ax1.annotate(f'400V系统: 10%-80% 充电时间 = {time_400v_10_80:.1f}分钟',
            xy=(30, 45), xytext=(5, 55),
            fontsize=11, color='red')

plt.tight_layout()
plt.savefig('ev_charging_comparison.png', dpi=300)
plt.show()

# 打印一些关键数据
print(f"800V系统最大充电功率: {max(power_800v):.1f} kW")
print(f"400V系统最大充电功率: {max(power_400v):.1f} kW")
print(f"800V系统10%-80%充电时间: {time_800v_10_80:.1f} 分钟")
print(f"400V系统10%-80%充电时间: {time_400v_10_80:.1f} 分钟")