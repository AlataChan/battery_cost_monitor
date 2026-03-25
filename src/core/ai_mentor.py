#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI导师模块 - 趋势研判智能体
集成DeepSeek API，提供智能趋势分析和投资建议
"""

import json
import os
import requests
import logging
from typing import Dict, Optional
from datetime import datetime
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config import AI_MENTOR_CONFIG

logger = logging.getLogger(__name__)

class AIMentor:
    """AI导师 - 趋势研判智能体"""
    
    def __init__(self):
        self.config = AI_MENTOR_CONFIG
        self.prompt_data = None
        self._load_prompt_data()
        
    def _load_prompt_data(self):
        """加载AI导师提示词配置"""
        try:
            prompt_file = self.config['prompt_file']
            if os.path.exists(prompt_file):
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    self.prompt_data = json.load(f)
                logger.info(f"成功加载AI导师配置文件: {prompt_file}")
            else:
                logger.warning(f"AI导师配置文件不存在: {prompt_file}")
                self.prompt_data = self._get_default_prompt()
        except Exception as e:
            logger.error(f"加载AI导师配置文件失败: {e}")
            self.prompt_data = self._get_default_prompt()
    
    def _get_default_prompt(self) -> Dict:
        """获取默认提示词配置"""
        return {
            "agentPrompt": {
                "persona": "你是一位专业的趋势研判专家，专注于电池材料价格走势分析。",
                "coreMethodology": {
                    "foundation": {
                        "pillars": [
                            "技术分析: 结合EMA、MACD、KDJ、布林带等多重技术指标",
                            "市场洞察: 分析行业周期、供需关系、政策影响",
                            "智能预测: 基于技术指标一致性和市场结构的综合判断"
                        ]
                    }
                }
            }
        }
    
    def get_trend_analysis(self, market_data: Dict) -> str:
        """
        获取AI导师的趋势分析
        
        Args:
            market_data: 包含市场数据的结构化字典
            
        Returns:
            AI导师的详细分析结果
        """
        if not self.prompt_data:
            return "错误: AI导师的配置文件未加载。"
        
        try:
            # 构建系统提示词
            system_prompt = self._build_system_prompt()
            
            # 构建用户提示词
            user_prompt = self._build_user_prompt(market_data)
            
            # 调用AI API
            analysis = self._call_ai_api(system_prompt, user_prompt)
            
            return analysis
            
        except Exception as e:
            logger.error(f"获取AI导师分析时出错: {e}")
            return f"获取AI导师分析时出错: {e}"
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        if not self.prompt_data:
            return "你是一位专业的趋势研判专家。"
        
        agent_prompt = self.prompt_data.get("agentPrompt", {})
        persona = agent_prompt.get("persona", "你是一位专业的趋势研判专家。")
        
        # 构建完整的系统提示词
        system_prompt = f"""
{persona}

请严格按照以下格式回复，并注意以下要求：
1. 使用中文回复
2. 专注于趋势研判，不要给出具体的买卖建议
3. 重点关注技术指标一致性、市场结构和风险收益比
4. 考虑电池材料行业的特殊性（周期性、政策敏感性等）
5. 结合布林带位置判断超买超卖状态和趋势强度

## 趋势研判建议
**方向**: [看涨趋势/看跌趋势/震荡整理/观察等待]
**目标价位**: [具体价格]（[价格相对性描述]）
**时间框架**: [建议持有天数范围]
**仓位建议**: [百分比]（[基于信号强度的说明]）

## 风险管理
**止损**: [具体条件或百分比]
**止盈**: [分层策略描述]
**动态调整**: [调整策略说明]

## 分析依据
[使用技术分析术语的详细分析，重点关注指标一致性]

请基于以上格式进行分析。
"""
        return system_prompt
    
    def _build_user_prompt(self, market_data: Dict) -> str:
        """构建用户提示词"""
        # 过滤敏感数据，保留必要的技术指标信息
        filtered_data = {
            'symbol': market_data.get('symbol'),
            'timestamp': market_data.get('timestamp'),
            'price': market_data.get('price'),
            'signal_type': market_data.get('signal_type'),
            'signal_strength': market_data.get('signal_strength'),
            # 技术指标数据
            'EMA8': market_data.get('EMA8'),
            'EMA21': market_data.get('EMA21'),
            'EMA55': market_data.get('EMA55'),
            'K_value': market_data.get('K_value'),
            'D_value': market_data.get('D_value'),
            'J_value': market_data.get('J_value'),
            'MACD': market_data.get('MACD'),
            'volume': market_data.get('volume'),
            'vol_ratio': market_data.get('vol_ratio'),
            # 布林带分析数据
            'bb_position': market_data.get('bb_position'),
            'bb_overbought': market_data.get('bb_overbought'),
            'bb_oversold': market_data.get('bb_oversold'),
            'bb_trend_strength': market_data.get('bb_trend_strength'),
            # 趋势分析
            'trend_short': market_data.get('trend_short'),
            'trend_medium': market_data.get('trend_medium'),
            'trend_long': market_data.get('trend_long'),
            'daily_trend_short': market_data.get('daily_trend_short'),
            'daily_trend_medium': market_data.get('daily_trend_medium'),
            # 价格变化
            'price_change_pct': market_data.get('price_change_pct')
        }
        
        user_prompt = f"""你好，TrendMaster。我的电池材料趋势分析系统检测到一个潜在的信号，请按照结论优先的格式进行分析。

请严格按照以下格式回复，并注意以下要求：
1. 不要在分析中提及具体的技术指标名称（如EMA、MACD、KDJ、威廉指标等）
2. 使用通用的技术分析术语（如均线、动量、趋势、成交量、布林带等）
3. 重点关注价格行为、成交量变化、市场结构和价格在布林带中的位置
4. 考虑电池材料市场的特殊性（周期性、政策敏感性、供需关系等）
5. 结合布林带位置判断超买超卖状态和趋势强度

## 趋势研判建议
**方向**: [看涨趋势/看跌趋势/震荡整理/观察等待]
**目标价位**: [具体价格]（[价格相对性描述]）
**时间框架**: [建议持有天数范围]
**仓位建议**: [百分比]（[基于信号强度的说明]）

## 风险管理
**止损**: [具体条件或百分比]
**止盈**: [分层策略描述]
**动态调整**: [调整策略说明]

## 分析依据
[使用通用技术分析术语的详细分析，避免暴露具体指标名称]

以下是相关市场数据：
{json.dumps(filtered_data, indent=2, ensure_ascii=False, default=str)}"""
        
        return user_prompt
    
    def _call_ai_api(self, system_prompt: str, user_prompt: str) -> str:
        """
        调用DeepSeek AI API
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            
        Returns:
            AI返回的分析结果
        """
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            logger.error("错误: DEEPSEEK_API_KEY 环境变量未设置。")
            return "错误: DeepSeek API Key未配置。"
        
        url = "https://api.deepseek.com/chat/completions"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        payload = {
            "model": self.config['model'],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.config['temperature'],
            "max_tokens": self.config['max_tokens'],
            "stream": False
        }
        
        try:
            logger.info("正在调用DeepSeek AI API...")
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            content = data['choices'][0]['message']['content']
            logger.info("成功从DeepSeek AI API获取分析。")
            return content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"调用DeepSeek API时发生网络错误: {e}")
            return f"错误: 调用DeepSeek API时发生网络错误: {e}"
        except KeyError:
            logger.error(f"从DeepSeek API返回的数据格式不正确: {response.text}")
            return "错误: 从DeepSeek API返回的数据格式不正确。"
        except Exception as e:
            logger.error(f"调用DeepSeek API时发生未知错误: {e}")
            return f"错误: 调用DeepSeek API时发生未知错误: {e}"
    
    def analyze_market_sentiment(self, market_data: Dict) -> Dict:
        """
        分析市场情绪
        
        Args:
            market_data: 市场数据
            
        Returns:
            市场情绪分析结果
        """
        try:
            # 获取AI分析
            ai_analysis = self.get_trend_analysis(market_data)
            
            # 分析结果
            sentiment_analysis = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'symbol': market_data.get('symbol'),
                'ai_analysis': ai_analysis,
                'market_sentiment': self._extract_sentiment(ai_analysis),
                'confidence_level': self._extract_confidence(ai_analysis),
                'risk_assessment': self._assess_risk(market_data)
            }
            
            return sentiment_analysis
            
        except Exception as e:
            logger.error(f"分析市场情绪时出错: {e}")
            return {
                'error': True,
                'error_message': str(e),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def _extract_sentiment(self, ai_analysis: str) -> str:
        """从AI分析中提取市场情绪"""
        if '看涨' in ai_analysis or '上涨' in ai_analysis:
            return '看涨'
        elif '看跌' in ai_analysis or '下跌' in ai_analysis:
            return '看跌'
        elif '震荡' in ai_analysis or '整理' in ai_analysis:
            return '震荡'
        else:
            return '中性'
    
    def _extract_confidence(self, ai_analysis: str) -> str:
        """从AI分析中提取置信度"""
        if '强烈' in ai_analysis:
            return '高'
        elif '谨慎' in ai_analysis:
            return '中'
        elif '观望' in ai_analysis:
            return '低'
        else:
            return '中'
    
    def _assess_risk(self, market_data: Dict) -> Dict:
        """评估市场风险"""
        risk_score = 0
        risk_factors = []
        
        # 基于技术指标评估风险
        if market_data.get('signal_strength', 0) >= 4:
            risk_score += 20
            risk_factors.append('信号强度高')
        
        if market_data.get('vol_ratio', 0) > 2:
            risk_score += 15
            risk_factors.append('成交量异常')
        
        if market_data.get('bb_overbought', False):
            risk_score += 10
            risk_factors.append('超买状态')
        
        if market_data.get('bb_oversold', False):
            risk_score += 10
            risk_factors.append('超卖状态')
        
        # 风险等级
        if risk_score >= 40:
            risk_level = '高'
        elif risk_score >= 20:
            risk_level = '中'
        else:
            risk_level = '低'
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'risk_factors': risk_factors
        }
