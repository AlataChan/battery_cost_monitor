import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from config import CHART_CONFIG
import os

class ChartGenerator:
    def __init__(self):
        self.config = CHART_CONFIG
        
    def generate_cost_composition_chart(self, cost_data: dict, save_path: str = 'output/charts/'):
        """Generate cost composition pie chart"""
        os.makedirs(save_path, exist_ok=True)
        
        # Prepare data with English labels
        labels = []
        values = []
        for material_key, data in cost_data['materials'].items():
            if material_key == 'LC':
                labels.append('Lithium Carbonate (Battery Grade)')
            else:
                labels.append(data['name'])  # fallback to original name
            values.append(data['current_cost'])
        
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
        
        # Calculate percentage based on standard total cost of 10000
        standard_total_cost = 10000
        current_total_cost = sum(values)
        percentage_of_standard = (current_total_cost / standard_total_cost) * 100
        
        # Create chart
        plt.figure(figsize=self.config['figure_size'], dpi=self.config['dpi'])
        
        # Custom autopct to show actual percentages relative to standard cost
        def autopct_format(pct):
            # pct is the percentage within the pie
            # We want to show the percentage relative to standard cost
            actual_value = (pct / 100) * current_total_cost
            pct_of_standard = (actual_value / standard_total_cost) * 100
            return f'{pct_of_standard:.1f}%'
        
        plt.pie(values, labels=labels, colors=colors, autopct=autopct_format, startangle=90)
        plt.title(f'Battery Material Cost Composition\n({percentage_of_standard:.1f}% of Standard Cost ¥{standard_total_cost})', 
                 fontsize=16, fontweight='bold')
        plt.axis('equal')
        
        # 保存图表
        filename = os.path.join(save_path, 'cost_composition.png')
        plt.savefig(filename, dpi=self.config['dpi'], bbox_inches='tight')
        plt.close()
        
        print(f"Cost composition chart saved: {filename}")
        return filename
    
    def generate_cost_trend_chart(self, cost_history_file: str, save_path: str = 'output/charts/'):
        """Generate cost trend chart"""
        if not os.path.exists(cost_history_file):
            print(f"Cost history file not found: {cost_history_file}")
            return None
            
        os.makedirs(save_path, exist_ok=True)
        
        # Read historical data
        df = pd.read_csv(cost_history_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Create chart
        plt.figure(figsize=self.config['figure_size'], dpi=self.config['dpi'])
        
        # Total cost trend
        plt.subplot(2, 1, 1)
        plt.plot(df['timestamp'], df['total_cost'], 'b-', linewidth=2, label='Total Cost')
        plt.axhline(y=3308, color='r', linestyle='--', label='Baseline Cost (¥3308)')
        plt.title('Battery Total Cost Trend', fontsize=14, fontweight='bold')
        plt.ylabel('Cost (¥)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Cost change percentage
        plt.subplot(2, 1, 2)
        plt.plot(df['timestamp'], df['cost_change_pct'], 'g-', linewidth=2, label='Cost Change %')
        plt.axhline(y=0, color='r', linestyle='--', label='Baseline')
        plt.title('Cost Change Percentage', fontsize=14, fontweight='bold')
        plt.ylabel('Change (%)')
        plt.xlabel('Date')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Format x-axis
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # Save chart
        filename = os.path.join(save_path, 'cost_trend.png')
        plt.savefig(filename, dpi=self.config['dpi'], bbox_inches='tight')
        plt.close()
        
        print(f"Cost trend chart saved: {filename}")
        return filename