import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

class TechnicalChartGenerator:
    """技术指标图表生成器"""
    
    def __init__(self):
        self.figure_size = (12, 8)
        self.dpi = 100
        
    def generate_technical_chart(self, symbol: str, save_path: str = '../../output/charts/'):
        """生成技术指标图表"""
        os.makedirs(save_path, exist_ok=True)
        
        try:
            # 导入期货数据获取函数
            import sys
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
            from gamma_shock_BYTE import (
                get_futures_minute_data,
                get_futures_daily_data,
                calculate_technical_indicators,
                calculate_daily_technical_indicators
            )
            
            # 获取数据
            futures_data = get_futures_minute_data(f"{symbol}0")
            daily_data = get_futures_daily_data(f"{symbol}0")
            
            if futures_data is None or daily_data is None:
                print(f"无法获取{symbol}数据")
                return None
            
            # 计算技术指标
            futures_data = calculate_technical_indicators(futures_data)
            daily_data = calculate_daily_technical_indicators(daily_data)
            
            # 生成图表
            chart_file = self._create_technical_chart(symbol, futures_data, daily_data, save_path)
            return chart_file
            
        except Exception as e:
            print(f"生成{symbol}技术指标图表失败: {e}")
            return None
    
    def _create_technical_chart(self, symbol: str, futures_data: pd.DataFrame, daily_data: pd.DataFrame, save_path: str):
        """创建技术指标图表"""
        fig, axes = plt.subplots(3, 2, figsize=(16, 12), dpi=self.dpi)
        fig.suptitle(f'{symbol} 技术指标分析', fontsize=16, fontweight='bold')
        
        # 1. 价格与均线
        self._plot_price_and_ma(axes[0, 0], futures_data, symbol)
        
        # 2. MACD指标
        self._plot_macd(axes[0, 1], futures_data, symbol)
        
        # 3. KDJ指标
        self._plot_kdj(axes[1, 0], futures_data, symbol)
        
        # 4. 布林带
        self._plot_bollinger_bands(axes[1, 1], daily_data, symbol)
        
        # 5. 成交量
        self._plot_volume(axes[2, 0], futures_data, symbol)
        
        # 6. 威廉指标
        self._plot_williams(axes[2, 1], futures_data, symbol)
        
        plt.tight_layout()
        
        # 保存图表
        filename = os.path.join(save_path, f'{symbol}_technical_analysis.png')
        plt.savefig(filename, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        print(f"{symbol}技术指标图表已保存: {filename}")
        return filename
    
    def _plot_price_and_ma(self, ax, data: pd.DataFrame, symbol: str):
        """绘制价格与均线"""
        # 获取最近100个数据点
        recent_data = data.tail(100)
        
        ax.plot(recent_data.index, recent_data['close'], label='收盘价', color='black', linewidth=1)
        ax.plot(recent_data.index, recent_data['EMA8'], label='EMA8', color='#FF6B6B', linewidth=1)
        ax.plot(recent_data.index, recent_data['EMA21'], label='EMA21', color='#4ECDC4', linewidth=1)
        ax.plot(recent_data.index, recent_data['EMA55'], label='EMA55', color='#45B7D1', linewidth=1)
        
        ax.set_title(f'{symbol} 价格与均线')
        ax.set_ylabel('价格')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 格式化x轴
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax.tick_params(axis='x', rotation=45)
    
    def _plot_macd(self, ax, data: pd.DataFrame, symbol: str):
        """绘制MACD指标"""
        recent_data = data.tail(100)
        
        # MACD柱状图
        colors = ['#4ECDC4' if x >= 0 else '#FF6B6B' for x in recent_data['MACD']]
        ax.bar(recent_data.index, recent_data['MACD'], color=colors, alpha=0.7, label='MACD')
        
        # DIF和DEA线
        ax.plot(recent_data.index, recent_data['DIF'], label='DIF', color='#FF6B6B', linewidth=1)
        ax.plot(recent_data.index, recent_data['DEA'], label='DEA', color='#45B7D1', linewidth=1)
        
        ax.set_title(f'{symbol} MACD指标')
        ax.set_ylabel('MACD值')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax.tick_params(axis='x', rotation=45)
    
    def _plot_kdj(self, ax, data: pd.DataFrame, symbol: str):
        """绘制KDJ指标"""
        recent_data = data.tail(100)
        
        ax.plot(recent_data.index, recent_data['K'], label='K值', color='#FF6B6B', linewidth=1)
        ax.plot(recent_data.index, recent_data['D'], label='D值', color='#4ECDC4', linewidth=1)
        ax.plot(recent_data.index, recent_data['J'], label='J值', color='#45B7D1', linewidth=1)
        
        # 添加超买超卖线
        ax.axhline(y=80, color='red', linestyle='--', alpha=0.5, label='超买线(80)')
        ax.axhline(y=20, color='green', linestyle='--', alpha=0.5, label='超卖线(20)')
        
        ax.set_title(f'{symbol} KDJ指标')
        ax.set_ylabel('KDJ值')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax.tick_params(axis='x', rotation=45)
    
    def _plot_bollinger_bands(self, ax, data: pd.DataFrame, symbol: str):
        """绘制布林带"""
        recent_data = data.tail(50)  # 日线数据，取50天
        
        ax.plot(recent_data.index, recent_data['close'], label='收盘价', color='black', linewidth=1)
        ax.plot(recent_data.index, recent_data['daily_BB_upper'], label='上轨', color='#FF6B6B', linewidth=1, linestyle='--')
        ax.plot(recent_data.index, recent_data['daily_BB_middle'], label='中轨', color='#4ECDC4', linewidth=1)
        ax.plot(recent_data.index, recent_data['daily_BB_lower'], label='下轨', color='#45B7D1', linewidth=1, linestyle='--')
        
        # 填充布林带区域
        ax.fill_between(recent_data.index, 
                       recent_data['daily_BB_upper'], 
                       recent_data['daily_BB_lower'], 
                       alpha=0.1, color='#4ECDC4')
        
        ax.set_title(f'{symbol} 布林带')
        ax.set_ylabel('价格')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.tick_params(axis='x', rotation=45)
    
    def _plot_volume(self, ax, data: pd.DataFrame, symbol: str):
        """绘制成交量"""
        recent_data = data.tail(100)
        
        # 成交量柱状图
        colors = ['#4ECDC4' if close >= open else '#FF6B6B' 
                 for close, open in zip(recent_data['close'], recent_data['open'])]
        ax.bar(recent_data.index, recent_data['volume'], color=colors, alpha=0.7, label='成交量')
        
        # 成交量均线
        ax.plot(recent_data.index, recent_data['VOL_MA5'], label='5日均量', color='#FF6B6B', linewidth=1)
        ax.plot(recent_data.index, recent_data['VOL_MA10'], label='10日均量', color='#45B7D1', linewidth=1)
        
        ax.set_title(f'{symbol} 成交量')
        ax.set_ylabel('成交量')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax.tick_params(axis='x', rotation=45)
    
    def _plot_williams(self, ax, data: pd.DataFrame, symbol: str):
        """绘制威廉指标"""
        recent_data = data.tail(100)
        
        ax.plot(recent_data.index, recent_data['ZLS'], label='ZLS(长期线)', color='#FF6B6B', linewidth=1)
        ax.plot(recent_data.index, recent_data['CZX'], label='CZX(短期线)', color='#4ECDC4', linewidth=1)
        ax.plot(recent_data.index, recent_data['HLB'], label='HLB(差值)', color='#45B7D1', linewidth=1)
        
        # 添加信号线
        ax.axhline(y=0.1, color='green', linestyle='--', alpha=0.5, label='超卖线(0.1)')
        ax.axhline(y=0.25, color='red', linestyle='--', alpha=0.5, label='超买线(0.25)')
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        ax.set_title(f'{symbol} 威廉指标')
        ax.set_ylabel('威廉值')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax.tick_params(axis='x', rotation=45)
    
    def generate_all_charts(self, predictions: dict) -> dict:
        """为所有材料生成技术指标图表"""
        charts = {}
        
        for symbol in predictions.keys():
            if not predictions[symbol].get('error'):
                try:
                    chart_file = self.generate_technical_chart(symbol)
                    if chart_file:
                        charts[f'{symbol}_technical'] = chart_file
                except Exception as e:
                    print(f"生成{symbol}技术指标图表失败: {e}")
        
        return charts
