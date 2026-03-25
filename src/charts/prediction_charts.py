import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

class PredictionChartGenerator:
    """价格预测图表生成器"""
    
    def __init__(self):
        self.figure_size = (12, 8)
        self.dpi = 100
        
    def generate_prediction_chart(self, predictions: dict, save_path: str = '../../output/charts/'):
        """生成价格预测图表"""
        os.makedirs(save_path, exist_ok=True)
        
        # 过滤有效的预测数据
        valid_predictions = {k: v for k, v in predictions.items() if not v.get('error')}
        
        if not valid_predictions:
            print("没有有效的预测数据")
            return None
        
        # 创建子图
        fig, axes = plt.subplots(2, 2, figsize=self.figure_size, dpi=self.dpi)
        fig.suptitle('电池材料价格预测分析', fontsize=16, fontweight='bold')
        
        # 1. 当前价格与预测价格对比
        self._plot_price_comparison(axes[0, 0], valid_predictions)
        
        # 2. 预测置信度
        self._plot_confidence(axes[0, 1], valid_predictions)
        
        # 3. 技术指标信号
        self._plot_technical_signals(axes[1, 0], valid_predictions)
        
        # 4. 趋势预测
        self._plot_trend_prediction(axes[1, 1], valid_predictions)
        
        plt.tight_layout()
        
        # 保存图表
        filename = os.path.join(save_path, 'price_predictions.png')
        plt.savefig(filename, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        print(f"价格预测图表已保存: {filename}")
        return filename
    
    def _plot_price_comparison(self, ax, predictions: dict):
        """绘制价格对比图"""
        symbols = list(predictions.keys())
        current_prices = [predictions[s]['current_price'] for s in symbols]
        predicted_prices = [predictions[s]['price_prediction']['predicted_price'] for s in symbols]
        
        x = np.arange(len(symbols))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, current_prices, width, label='当前价格', color='#FF6B6B')
        bars2 = ax.bar(x + width/2, predicted_prices, width, label='预测价格', color='#4ECDC4')
        
        ax.set_xlabel('材料')
        ax.set_ylabel('价格 (元/吨)')
        ax.set_title('当前价格 vs 预测价格')
        ax.set_xticks(x)
        ax.set_xticklabels(symbols)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 添加数值标签
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.0f}', ha='center', va='bottom')
    
    def _plot_confidence(self, ax, predictions: dict):
        """绘制预测置信度图"""
        symbols = list(predictions.keys())
        confidences = [predictions[s]['confidence'] for s in symbols]
        colors = ['#FF6B6B' if c < 50 else '#4ECDC4' if c < 80 else '#45B7D1' for c in confidences]
        
        bars = ax.bar(symbols, confidences, color=colors)
        ax.set_xlabel('材料')
        ax.set_ylabel('置信度 (%)')
        ax.set_title('预测置信度')
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)
        
        # 添加置信度标签
        for bar, conf in zip(bars, confidences):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{conf:.1f}%', ha='center', va='bottom')
    
    def _plot_technical_signals(self, ax, predictions: dict):
        """绘制技术指标信号图"""
        symbols = list(predictions.keys())
        
        # 提取技术指标信号
        ema_signals = []
        macd_signals = []
        kdj_signals = []
        bb_signals = []
        
        for symbol in symbols:
            tech = predictions[symbol]['technical_analysis']
            ema_signals.append(1 if tech['ema_trend'] == 'bullish' else (-1 if tech['ema_trend'] == 'bearish' else 0))
            macd_signals.append(1 if tech['macd_signal'] == 'bullish' else (-1 if tech['macd_signal'] == 'bearish' else 0))
            kdj_signals.append(1 if tech['kdj_signal'] == 'bullish' else (-1 if tech['kdj_signal'] == 'bearish' else 0))
            bb_signals.append(1 if tech['bb_position'] in ['above_middle', 'above_upper'] else (-1 if tech['bb_position'] in ['below_middle', 'below_lower'] else 0))
        
        x = np.arange(len(symbols))
        width = 0.2
        
        ax.bar(x - width*1.5, ema_signals, width, label='EMA趋势', color='#FF6B6B')
        ax.bar(x - width*0.5, macd_signals, width, label='MACD信号', color='#4ECDC4')
        ax.bar(x + width*0.5, kdj_signals, width, label='KDJ信号', color='#45B7D1')
        ax.bar(x + width*1.5, bb_signals, width, label='布林带位置', color='#96CEB4')
        
        ax.set_xlabel('材料')
        ax.set_ylabel('信号强度')
        ax.set_title('技术指标信号分析')
        ax.set_xticks(x)
        ax.set_xticklabels(symbols)
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    
    def _plot_trend_prediction(self, ax, predictions: dict):
        """绘制趋势预测图"""
        symbols = list(predictions.keys())
        trend_directions = []
        trend_confidences = []
        
        for symbol in symbols:
            trend = predictions[symbol]['trend_prediction']
            trend_directions.append(1 if trend['trend_direction'] == 'up' else -1)
            trend_confidences.append(trend['trend_confidence'])
        
        # 创建散点图
        colors = ['#4ECDC4' if d > 0 else '#FF6B6B' for d in trend_directions]
        sizes = [c * 2 for c in trend_confidences]
        
        scatter = ax.scatter(symbols, trend_confidences, c=colors, s=sizes, alpha=0.7)
        ax.set_xlabel('材料')
        ax.set_ylabel('趋势置信度 (%)')
        ax.set_title('价格趋势预测')
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)
        
        # 添加趋势方向标签
        for i, (symbol, direction) in enumerate(zip(symbols, trend_directions)):
            direction_text = "↑" if direction > 0 else "↓"
            ax.annotate(direction_text, (symbol, trend_confidences[i]), 
                       xytext=(0, 10), textcoords='offset points', 
                       ha='center', fontsize=16, fontweight='bold')
    
    def generate_all_charts(self, predictions: dict) -> dict:
        """生成所有预测图表"""
        charts = {}
        
        # 主预测图表
        main_chart = self.generate_prediction_chart(predictions)
        if main_chart:
            charts['price_predictions'] = main_chart
        
        return charts
