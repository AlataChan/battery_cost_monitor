#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电池成本分析主脚本
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cost_calculator import BatteryCostCalculator
from chart_generator import ChartGenerator
from dashboard_generator import DashboardGenerator
from config import BATTERY_CONFIG

def get_current_prices():
    """获取当前价格（这里需要集成现有的价格获取逻辑）"""
    # 模拟数据，实际应该从gamma_shock_BYTE.py获取
    return {
        'LC': 85000,  # 碳酸锂当前价格
        'NI': 28000   # 镍当前价格
    }

def main():
    print("开始电池成本分析...")
    
    # 1. 初始化组件
    calculator = BatteryCostCalculator()
    chart_gen = ChartGenerator()
    dashboard_gen = DashboardGenerator()
    
    # 2. 获取当前价格
    current_prices = get_current_prices()
    print(f"获取到当前价格: {current_prices}")

    # 3. 计算成本
    cost_data = calculator.calculate_current_cost()
    print(f"成本计算完成，总成本: {cost_data['total_cost']:.2f}元")
    
    # 4. 保存成本历史
    calculator.save_cost_history(cost_data)
    
    # 5. 生成图表
    chart_files = {}
    
    # 成本构成图
    comp_chart = chart_gen.generate_cost_composition_chart(cost_data)
    if comp_chart:
        chart_files['cost_composition'] = comp_chart
    
    # 成本趋势图
    trend_chart = chart_gen.generate_cost_trend_chart('data/cost_history.csv')
    if trend_chart:
        chart_files['cost_trend'] = trend_chart
    
    # 6. 生成仪表板
    dashboard_path = dashboard_gen.generate_dashboard(cost_data, chart_files)
    
    print(f"\n分析完成！")
    print(f"仪表板文件: {dashboard_path}")
    print(f"总成本: ¥{cost_data['total_cost']:.2f}")
    print(f"成本变化: ¥{cost_data['cost_change']:.2f} ({cost_data['cost_change_pct']:.2f}%)")

if __name__ == "__main__":
    main()