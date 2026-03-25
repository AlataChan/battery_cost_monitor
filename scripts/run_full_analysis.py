#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电池成本监测与价格预测系统 - 完整分析脚本
集成AI导师功能，专注碳酸锂(LC)分析
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from cost_calculator import BatteryCostCalculator
from chart_generator import ChartGenerator
from dashboard_generator import DashboardGenerator

# 导入新的图表生成器
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'charts'))
from prediction_charts import PredictionChartGenerator
from technical_charts import TechnicalChartGenerator

def main():
    print("🚀 开始电池成本监测与价格预测分析...")
    print("🎯 专注分析: 碳酸锂(LC)")
    print("=" * 80)
    
    # 1. 初始化组件
    print("📊 初始化分析组件...")
    cost_calculator = BatteryCostCalculator()
    cost_chart_gen = ChartGenerator()
    prediction_chart_gen = PredictionChartGenerator()
    technical_chart_gen = TechnicalChartGenerator()
    dashboard_gen = DashboardGenerator()
    
    # 2. 执行成本分析
    print("\n💰 执行成本分析...")
    try:
        cost_data = cost_calculator.calculate_current_cost()
        
        print(f"✅ 成本分析完成")
        print(f"   总成本: ¥{cost_data['total_cost']:.2f}")
        print(f"   成本变化: ¥{cost_data['cost_change']:.2f} ({cost_data['cost_change_pct']:.2f}%)")
        print(f"   数据源: {cost_data.get('data_source', 'unknown')}")
        
        # 显示材料成本详情
        print("\n📋 材料成本详情:")
        for symbol, material in cost_data['materials'].items():
            print(f"   {material['name']}: ¥{material['current_cost']:.2f} "
                  f"(变化: {'+' if material['cost_change'] >= 0 else ''}¥{material['cost_change']:.2f})")
        
    except Exception as e:
        print(f"❌ 成本分析失败: {e}")
        return
    
    # 3. 获取AI导师洞察
    print("\n🤖 获取AI导师洞察...")
    try:
        ai_insights = cost_calculator.get_ai_insights(cost_data)
        if not ai_insights.get('error'):
            print("✅ AI导师分析完成")
            
            # 显示成本趋势分析
            cost_trend = ai_insights.get('cost_trend', {})
            print(f"   成本趋势: {cost_trend.get('trend', '未知')}")
            print(f"   变化幅度: {cost_trend.get('change_pct', 0):.2f}%")
            print(f"   关注状态: {cost_trend.get('status', '未知')}")
            
            # 显示AI建议
            recommendations = ai_insights.get('recommendations', [])
            if recommendations:
                print("   📝 AI建议:")
                for i, rec in enumerate(recommendations, 1):
                    print(f"      {i}. {rec}")
        else:
            print(f"⚠️ AI导师分析失败: {ai_insights.get('error_message', '未知错误')}")
            
    except Exception as e:
        print(f"⚠️ 获取AI洞察失败: {e}")
    
    # 4. 保存成本历史
    print("\n💾 保存成本历史数据...")
    try:
        cost_calculator.save_cost_history(cost_data)
        print("✅ 成本历史数据已保存")
    except Exception as e:
        print(f"⚠️ 保存成本历史失败: {e}")
    
    # 5. 生成图表
    print("\n📈 生成分析图表...")
    all_charts = {}
    
    # 成本图表
    try:
        print("   生成成本构成图...")
        comp_chart = cost_chart_gen.generate_cost_composition_chart(cost_data)
        if comp_chart:
            all_charts['cost_composition'] = comp_chart
            print("   ✅ 成本构成图已生成")
        
        print("   生成成本趋势图...")
        trend_chart = cost_chart_gen.generate_cost_trend_chart('data/cost_history.csv')
        if trend_chart:
            all_charts['cost_trend'] = trend_chart
            print("   ✅ 成本趋势图已生成")
    except Exception as e:
        print(f"   ❌ 成本图表生成失败: {e}")
    
    # 预测图表
    try:
        print("   生成价格预测图表...")
        prediction_charts = prediction_chart_gen.generate_all_charts(cost_data['predictions'])
        all_charts.update(prediction_charts)
        print(f"   ✅ 价格预测图表已生成 ({len(prediction_charts)} 个)")
    except Exception as e:
        print(f"   ❌ 价格预测图表生成失败: {e}")
    
    # 技术指标图表
    try:
        print("   生成技术指标图表...")
        technical_charts = technical_chart_gen.generate_all_charts(cost_data['predictions'])
        all_charts.update(technical_charts)
        print(f"   ✅ 技术指标图表已生成 ({len(technical_charts)} 个)")
    except Exception as e:
        print(f"   ❌ 技术指标图表生成失败: {e}")
    
    # 6. 生成仪表板
    print("\n🖥️ 生成仪表板...")
    try:
        dashboard_path = dashboard_gen.generate_dashboard(cost_data, all_charts)
        print(f"✅ 仪表板已生成: {dashboard_path}")
    except Exception as e:
        print(f"❌ 仪表板生成失败: {e}")
        return
    
    # 7. 输出结果摘要
    print("\n" + "=" * 80)
    print("🎉 分析完成！")
    print(f"📁 仪表板文件: {dashboard_path}")
    print(f"💰 当前总成本: ¥{cost_data['total_cost']:.2f}")
    print(f"📊 成本变化: ¥{cost_data['cost_change']:.2f} ({cost_data['cost_change_pct']:.2f}%)")
    print(f"📈 生成图表数量: {len(all_charts)} 个")
    
    # 显示预测信息
    print("\n🔮 价格预测摘要:")
    for symbol, prediction in cost_data['predictions'].items():
        if not prediction.get('error'):
            try:
                price_pred = prediction.get('price_prediction', {})
                if price_pred:
                    current_price = prediction.get('current_price', 0)
                    predicted_price = price_pred.get('predicted_price', 0)
                    confidence = prediction.get('confidence', 0)
                    recommendation = prediction.get('recommendation', '未知')
                    comprehensive_score = prediction.get('comprehensive_score', 0)
                    
                    print(f"   {symbol}: {recommendation}")
                    print(f"     当前价格: ¥{current_price:.2f}")
                    print(f"     预测价格: ¥{predicted_price:.2f}")
                    print(f"     预测置信度: {confidence:.1f}%")
                    print(f"     综合评分: {comprehensive_score:.1f}/100")
                    
                    # 显示AI导师分析
                    ai_analysis = prediction.get('ai_mentor_analysis', {})
                    if ai_analysis and not ai_analysis.get('error'):
                        market_sentiment = ai_analysis.get('market_sentiment', '未知')
                        confidence_level = ai_analysis.get('confidence_level', '未知')
                        print(f"     AI情绪: {market_sentiment}")
                        print(f"     AI置信度: {confidence_level}")
                        
                        # 显示风险评估
                        risk_assessment = ai_analysis.get('risk_assessment', {})
                        if risk_assessment:
                            risk_level = risk_assessment.get('risk_level', '未知')
                            risk_factors = risk_assessment.get('risk_factors', [])
                            print(f"     风险等级: {risk_level}")
                            if risk_factors:
                                print(f"     风险因素: {', '.join(risk_factors)}")
                    
                    # 显示技术指标信号
                    tech = prediction.get('technical_analysis', {})
                    if tech:
                        print(f"     技术信号: EMA({tech.get('ema_trend', 'neutral')}) "
                              f"MACD({tech.get('macd_signal', 'neutral')}) "
                              f"KDJ({tech.get('kdj_signal', 'neutral')})")
                    
                    print()
            except Exception as e:
                print(f"   {symbol}: 预测信息解析失败 - {e}")
        else:
            print(f"   {symbol}: 预测失败 - {prediction.get('error_message', '未知错误')}")
    
    # 8. 生成分析报告
    print("\n📝 生成分析报告...")
    try:
        report_path = generate_analysis_report(cost_data, all_charts, ai_insights)
        print(f"✅ 分析报告已生成: {report_path}")
    except Exception as e:
        print(f"⚠️ 分析报告生成失败: {e}")
    
    print("\n🎯 系统运行完成！请打开仪表板查看详细分析结果。")
    print("🤖 AI导师已为您提供智能趋势研判和投资建议。")

def generate_analysis_report(cost_data: dict, charts: dict, ai_insights: dict) -> str:
    """生成分析报告"""
    report_dir = 'output/reports'
    os.makedirs(report_dir, exist_ok=True)
    
    report_path = os.path.join(report_dir, f'analysis_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("电池成本监测与价格预测系统 - 分析报告\n")
        f.write("🎯 专注分析: 碳酸锂(LC)\n")
        f.write("🤖 集成AI导师: 趋势研判智能体\n")
        f.write("=" * 60 + "\n")
        f.write(f"生成时间: {cost_data['timestamp']}\n")
        f.write(f"数据源: {cost_data.get('data_source', 'unknown')}\n\n")
        
        # 成本摘要
        f.write("成本分析摘要:\n")
        f.write(f"  总成本: ¥{cost_data['total_cost']:.2f}\n")
        f.write(f"  成本变化: ¥{cost_data['cost_change']:.2f} ({cost_data['cost_change_pct']:.2f}%)\n")
        f.write(f"  基准成本: ¥{cost_data.get('baseline_total_cost', 10000):.2f}\n\n")
        
        # 材料详情
        f.write("材料成本详情:\n")
        for symbol, material in cost_data['materials'].items():
            f.write(f"  {material['name']}:\n")
            f.write(f"    当前价格: ¥{material['current_price']:.2f}/吨\n")
            f.write(f"    基准价格: ¥{material['baseline_price']:.2f}/吨\n")
            f.write(f"    当前成本: ¥{material['current_cost']:.2f}\n")
            f.write(f"    基准成本: ¥{material['baseline_cost']:.2f}\n")
            f.write(f"    成本变化: {'+' if material['cost_change'] >= 0 else ''}¥{material['cost_change']:.2f}\n")
            f.write(f"    变化百分比: {'+' if material['cost_change_pct'] >= 0 else ''}{material['cost_change_pct']:.2f}%\n\n")
        
        # AI导师洞察
        if ai_insights and not ai_insights.get('error'):
            f.write("AI导师洞察:\n")
            cost_trend = ai_insights.get('cost_trend', {})
            f.write(f"  成本趋势: {cost_trend.get('trend', '未知')}\n")
            f.write(f"  变化幅度: {cost_trend.get('change_pct', 0):.2f}%\n")
            f.write(f"  关注状态: {cost_trend.get('status', '未知')}\n")
            
            recommendations = ai_insights.get('recommendations', [])
            if recommendations:
                f.write("  AI建议:\n")
                for i, rec in enumerate(recommendations, 1):
                    f.write(f"    {i}. {rec}\n")
            f.write("\n")
        
        # 预测摘要
        f.write("价格预测摘要:\n")
        for symbol, prediction in cost_data['predictions'].items():
            if not prediction.get('error'):
                f.write(f"  {symbol}:\n")
                f.write(f"    当前价格: ¥{prediction.get('current_price', 0):.2f}\n")
                f.write(f"    预测价格: ¥{prediction.get('price_prediction', {}).get('predicted_price', 0):.2f}\n")
                f.write(f"    预测置信度: {prediction.get('confidence', 0):.1f}%\n")
                f.write(f"    投资建议: {prediction.get('recommendation', '未知')}\n")
                f.write(f"    综合评分: {prediction.get('comprehensive_score', 0):.1f}/100\n")
                
                # AI导师分析
                ai_analysis = prediction.get('ai_mentor_analysis', {})
                if ai_analysis and not ai_analysis.get('error'):
                    f.write(f"    AI情绪: {ai_analysis.get('market_sentiment', '未知')}\n")
                    f.write(f"    AI置信度: {ai_analysis.get('confidence_level', '未知')}\n")
                    
                    risk_assessment = ai_analysis.get('risk_assessment', {})
                    if risk_assessment:
                        f.write(f"    风险等级: {risk_assessment.get('risk_level', '未知')}\n")
                        risk_factors = risk_assessment.get('risk_factors', [])
                        if risk_factors:
                            f.write(f"    风险因素: {', '.join(risk_factors)}\n")
                
                f.write("\n")
            else:
                f.write(f"  {symbol}: 预测失败 - {prediction.get('error_message', '未知错误')}\n\n")
        
        # 图表列表
        f.write("生成图表:\n")
        for chart_name, chart_path in charts.items():
            f.write(f"  {chart_name}: {chart_path}\n")
    
    return report_path

if __name__ == "__main__":
    main()
