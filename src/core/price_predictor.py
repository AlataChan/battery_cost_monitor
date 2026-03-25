import pandas as pd
from datetime import datetime, timedelta
from typing import Dict
import sys
import os

# 添加gamma_shock_BYTE.py所在目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from gamma_shock_BYTE import (
    get_futures_minute_data, 
    get_futures_daily_data,
    calculate_technical_indicators,
    calculate_daily_technical_indicators
)

# 导入AI导师模块
from ai_mentor import AIMentor

class PricePredictor:
    """基于技术指标和AI导师的价格预测器"""
    
    def __init__(self):
        self.prediction_horizon = 5  # 预测未来5个交易日
        self.ai_mentor = AIMentor()  # AI导师实例
        
    def predict_material_price(self, symbol: str) -> Dict:
        """预测指定材料的价格走势"""
        try:
            # 获取分钟线和日线数据
            futures_data = get_futures_minute_data(f"{symbol}0")
            daily_data = get_futures_daily_data(f"{symbol}0")
            
            if futures_data is None or daily_data is None:
                return self._create_error_prediction(f"无法获取{symbol}数据")
            
            # 计算技术指标
            futures_data = calculate_technical_indicators(futures_data)
            daily_data = calculate_daily_technical_indicators(daily_data)
            
            # 生成技术指标预测
            technical_prediction = self._generate_prediction(symbol, futures_data, daily_data)
            
            # 获取AI导师分析
            ai_analysis = self._get_ai_analysis(symbol, technical_prediction)
            
            # 综合预测结果
            comprehensive_prediction = self._combine_predictions(technical_prediction, ai_analysis)
            
            return comprehensive_prediction
            
        except Exception as e:
            return self._create_error_prediction(f"预测{symbol}时出错: {str(e)}")
    
    def _get_ai_analysis(self, symbol: str, technical_prediction: Dict) -> Dict:
        """获取AI导师分析"""
        try:
            # 构建市场数据
            market_data = self._build_market_data(symbol, technical_prediction)
            
            # 调用AI导师
            ai_analysis = self.ai_mentor.analyze_market_sentiment(market_data)
            
            return ai_analysis
            
        except Exception as e:
            print(f"获取{symbol} AI分析失败: {e}")
            return {
                'error': True,
                'error_message': str(e),
                'ai_analysis': 'AI分析暂时不可用'
            }
    
    def _build_market_data(self, symbol: str, technical_prediction: Dict) -> Dict:
        """构建市场数据供AI导师分析"""
        return {
            'symbol': symbol,
            'timestamp': technical_prediction.get('timestamp', ''),
            'price': technical_prediction.get('current_price', 0),
            'signal_type': technical_prediction.get('technical_analysis', {}).get('overall_signal', 'neutral'),
            'signal_strength': self._calculate_signal_strength(technical_prediction),
            'EMA8': technical_prediction.get('technical_analysis', {}).get('ema_trend', 'neutral'),
            'EMA21': technical_prediction.get('technical_analysis', {}).get('ema_trend', 'neutral'),
            'EMA55': technical_prediction.get('technical_analysis', {}).get('ema_trend', 'neutral'),
            'K_value': 50,  # 默认值
            'D_value': 50,  # 默认值
            'J_value': 50,  # 默认值
            'MACD': technical_prediction.get('technical_analysis', {}).get('macd_signal', 'neutral'),
            'volume': 1,  # 默认值
            'vol_ratio': 1,  # 默认值
            'bb_position': technical_prediction.get('technical_analysis', {}).get('bb_position', 'middle'),
            'bb_overbought': technical_prediction.get('technical_analysis', {}).get('bb_position') == 'above_upper',
            'bb_oversold': technical_prediction.get('technical_analysis', {}).get('bb_position') == 'below_lower',
            'bb_trend_strength': '中性',
            'trend_short': technical_prediction.get('technical_analysis', {}).get('ema_trend', 'neutral'),
            'trend_medium': technical_prediction.get('technical_analysis', {}).get('ema_trend', 'neutral'),
            'trend_long': technical_prediction.get('technical_analysis', {}).get('ema_trend', 'neutral'),
            'daily_trend_short': technical_prediction.get('technical_analysis', {}).get('ema_trend', 'neutral'),
            'daily_trend_medium': technical_prediction.get('technical_analysis', {}).get('ema_trend', 'neutral'),
            'price_change_pct': technical_prediction.get('price_prediction', {}).get('price_change_pct', 0)
        }
    
    def _calculate_signal_strength(self, technical_prediction: Dict) -> int:
        """计算信号强度"""
        tech_analysis = technical_prediction.get('technical_analysis', {})
        
        # 计算看涨信号数量
        bullish_signals = sum([
            tech_analysis.get('ema_trend') == 'bullish',
            tech_analysis.get('macd_signal') == 'bullish',
            tech_analysis.get('kdj_signal') == 'bullish',
            tech_analysis.get('bb_position') in ['above_middle', 'above_upper'],
            tech_analysis.get('volume_signal') == 'high'
        ])
        
        # 计算看跌信号数量
        bearish_signals = sum([
            tech_analysis.get('ema_trend') == 'bearish',
            tech_analysis.get('macd_signal') == 'bearish',
            tech_analysis.get('kdj_signal') == 'bearish',
            tech_analysis.get('bb_position') in ['below_middle', 'below_lower'],
            tech_analysis.get('volume_signal') == 'high'
        ])
        
        # 返回信号强度
        if bullish_signals > bearish_signals:
            return min(bullish_signals + 1, 5)  # 最大强度5
        elif bearish_signals > bullish_signals:
            return min(bearish_signals + 1, 5)  # 最大强度5
        else:
            return 1  # 中性信号
    
    def _combine_predictions(self, technical_prediction: Dict, ai_analysis: Dict) -> Dict:
        """综合技术指标预测和AI分析"""
        # 基础预测结果
        combined_prediction = technical_prediction.copy()
        
        # 添加AI分析结果
        if not ai_analysis.get('error'):
            combined_prediction['ai_mentor_analysis'] = ai_analysis
            
            # 提升预测置信度
            ai_confidence_boost = 0.15  # AI分析提升15%置信度
            combined_prediction['confidence'] = min(
                combined_prediction.get('confidence', 0) + ai_confidence_boost * 100, 
                100
            )
            
            # 更新投资建议
            if ai_analysis.get('market_sentiment'):
                combined_prediction['ai_recommendation'] = ai_analysis['market_sentiment']
            
            # 添加风险评估
            if ai_analysis.get('risk_assessment'):
                combined_prediction['risk_assessment'] = ai_analysis['risk_assessment']
        else:
            combined_prediction['ai_mentor_analysis'] = {
                'status': 'unavailable',
                'message': 'AI分析暂时不可用'
            }
        
        # 添加综合评分
        combined_prediction['comprehensive_score'] = self._calculate_comprehensive_score(combined_prediction)
        
        return combined_prediction
    
    def _calculate_comprehensive_score(self, prediction: Dict) -> float:
        """计算综合评分"""
        score = 0
        
        # 技术指标评分 (40%)
        tech_score = prediction.get('confidence', 0) * 0.4
        score += tech_score
        
        # AI分析评分 (30%)
        ai_analysis = prediction.get('ai_mentor_analysis', {})
        if not ai_analysis.get('error'):
            ai_confidence = ai_analysis.get('confidence_level', '中')
            ai_score_map = {'高': 30, '中': 20, '低': 10}
            score += ai_score_map.get(ai_confidence, 15)
        else:
            score += 15  # 默认中等分数
        
        # 风险评分 (30%)
        risk_assessment = prediction.get('risk_assessment', {})
        if risk_assessment:
            risk_level = risk_assessment.get('risk_level', '中')
            risk_score_map = {'低': 30, '中': 20, '高': 10}
            score += risk_score_map.get(risk_level, 20)
        else:
            score += 20  # 默认中等分数
        
        return min(score, 100)
    
    def _generate_prediction(self, symbol: str, futures_data: pd.DataFrame, daily_data: pd.DataFrame) -> Dict:
        """生成价格预测"""
        current_price = futures_data['close'].iloc[-1]
        current_row = futures_data.iloc[-1]
        daily_current = daily_data.iloc[-1] if not daily_data.empty else None
        
        # 技术指标分析
        technical_analysis = self._analyze_technical_indicators(current_row, daily_current)
        
        # 趋势预测
        trend_prediction = self._predict_trend(futures_data, daily_data)
        
        # 价格区间预测
        price_range = self._predict_price_range(current_price, technical_analysis, trend_prediction)
        
        # 预测置信度
        confidence = self._calculate_confidence(technical_analysis, trend_prediction)
        
        return {
            'symbol': symbol,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_price': current_price,
            'prediction_horizon': self.prediction_horizon,
            'technical_analysis': technical_analysis,
            'trend_prediction': trend_prediction,
            'price_prediction': price_range,
            'confidence': confidence,
            'recommendation': self._generate_recommendation(technical_analysis, trend_prediction)
        }
    
    def _analyze_technical_indicators(self, current_row: pd.Series, daily_current: pd.Series) -> Dict:
        """分析技术指标"""
        analysis = {
            'ema_trend': 'neutral',
            'macd_signal': 'neutral',
            'kdj_signal': 'neutral',
            'bb_position': 'middle',
            'volume_signal': 'normal',
            'overall_signal': 'neutral'
        }
        
        # EMA趋势分析
        if current_row['EMA8'] > current_row['EMA21'] > current_row['EMA55']:
            analysis['ema_trend'] = 'bullish'
        elif current_row['EMA8'] < current_row['EMA21'] < current_row['EMA55']:
            analysis['ema_trend'] = 'bearish'
        
        # MACD信号分析
        if current_row['MACD'] > 0 and current_row['DIF'] > current_row['DEA']:
            analysis['macd_signal'] = 'bullish'
        elif current_row['MACD'] < 0 and current_row['DIF'] < current_row['DEA']:
            analysis['macd_signal'] = 'bearish'
        
        # KDJ信号分析
        if current_row['J'] > current_row['K'] > current_row['D']:
            analysis['kdj_signal'] = 'bullish'
        elif current_row['J'] < current_row['K'] < current_row['D']:
            analysis['kdj_signal'] = 'bearish'
        
        # 布林带位置分析
        if daily_current is not None:
            if daily_current['close'] > daily_current['daily_BB_upper']:
                analysis['bb_position'] = 'above_upper'
            elif daily_current['close'] < daily_current['daily_BB_lower']:
                analysis['bb_position'] = 'below_lower'
            elif daily_current['close'] > daily_current['daily_BB_middle']:
                analysis['bb_position'] = 'above_middle'
            else:
                analysis['bb_position'] = 'below_middle'
        
        # 成交量分析
        if current_row['volume'] > current_row['VOL_MA10'] * 1.5:
            analysis['volume_signal'] = 'high'
        elif current_row['volume'] < current_row['VOL_MA10'] * 0.5:
            analysis['volume_signal'] = 'low'
        
        # 综合信号
        bullish_signals = sum([
            analysis['ema_trend'] == 'bullish',
            analysis['macd_signal'] == 'bullish',
            analysis['kdj_signal'] == 'bullish',
            analysis['bb_position'] in ['above_middle', 'above_upper'],
            analysis['volume_signal'] == 'high'
        ])
        
        bearish_signals = sum([
            analysis['ema_trend'] == 'bearish',
            analysis['macd_signal'] == 'bearish',
            analysis['kdj_signal'] == 'bearish',
            analysis['bb_position'] in ['below_middle', 'below_lower'],
            analysis['volume_signal'] == 'high'
        ])
        
        if bullish_signals > bearish_signals:
            analysis['overall_signal'] = 'bullish'
        elif bearish_signals > bullish_signals:
            analysis['overall_signal'] = 'bearish'
        
        return analysis
    
    def _predict_trend(self, futures_data: pd.DataFrame, daily_data: pd.DataFrame) -> Dict:
        """预测价格趋势"""
        # 基于技术指标的趋势预测
        _ = daily_data  # 保留参数但标记为未使用
        
        # 计算移动平均趋势
        ema8_trend = futures_data['EMA8'].diff().iloc[-5:].mean()
        ema21_trend = futures_data['EMA21'].diff().iloc[-5:].mean()
        
        # 计算价格动量
        price_momentum = futures_data['close'].pct_change().iloc[-5:].mean()
        
        # 趋势强度
        trend_strength = abs(ema8_trend) + abs(ema21_trend) + abs(price_momentum)
        
        return {
            'ema8_trend': ema8_trend,
            'ema21_trend': ema21_trend,
            'price_momentum': price_momentum,
            'trend_strength': trend_strength,
            'trend_direction': 'up' if ema8_trend > 0 else 'down',
            'trend_confidence': min(trend_strength * 100, 100)
        }
    
    def _predict_price_range(self, current_price: float, technical_analysis: Dict, trend_prediction: Dict) -> Dict:
        """预测价格区间 - 优化版本"""
        # 获取原始趋势强度
        raw_volatility = trend_prediction['trend_strength']
        trend_direction = trend_prediction['trend_direction']
        
        # 1. 缩放趋势强度到5%合理范围内
        scaled_volatility = self._scale_trend_strength(raw_volatility)
        
        # 2. 基于趋势方向计算初始价格变化
        if trend_direction == 'up':
            initial_price_change_pct = scaled_volatility  # 上涨使用缩放后的值
        else:
            initial_price_change_pct = -scaled_volatility  # 下跌使用缩放后的值
        
        # 3. 应用布林线均值回归机制
        bb_adjusted_change_pct = self._apply_bollinger_mean_reversion(
            current_price, initial_price_change_pct, technical_analysis
        )
        
        # 4. 应用±8%硬限制保护
        final_price_change_pct = self._apply_price_limits(bb_adjusted_change_pct)
        
        # 计算最终预测价格
        predicted_price = current_price * (1 + final_price_change_pct / 100)
        
        # 计算置信区间（基于缩放后的波动率）
        confidence_interval = current_price * scaled_volatility * 0.3 / 100
        
        return {
            'predicted_price': predicted_price,
            'price_change': predicted_price - current_price,
            'price_change_pct': final_price_change_pct,
            'raw_volatility': raw_volatility,
            'scaled_volatility': scaled_volatility,
            'bb_adjustment': bb_adjusted_change_pct - initial_price_change_pct,
            'confidence_upper': predicted_price + confidence_interval,
            'confidence_lower': predicted_price - confidence_interval,
            'prediction_date': (datetime.now() + timedelta(days=self.prediction_horizon)).strftime('%Y-%m-%d')
        }
    
    def _calculate_confidence(self, technical_analysis: Dict, trend_prediction: Dict) -> float:
        """计算预测置信度"""
        # 基于技术指标一致性计算置信度
        signal_consistency = 0
        total_signals = 0
        
        # 检查信号一致性
        for signal_type in ['ema_trend', 'macd_signal', 'kdj_signal']:
            if technical_analysis[signal_type] != 'neutral':
                total_signals += 1
                if technical_analysis[signal_type] == technical_analysis['overall_signal']:
                    signal_consistency += 1
        
        # 趋势强度贡献
        trend_contribution = min(trend_prediction['trend_confidence'], 100)
        
        # 综合置信度
        if total_signals > 0:
            signal_confidence = (signal_consistency / total_signals) * 100
        else:
            signal_confidence = 50
        
        # 加权平均
        confidence = (signal_confidence * 0.6 + trend_contribution * 0.4)
        
        return min(confidence, 100)
    
    def _generate_recommendation(self, technical_analysis: Dict, trend_prediction: Dict) -> str:
        """生成投资建议"""
        overall_signal = technical_analysis['overall_signal']
        trend_direction = trend_prediction['trend_direction']
        
        if overall_signal == 'bullish' and trend_direction == 'up':
            return "强烈买入"
        elif overall_signal == 'bullish':
            return "谨慎买入"
        elif overall_signal == 'bearish' and trend_direction == 'down':
            return "强烈卖出"
        elif overall_signal == 'bearish':
            return "谨慎卖出"
        else:
            return "观望等待"
    
    def _scale_trend_strength(self, raw_volatility: float) -> float:
        """将趋势强度缩放到5%合理范围内"""
        # 使用Tanh函数进行非线性缩放，将任意大的趋势强度缩放到0-5%
        # tanh(x)的值域在[-1, 1]之间，我们将其映射到[0, 5]
        import math
        
        # 对原始波动率进行标准化处理
        normalized_input = raw_volatility / 10  # 将输入值缩小10倍
        scaled_value = math.tanh(normalized_input)  # 应用tanh函数
        
        # 映射到0-5%范围
        scaled_volatility = abs(scaled_value) * 5
        
        return min(scaled_volatility, 5.0)  # 确保不超过5%
    
    def _apply_bollinger_mean_reversion(self, current_price: float, initial_change_pct: float, 
                                      technical_analysis: Dict) -> float:
        """应用布林线均值回归机制"""
        _ = current_price  # 保留参数但当前未使用
        bb_position = technical_analysis.get('bb_position', 'middle')
        
        # 根据布林线位置调整预测
        if bb_position == 'above_upper':
            # 在上轨上方，预期回归到中线以下8%
            # 如果原始预测是上涨，则减弱上涨幅度或转为下跌
            if initial_change_pct > 0:
                # 原本上涨预测，改为轻微下跌
                adjusted_change_pct = -min(initial_change_pct * 0.5, 2.0)
            else:
                # 原本下跌预测，加强下跌幅度但不超过8%
                adjusted_change_pct = initial_change_pct * 1.5
                
        elif bb_position == 'below_lower':
            # 在下轨下方，预期回归反弹，以下轨以下8%为超跌反弹点
            # 如果原始预测是下跌，则减弱下跌幅度或转为上涨
            if initial_change_pct < 0:
                # 原本下跌预测，改为轻微上涨（超跌反弹）
                adjusted_change_pct = min(abs(initial_change_pct) * 0.6, 3.0)
            else:
                # 原本上涨预测，保持但可能减弱
                adjusted_change_pct = initial_change_pct * 0.8
                
        elif bb_position == 'above_middle':
            # 在中线上方，略微减弱上涨预期
            if initial_change_pct > 0:
                adjusted_change_pct = initial_change_pct * 0.8
            else:
                adjusted_change_pct = initial_change_pct * 1.2
                
        elif bb_position == 'below_middle':
            # 在中线下方，略微减弱下跌预期
            if initial_change_pct < 0:
                adjusted_change_pct = initial_change_pct * 0.8
            else:
                adjusted_change_pct = initial_change_pct * 1.2
        else:
            # 在中线附近，保持原始预测
            adjusted_change_pct = initial_change_pct
            
        return adjusted_change_pct
    
    def _apply_price_limits(self, price_change_pct: float) -> float:
        """应用±8%价格变动硬限制保护"""
        # 设置最大单日变动幅度为8%
        max_daily_change = 8.0
        
        if price_change_pct > max_daily_change:
            return max_daily_change
        elif price_change_pct < -max_daily_change:
            return -max_daily_change
        else:
            return price_change_pct

    def _create_error_prediction(self, error_msg: str) -> Dict:
        """创建错误预测结果"""
        return {
            'error': True,
            'error_message': error_msg,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'prediction': None
        }
