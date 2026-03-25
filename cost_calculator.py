import pandas as pd
from datetime import datetime
from config import BATTERY_CONFIG
import sys
import os

# 添加价格预测模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'core'))
from price_predictor import PricePredictor

class BatteryCostCalculator:
    def __init__(self):
        self.config = BATTERY_CONFIG
        self.price_predictor = PricePredictor()
        
    def calculate_current_cost(self) -> dict:
        """计算当前成本（从期货系统获取实时价格）"""
        # 从期货系统获取价格
        current_prices = self._get_current_prices_from_futures()
        
        results = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_cost': 0,
            'cost_change': 0,
            'cost_change_pct': 0,
            'materials': {},
            'predictions': {},
            'data_source': 'futures_system'
        }
        
        # 计算每种材料的成本
        for symbol, config in self.config['materials'].items():
            if symbol in current_prices:
                material_cost = self._calculate_material_cost(symbol, config, current_prices[symbol])
                results['materials'][symbol] = material_cost
                results['total_cost'] += material_cost['current_cost']
                
                # 获取价格预测（包含AI导师分析）
                try:
                    prediction = self.price_predictor.predict_material_price(symbol)
                    results['predictions'][symbol] = prediction
                except Exception as e:
                    print(f"获取{symbol}价格预测失败: {e}")
                    results['predictions'][symbol] = {'error': True, 'error_message': str(e)}
        
        # 计算总成本变化
        baseline_total = self.config['baseline_total_cost']
        results['cost_change'] = results['total_cost'] - baseline_total
        results['cost_change_pct'] = (results['cost_change'] / baseline_total) * 100 if baseline_total > 0 else 0
        
        return results
    
    def _get_current_prices_from_futures(self) -> dict:
        """从期货系统获取当前价格"""
        current_prices = {}
        
        for symbol in self.config['materials'].keys():
            try:
                # 导入期货数据获取函数
                sys.path.append(os.path.join(os.path.dirname(__file__)))
                from gamma_shock_BYTE import get_futures_minute_data
                
                futures_data = get_futures_minute_data(f"{symbol}0")
                if futures_data is not None and not futures_data.empty:
                    current_prices[symbol] = futures_data['close'].iloc[-1]
                    print(f"✅ 从期货系统获取到{symbol}价格: {current_prices[symbol]:.2f}")
                else:
                    print(f"⚠️ 未获取到{symbol}数据")
            except Exception as e:
                print(f"❌ 获取{symbol}价格失败: {e}")
                # 使用基准价格作为备选
                current_prices[symbol] = self.config['materials'][symbol]['baseline_price']
                print(f"使用{symbol}基准价格: {current_prices[symbol]:.2f}")
        
        return current_prices
    
    def _calculate_material_cost(self, symbol: str, config: dict, current_price: float) -> dict:
        """计算单个材料的成本"""
        baseline_price = config['baseline_price']
        usage = config['standard_usage']
        
        # 计算成本（价格从元/吨转换为元/kg）
        current_cost = (current_price / 1000) * usage
        baseline_cost = (baseline_price / 1000) * usage
        
        cost_change = current_cost - baseline_cost
        cost_change_pct = (cost_change / baseline_cost) * 100 if baseline_cost > 0 else 0
        
        return {
            'name': config['name'],
            'current_price': current_price,
            'baseline_price': baseline_price,
            'current_cost': current_cost,
            'baseline_cost': baseline_cost,
            'cost_change': cost_change,
            'cost_change_pct': cost_change_pct,
            'usage': usage
        }
    
    def save_cost_history(self, cost_data: dict, filename: str = 'data/cost_history.csv'):
        """保存成本历史数据"""
        import os
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # 准备数据
        history_data = {
            'timestamp': [cost_data['timestamp']],
            'total_cost': [cost_data['total_cost']],
            'cost_change': [cost_data['cost_change']],
            'cost_change_pct': [cost_data['cost_change_pct']]
        }
        
        # 添加材料数据
        for symbol, material in cost_data['materials'].items():
            history_data[f'{symbol}_cost'] = [material['current_cost']]
            history_data[f'{symbol}_change'] = [material['cost_change']]
        
        df = pd.DataFrame(history_data)
        
        # 如果文件存在，追加；否则创建新文件
        if os.path.exists(filename):
            df.to_csv(filename, mode='a', header=False, index=False)
        else:
            df.to_csv(filename, index=False)
        
        print(f"成本数据已保存到: {filename}")
    
    def get_ai_insights(self, cost_data: dict) -> dict:
        """获取AI导师的成本分析洞察"""
        try:
            # 导入AI导师模块
            sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'core'))
            from ai_mentor import AIMentor
            
            ai_mentor = AIMentor()
            
            # 构建成本分析数据
            cost_analysis_data = {
                'symbol': 'LC',  # 专注碳酸锂
                'timestamp': cost_data['timestamp'],
                'price': cost_data['materials'].get('LC', {}).get('current_price', 0),
                'cost_change_pct': cost_data['cost_change_pct'],
                'total_cost': cost_data['total_cost'],
                'baseline_cost': self.config['baseline_total_cost']
            }
            
            # 获取AI分析
            ai_insights = ai_mentor.analyze_market_sentiment(cost_analysis_data)
            
            return {
                'ai_analysis': ai_insights,
                'cost_trend': self._analyze_cost_trend(cost_data),
                'recommendations': self._generate_cost_recommendations(cost_data)
            }
            
        except Exception as e:
            print(f"获取AI洞察失败: {e}")
            return {
                'error': True,
                'error_message': str(e),
                'ai_analysis': 'AI分析暂时不可用'
            }
    
    def _analyze_cost_trend(self, cost_data: dict) -> dict:
        """分析成本趋势"""
        cost_change_pct = cost_data['cost_change_pct']
        
        if cost_change_pct > 10:
            trend = '显著上涨'
            severity = '高'
        elif cost_change_pct > 5:
            trend = '温和上涨'
            severity = '中'
        elif cost_change_pct > -5:
            trend = '相对稳定'
            severity = '低'
        elif cost_change_pct > -10:
            trend = '温和下跌'
            severity = '中'
        else:
            trend = '显著下跌'
            severity = '高'
        
        return {
            'trend': trend,
            'severity': severity,
            'change_pct': cost_change_pct,
            'status': '需要关注' if abs(cost_change_pct) > 5 else '正常范围'
        }
    
    def _generate_cost_recommendations(self, cost_data: dict) -> list:
        """生成成本管理建议"""
        recommendations = []
        cost_change_pct = cost_data['cost_change_pct']
        
        if cost_change_pct > 10:
            recommendations.extend([
                "成本显著上涨，建议关注上游原材料价格走势",
                "考虑调整采购策略，寻找替代供应商",
                "评估成本转嫁的可能性"
            ])
        elif cost_change_pct > 5:
            recommendations.extend([
                "成本温和上涨，建议监控价格变化",
                "优化库存管理，平衡采购时机"
            ])
        elif cost_change_pct < -5:
            recommendations.extend([
                "成本下降，可考虑增加采购量",
                "评估长期采购合同的机会"
            ])
        else:
            recommendations.append("成本相对稳定，维持现有采购策略")
        
        return recommendations