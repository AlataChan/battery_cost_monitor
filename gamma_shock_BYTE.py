# -*- coding: utf-8 -*-
"""
期货期权策略跟踪系统
- 应用于沪镍(NI)、碳酸锂(LC)等期货品种
- 基于双重确认升级版策略
- 利用AI导师(DeepSeek)进行交易信号分析
- 集成布林带指标用于日线大趋势判断和超买超卖分析

技术指标体系：
1. 分钟线级别：EMA8/21/55/125, KDJ(14), MACD(12,26,9), 威廉指标变种, 成交量分析
2. 日线级别：EMA8/21/55, MACD(12,26,9), KDJ(14), 布林带(20日,2倍标准差)
3. 信号确认：双重确认升级版 + 布林带位置判断 + 成交量确认
"""
import akshare as ak
import pandas as pd
from datetime import datetime
import os
import sys
import json
import time
import requests
from typing import Optional
import schedule
import logging
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import numpy as np
from dotenv import load_dotenv
import smtplib

# --- AI导师模块 ---
AGENT_PROMPT_JSON_PATH = "options_trading_prompt.json"
MASTER_AGENT_PROMPT = None

def load_master_agent_prompt():
    """
    /**
     * @description 在脚本启动时加载AI导师的配置文件
     */
    """
    global MASTER_AGENT_PROMPT
    try:
        with open(AGENT_PROMPT_JSON_PATH, 'r', encoding='utf-8') as f:
            MASTER_AGENT_PROMPT = json.load(f)
        logger.info(f"成功加载AI导师配置文件: {AGENT_PROMPT_JSON_PATH}")
    except Exception as e:
        logger.error(f"加载AI导师配置文件失败: {e}")
        MASTER_AGENT_PROMPT = None

def convert_numpy_types(obj):
    """
    /**
     * @description 递归转换numpy类型为Python原生类型，以便JSON序列化
     * @param {any} obj - 待转换的对象
     * @returns {any} 转换后的对象
     */
    """
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    else:
        return obj

def call_llm_api(system_prompt: str, user_prompt: str) -> str:
    """
    /**
     * @description 调用DeepSeek大语言模型API的函数。
     * @param {string} system_prompt - 系统提示词，定义了AI的角色和规则。
     * @param {string} user_prompt - 用户提示词，包含了实时市场数据和请求。
     * @returns {string} 从LLM返回的分析文本。
     */
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
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "stream": False
    }

    try:
        logger.info("正在调用DeepSeek Chat API...")
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        content = data['choices'][0]['message']['content']
        logger.info("成功从DeepSeek Chat API获取分析。")
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

def get_master_analysis(market_data: dict) -> str:
    """
    /**
     * @description 获取AI导师的综合分析。
     * @param {dict} market_data - 包含市场数据的结构化字典。
     * @returns {string} AI导师的详细分析。
     */
    """
    if not MASTER_AGENT_PROMPT:
        return "错误: AI导师的配置文件未加载。"

    try:
        # 转换numpy类型为Python原生类型
        clean_market_data = convert_numpy_types(market_data)
        
        system_prompt = json.dumps(MASTER_AGENT_PROMPT, ensure_ascii=False)
        # 过滤敏感数据，隐藏核心策略指标
        filtered_data = {
            'symbol': clean_market_data.get('symbol'),
            'timestamp': clean_market_data.get('timestamp'),
            'price': clean_market_data.get('price'),
            'signal_type': clean_market_data.get('signal_type'),
            'signal_strength': clean_market_data.get('signal_strength'),
            # 使用通用技术指标名称，隐藏具体实现
            'short_ma': clean_market_data.get('EMA8'),  # 短期均线
            'medium_ma': clean_market_data.get('EMA21'),  # 中期均线
            'long_ma': clean_market_data.get('EMA55'),   # 长期均线
            'momentum_fast': clean_market_data.get('K_value'),  # 快速动量
            'momentum_slow': clean_market_data.get('D_value'),  # 慢速动量
            'momentum_signal': clean_market_data.get('J_value'), # 动量信号
            'trend_indicator': clean_market_data.get('MACD'),    # 趋势指标
            'volume': clean_market_data.get('volume'),
            'volume_ratio': clean_market_data.get('vol_ratio'),
            'volatility_index': clean_market_data.get('futures_volatility'),
            'volatility_percentile': clean_market_data.get('vol_percentile'),
            'trend_short': clean_market_data.get('trend_short'),
            'trend_medium': clean_market_data.get('trend_medium'),
            'trend_long': clean_market_data.get('trend_long'),
            'daily_trend_short': clean_market_data.get('daily_trend_short'),
            'daily_trend_medium': clean_market_data.get('daily_trend_medium'),
            # 布林带分析数据
            'bb_position': clean_market_data.get('bb_position'),
            'bb_overbought': clean_market_data.get('bb_overbought'),
            'bb_oversold': clean_market_data.get('bb_oversold'),
            'bb_trend_strength': clean_market_data.get('bb_trend_strength'),
            # 隐藏威廉指标，用通用名称
            'proprietary_signal_confirmed': clean_market_data.get('williams_c_signal') or clean_market_data.get('williams_p_signal'),
            'signal_confirmation_type': 'bullish_confirmation' if clean_market_data.get('williams_c_signal') else ('bearish_confirmation' if clean_market_data.get('williams_p_signal') else 'none'),
            'volume_confirmation': clean_market_data.get('volume_confirmation'),
            # 期货特有数据
            'futures_type': clean_market_data.get('futures_type'),
            'contract_month': clean_market_data.get('contract_month'),
            'open_interest': clean_market_data.get('open_interest'),
            'price_change_pct': clean_market_data.get('price_change_pct')
        }
        
        user_prompt_text = f"""你好，Alata。我的期货期权量化策略系统检测到一个潜在的交易信号，请按照结论优先的格式进行分析。

请严格按照以下格式回复，并注意以下要求：
1. 不要在分析中提及具体的技术指标名称（如EMA、MACD、KDJ、威廉指标等）
2. 使用通用的技术分析术语（如均线、动量、趋势、成交量、布林带等）
3. 重点关注价格行为、成交量变化、市场结构和价格在布林带中的位置
4. 考虑期货市场的特殊性（杠杆、保证金、交割等）
5. 结合布林带位置判断超买超卖状态和趋势强度

## 期权策略建议
**方向**: [买入看涨期权/买入看跌期权/观察等待]
**行权价**: [具体价格]（[价格相对性描述]）
**到期日**: [建议天数范围]
**仓位**: [百分比]（[基于信号强度的说明]）

## 风险管理
**止损**: [具体条件或百分比]
**止盈**: [分层策略描述]
**Roll Up**: [滚动策略说明]

## 分析依据
[使用通用技术分析术语的详细分析，避免暴露具体指标名称]

以下是相关市场数据：
{json.dumps(filtered_data, indent=2, ensure_ascii=False, default=str)}"""
        
        analysis = call_llm_api(system_prompt, user_prompt_text)
        return analysis
        
    except Exception as e:
        logger.error(f"获取AI导师分析时出错: {e}")
        return f"获取AI导师分析时出错: {e}"

# --- 邮件发送模块 ---
# 全局邮件参数
SMTP_SERVER = None
FROM_ADDR = None
PASSWORD = None
TO_ADDR = None

def setup_email(smtp_server, from_addr, password, to_addr):
    """
    /**
     * @description 设置邮件参数
     * @param {string} smtp_server - SMTP服务器地址
     * @param {string} from_addr - 发送邮箱
     * @param {string} password - 邮箱授权码
     * @param {list} to_addr - 接收邮箱列表
     */
    """
    global SMTP_SERVER, FROM_ADDR, PASSWORD, TO_ADDR
    SMTP_SERVER = smtp_server
    FROM_ADDR = from_addr
    PASSWORD = password
    TO_ADDR = to_addr
    logger.info("邮件参数设置完成")

def send_email(subject, content):
    """
    /**
     * @description 使用配置的邮件参数发送邮件通知
     * @param {string} subject - 邮件主题
     * @param {string} content - 邮件内容
     * @returns {boolean} 是否发送成功
     */
    """
    if not all([SMTP_SERVER, FROM_ADDR, PASSWORD, TO_ADDR]):
        logger.error("邮件参数未设置")
        return False
        
    try:
        # 创建邮件对象
        msg = MIMEMultipart()
        msg['From'] = FROM_ADDR
        msg['To'] = ';'.join(TO_ADDR)  # 多个收件人用分号连接
        msg['Subject'] = Header(subject, 'utf-8')
        
        # 添加邮件内容
        msg.attach(MIMEText(content, 'plain', 'utf-8'))
        
        # 连接到SMTP服务器
        server = smtplib.SMTP_SSL(SMTP_SERVER, 465)
        server.login(FROM_ADDR, PASSWORD)
        
        # 发送邮件
        server.sendmail(FROM_ADDR, TO_ADDR, msg.as_string())
        server.quit()
        
        logger.info(f"邮件发送成功: {subject}")
        return True
    except Exception as e:
        logger.error(f"邮件发送失败: {str(e)}")
        return False

def send_notification(message: str, symbol: Optional[str] = None, signal_type: Optional[str] = None):
    """
    /**
     * @description 发送通知（集成邮箱发送功能）
     * @param {string} message - 通知消息
     * @param {string} symbol - 期货代码（可选）
     * @param {string} signal_type - 信号类型（可选）
     */
    """
    try:
        # 记录到日志
        logger.info(f"通知消息: {message}")
        print(f"\n=== 交易信号通知 ===\n{message}\n===================")
        
        # 使用内置邮件发送功能
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 根据信号类型确定交易方向
            direction = ""
            if signal_type and symbol:
                if "多头" in signal_type or "超卖反弹" in signal_type:
                    direction = "买入看涨期权"
                elif "空头" in signal_type or "超买回调" in signal_type:
                    direction = "买入看跌期权"
                elif "预警" in signal_type:
                    if "多头" in signal_type:
                        direction = "多头预警"
                    elif "空头" in signal_type:
                        direction = "空头预警"
                elif "减仓" in signal_type:
                    if "多头" in signal_type:
                        direction = "多头减仓"
                    elif "空头" in signal_type:
                        direction = "空头减仓"
                elif "平仓" in signal_type:
                    if "多头" in signal_type:
                        direction = "多头平仓"
                    elif "空头" in signal_type:
                        direction = "空头平仓"
                elif "变盘" in signal_type:
                    if "多头" in signal_type:
                        direction = "多头变盘"
                    elif "空头" in signal_type:
                        direction = "空头变盘"
                elif "持仓" in signal_type:
                    if "多头" in signal_type:
                        direction = "多头持仓"
                    elif "空头" in signal_type:
                        direction = "空头持仓"
                elif "开仓" in signal_type:
                    if "多头" in signal_type:
                        direction = "买入看涨期权"
                    elif "空头" in signal_type:
                        direction = "买入看跌期权"
                else:
                    direction = "观察等待"
                
                # 构建包含期货代码和方向的邮件标题
                subject = f"{symbol}-{direction} 期货期权策略信号[{current_time}]"
            else:
                # 默认标题（向后兼容）
                subject = f"期货期权策略信号[{current_time}]"
            
            success = send_email(subject, message)
            if success:
                logger.info("邮箱通知发送成功")
            else:
                logger.warning("邮箱通知发送失败")
        except Exception as email_err:
            logger.warning(f"邮箱通知发送失败: {email_err}")
            
    except Exception as e:
        logger.error(f"发送通知失败: {e}")

# --- 配置 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), "gamma_shock_futures.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

CONFIG = {
    'data_dir': os.path.join(os.path.dirname(__file__), "data", "futures_data"),
    'symbols': {
        'NI': {'code': 'NI0', 'name': '沪镍主连', 'exchange': 'SHFE'},
        'LC': {'code': 'LC0', 'name': '碳酸锂主连', 'exchange': 'DCE'}
    },
    'period': "5"  # 单位：分钟
}

data_dir = str(CONFIG['data_dir'])
cache_dir = os.path.join(data_dir, "cache")

# 创建数据目录
if not os.path.exists(data_dir):
    os.makedirs(data_dir)
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)

# --- 数据获取模块 ---

def get_futures_minute_data(symbol: str, period: str = "5"):
    """
    /**
     * @description 获取期货分钟线数据，并进行缓存和处理。
     * @param {string} symbol - 期货代码 (e.g., "SA0", "AO0", "AG0", "PS0")。
     * @param {string} period - K线周期（分钟）。
     * @returns {pd.DataFrame | None} 处理后的分钟线数据。
     */
    """
    cache_file = os.path.join(cache_dir, f"futures_{symbol}_{period}min.csv")
    
    # 尝试从缓存加载
    if os.path.exists(cache_file):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
        # 对于分钟线数据，设置一个较短的缓存有效期
        if (datetime.now() - file_mod_time).seconds < int(period) * 60:
            try:
                logger.info(f"使用缓存的 {symbol} 数据。")
                df = pd.read_csv(cache_file)
                df['datetime'] = pd.to_datetime(df['datetime'])
                return df.set_index('datetime')
            except Exception as e:
                logger.warning(f"读取 {symbol} 缓存失败: {e}, 将重新获取。")

    logger.info(f"从API获取 {symbol} 的分钟线数据...")
    try:
        # 获取期货分钟线数据
        futures_min_df = ak.futures_zh_minute_sina(symbol=symbol, period=period)
        
        if futures_min_df is None or futures_min_df.empty:
            logger.warning(f"未能获取到 {symbol} 的分钟线数据。")
            return None

        # 数据预处理
        futures_min_df.rename(columns={
            'datetime': 'datetime',
            'open': 'open', 
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        }, inplace=True)
        
        futures_min_df['datetime'] = pd.to_datetime(futures_min_df['datetime'])
        futures_min_df.set_index('datetime', inplace=True)
        
        # 将数据类型转换为数值型
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in futures_min_df.columns:
                futures_min_df[col] = pd.to_numeric(futures_min_df[col], errors='coerce')

        # 数据清洗：移除异常值
        for col in ['open', 'high', 'low', 'close']:
            if col in futures_min_df.columns:
                # 移除价格为0或负数的异常数据
                futures_min_df = futures_min_df[futures_min_df[col] > 0]
        
        if futures_min_df.empty:
            logger.warning(f"{symbol} 数据清洗后为空。")
            return None

        # 保存缓存
        futures_min_df.to_csv(cache_file)
        logger.info(f"已更新 {symbol} 的数据缓存。")
        return futures_min_df

    except Exception as e:
        logger.error(f"获取 {symbol} 数据时出错: {e}")
        # 如果API失败，尝试返回旧缓存
        if os.path.exists(cache_file):
            try:
                logger.warning(f"API请求失败，使用 {symbol} 的旧缓存数据。")
                df = pd.read_csv(cache_file)
                df['datetime'] = pd.to_datetime(df['datetime'])
                return df.set_index('datetime')
            except Exception as cache_err:
                logger.error(f"读取 {symbol} 的旧缓存也失败了: {cache_err}")
        return None

def get_futures_daily_data(symbol: str):
    """
    /**
     * @description 获取期货日线数据，并进行缓存和处理。
     * @param {string} symbol - 期货代码 (e.g., "SA0", "AO0", "AG0", "PS0")。
     * @returns {pd.DataFrame | None} 处理后的日线数据。
     */
    """
    cache_file = os.path.join(cache_dir, f"futures_{symbol}_daily.csv")
    
    # 检查缓存是否存在且有效（当日有效）
    use_cache = False
    if os.path.exists(cache_file):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
        if file_mod_time.date() == datetime.now().date():
            use_cache = True
    
    if use_cache:
        try:
            logger.info(f"使用缓存的{symbol}日线数据。")
            df = pd.read_csv(cache_file)
            df['date'] = pd.to_datetime(df['date'])
            return df.set_index('date')
        except Exception as e:
            logger.warning(f"读取{symbol}日线缓存失败: {e}, 将重新获取。")
    
    logger.info(f"从API获取{symbol}日线数据...")
    try:
        # 获取期货日线数据
        daily_data = ak.futures_zh_daily_sina(symbol=symbol)
        
        if daily_data is None or daily_data.empty:
            logger.warning(f"未能获取到{symbol}的日线数据。")
            return None
        
        # 数据预处理
        daily_data.rename(columns={
            'date': 'date',
            'open': 'open',
            'high': 'high', 
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        }, inplace=True)
        
        daily_data['date'] = pd.to_datetime(daily_data['date'])
        daily_data.set_index('date', inplace=True)
        
        # 将数据类型转换为数值型
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in daily_data.columns:
                daily_data[col] = pd.to_numeric(daily_data[col], errors='coerce')
        
        # 保存缓存
        daily_data.to_csv(cache_file)
        logger.info(f"已缓存{symbol}日线数据。")
        return daily_data
        
    except Exception as e:
        logger.error(f"获取{symbol}日线数据时出错: {e}")
        # 如果API失败，尝试返回旧缓存
        if os.path.exists(cache_file):
            try:
                logger.warning(f"API请求失败，使用{symbol}的旧日线缓存数据。")
                df = pd.read_csv(cache_file)
                df['date'] = pd.to_datetime(df['date'])
                return df.set_index('date')
            except Exception as cache_err:
                logger.error(f"读取{symbol}的旧日线缓存也失败了: {cache_err}")
        return None

def calculate_futures_volatility(futures_data: pd.DataFrame, period: int = 20) -> float:
    """
    /**
     * @description 计算期货的历史波动率（年化）
     * @param {pd.DataFrame} futures_data - 期货数据
     * @param {int} period - 计算周期（默认20日）
     * @returns {float} 年化波动率
     */
    """
    if len(futures_data) < period:
        return 0.0
    
    # 计算收益率
    returns = futures_data['close'].pct_change().dropna()
    
    if len(returns) < period:
        return 0.0
    
    # 计算最近period天的波动率并年化
    recent_returns = returns.tail(period)
    volatility = recent_returns.std() * (252 ** 0.5)  # 年化（假设252个交易日）
    
    return volatility

# --- 技术指标计算模块 ---

def calculate_technical_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """
    /**
     * @description 计算期货技术指标
     * @param {pd.DataFrame} data - 原始价格数据
     * @returns {pd.DataFrame} 包含技术指标的数据
     */
    """
    df = data.copy()
    
    # 1. 多均线系统
    df['EMA8'] = df['close'].ewm(span=8, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA55'] = df['close'].ewm(span=55, adjust=False).mean()
    df['EMA125'] = df['close'].ewm(span=125, adjust=False).mean()
    
    # 2. KDJ随机指标（14周期）
    low_list = df['low'].rolling(window=14, min_periods=1).min()
    high_list = df['high'].rolling(window=14, min_periods=1).max()
    rsv = (df['close'] - low_list) / (high_list - low_list) * 100
    df['K'] = rsv.ewm(com=2, adjust=False).mean()  # SMA(RSV,3,1) 近似
    df['D'] = df['K'].ewm(com=2, adjust=False).mean()  # SMA(K,3,1) 近似
    df['J'] = 3 * df['K'] - 2 * df['D']
    
    # 3. MACD指标
    df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['DIF'] = df['EMA12'] - df['EMA26']
    df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
    df['MACD'] = (df['DIF'] - df['DEA']) * 2
    
    # 4. 威廉指标变种
    N = 19
    df['VAR1'] = df['high'].rolling(window=N, min_periods=1).max()  # HHV(HIGH,19)
    df['VAR2'] = df['low'].rolling(window=N, min_periods=1).min()   # LLV(LOW,19)
    
    # 计算威廉指标基础值
    williams_base = (df['close'] - df['VAR2']) / (df['VAR1'] - df['VAR2'])
    williams_base = williams_base.fillna(0.5)  # 处理除零情况
    
    # ZLS: 21日EMA平滑后减0.5 (长期线)
    df['ZLS'] = williams_base.ewm(span=21, adjust=False).mean() - 0.5
    
    # CZX: 5日EMA平滑后减0.5 (短期线)  
    df['CZX'] = williams_base.ewm(span=5, adjust=False).mean() - 0.5
    
    # HLB: 两线差值
    df['HLB'] = df['CZX'] - df['ZLS']

    # 5. 成交量分析
    df['VOL_MA5'] = df['volume'].rolling(window=5, min_periods=1).mean()
    df['VOL_MA10'] = df['volume'].rolling(window=10, min_periods=1).mean()
    
    return df

def calculate_daily_technical_indicators(daily_data: pd.DataFrame) -> pd.DataFrame:
    """
    /**
     * @description 计算日线技术指标
     * @param {pd.DataFrame} daily_data - 日线数据
     * @returns {pd.DataFrame} 包含日线技术指标的数据
     */
    """
    if daily_data is None or daily_data.empty:
        return None
        
    df = daily_data.copy()
    
    # 日线EMA系统
    df['daily_EMA8'] = df['close'].ewm(span=8, adjust=False).mean()
    df['daily_EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['daily_EMA55'] = df['close'].ewm(span=55, adjust=False).mean()
    
    # 日线MACD
    df['daily_EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['daily_EMA26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['daily_DIF'] = df['daily_EMA12'] - df['daily_EMA26']
    df['daily_DEA'] = df['daily_DIF'].ewm(span=9, adjust=False).mean()
    df['daily_MACD'] = (df['daily_DIF'] - df['daily_DEA']) * 2
    
    # 日线KDJ
    low_list = df['low'].rolling(window=14, min_periods=1).min()
    high_list = df['high'].rolling(window=14, min_periods=1).max()
    rsv = (df['close'] - low_list) / (high_list - low_list) * 100
    df['daily_K'] = rsv.ewm(com=2, adjust=False).mean()
    df['daily_D'] = df['daily_K'].ewm(com=2, adjust=False).mean()
    df['daily_J'] = 3 * df['daily_K'] - 2 * df['daily_D']
    
    # 日线布林带指标 (20日，2倍标准差)
    df['daily_BB_middle'] = df['close'].rolling(window=20, min_periods=1).mean()  # 中轨(20日SMA)
    bb_std = df['close'].rolling(window=20, min_periods=1).std()  # 20日标准差
    df['daily_BB_upper'] = df['daily_BB_middle'] + (bb_std * 2)  # 上轨
    df['daily_BB_lower'] = df['daily_BB_middle'] - (bb_std * 2)  # 下轨
    
    # 布林带宽度和百分比B
    df['daily_BB_width'] = df['daily_BB_upper'] - df['daily_BB_lower']  # 带宽
    df['daily_BB_percent'] = (df['close'] - df['daily_BB_lower']) / (df['daily_BB_upper'] - df['daily_BB_lower'])  # %B值
    
    return df

# --- 信号检测模块 ---

def detect_futures_signals(data: pd.DataFrame, symbol: str, daily_data: pd.DataFrame = None) -> tuple:
    """
    /**
     * @description 检测期货交易信号（基于双重确认升级版策略）
     * @param {pd.DataFrame} data - 包含技术指标的数据
     * @param {string} symbol - 期货代码
     * @param {pd.DataFrame} daily_data - 日线数据
     * @returns {tuple} 包含市场数据字典和信号检测标志的元组
     */
    """
    if len(data) < 3:
        logger.warning(f"{symbol} 数据点不足，无法生成信号。")
        return None, False
        
    # 获取当前和历史数据点
    current_row = data.iloc[-1]
    prev_row = data.iloc[-2] if len(data) >= 2 else current_row
    prev2_row = data.iloc[-3] if len(data) >= 3 else prev_row

    # 计算日线技术指标
    daily_indicators = None
    daily_trend = {"short": "中性", "medium": "中性"}
    
    if daily_data is not None and not daily_data.empty:
        daily_indicators = calculate_daily_technical_indicators(daily_data)
        if daily_indicators is not None and len(daily_indicators) > 0:
            daily_current = daily_indicators.iloc[-1]
            
            # 布林带分析
            bb_analysis = {
                "position": "中线",  # 价格在布林带中的位置
                "overbought": False,  # 是否超买
                "oversold": False,    # 是否超卖
                "trend_strength": "中性"  # 趋势强度
            }
            
            # 判断价格在布林带中的位置
            if daily_current['close'] > daily_current['daily_BB_upper']:
                bb_analysis["position"] = "上轨之上"
                bb_analysis["overbought"] = True
                bb_analysis["trend_strength"] = "强势上涨"
            elif daily_current['close'] < daily_current['daily_BB_lower']:
                bb_analysis["position"] = "下轨之下"
                bb_analysis["oversold"] = True
                bb_analysis["trend_strength"] = "强势下跌"
            elif daily_current['close'] > daily_current['daily_BB_middle']:
                bb_analysis["position"] = "中轨之上"
                bb_analysis["trend_strength"] = "偏多"
            else:
                bb_analysis["position"] = "中轨之下"
                bb_analysis["trend_strength"] = "偏空"
            
            # 日线趋势判断（结合布林带）
            daily_trend = {
                "short": "多头" if daily_current['daily_EMA8'] > daily_current['daily_EMA21'] else "空头",
                "medium": "多头" if daily_current['daily_EMA21'] > daily_current['daily_EMA55'] else "空头",
                "bb_position": str(bb_analysis["position"]),
                "bb_overbought": str(bb_analysis["overbought"]),
                "bb_oversold": str(bb_analysis["oversold"]),
                "bb_trend_strength": str(bb_analysis["trend_strength"])
            }

    # --- 威廉指标信号检测 ---
    williams_c_signal = False  # 超卖反弹信号
    williams_p_signal = False  # 超买回调信号
    
    # C信号: CZX上穿ZLS且ZLS<0.1（超卖反弹）
    if (current_row['CZX'] > current_row['ZLS'] and 
        prev_row['CZX'] <= prev_row['ZLS'] and 
        current_row['ZLS'] < 0.1):
        williams_c_signal = True
        logger.info(f"{symbol}: 威廉指标C信号 - 超卖反弹 (ZLS={current_row['ZLS']:.3f})")
    
    # P信号: ZLS上穿CZX且ZLS>0.25（超买回调）
    if (current_row['ZLS'] > current_row['CZX'] and 
        prev_row['ZLS'] <= prev_row['CZX'] and 
        current_row['ZLS'] > 0.25):
        williams_p_signal = True
        logger.info(f"{symbol}: 威廉指标P信号 - 超买回调 (ZLS={current_row['ZLS']:.3f})")

    # --- 双重确认升级版信号逻辑 ---
    signal_type = "无信号"
    signal_strength = 0
    volume_confirmation = False
    williams_confirmation = ""
    
    # 成交量确认条件（降低期货市场成交量放大标准）
    if current_row['volume'] > current_row['VOL_MA10'] * 1.5:  # 降低到1.5倍标准
        volume_confirmation = True
        logger.info(f"{symbol}: 检测到成交量放大 (当前: {current_row['volume']:.0f}, 10日均量: {current_row['VOL_MA10']:.0f})")

    # 1. 多头进场信号（放宽条件）
    # 条件1: EMA8上穿EMA21（经典金叉）
    # 条件2: EMA8持续上涨趋势（当前EMA8 > 前一根EMA8）
    # 条件3: 价格在EMA8之上或接近EMA8
    if (current_row['EMA8'] > current_row['EMA21'] and 
        prev_row['EMA8'] <= prev_row['EMA21'] and 
        current_row['EMA8'] > prev_row['EMA8']):  # 简化条件，只要EMA8上涨
        signal_type = "多头进场信号"
        signal_strength = 2  # 降低基础强度
        if volume_confirmation:
            signal_strength += 1
        if williams_c_signal:  # 威廉指标确认
            signal_strength += 1
            williams_confirmation = "威廉C信号确认"

    # 2. 空头进场信号（放宽条件）
    # 条件1: EMA21上穿EMA8（经典死叉）
    # 条件2: EMA8持续下跌趋势（当前EMA8 < 前一根EMA8）
    # 条件3: 价格在EMA8之下或接近EMA8
    elif (current_row['EMA21'] > current_row['EMA8'] and 
          prev_row['EMA8'] >= prev_row['EMA21'] and 
          current_row['EMA8'] < prev_row['EMA8']):  # 简化条件，只要EMA8下跌
        signal_type = "空头进场信号"
        signal_strength = 2  # 降低基础强度
        if volume_confirmation:
            signal_strength += 1
        if williams_p_signal:  # 威廉指标确认
            signal_strength += 1
            williams_confirmation = "威廉P信号确认"

    # 3. 多头趋势确认信号（新增）
    # EMA8 > EMA21 且价格突破前高
    elif (current_row['EMA8'] > current_row['EMA21'] and 
          current_row['close'] > prev_row['high'] and
          current_row['close'] > current_row['EMA8']):
        signal_type = "多头趋势确认信号"
        signal_strength = 2
        if volume_confirmation:
            signal_strength += 1
        if williams_c_signal:
            signal_strength += 1
            williams_confirmation = "威廉C信号确认"

    # 4. 空头趋势确认信号（新增）
    # EMA21 > EMA8 且价格跌破前低
    elif (current_row['EMA21'] > current_row['EMA8'] and 
          current_row['close'] < prev_row['low'] and
          current_row['close'] < current_row['EMA8']):
        signal_type = "空头趋势确认信号"
        signal_strength = 2
        if volume_confirmation:
            signal_strength += 1
        if williams_p_signal:
            signal_strength += 1
            williams_confirmation = "威廉P信号确认"

    # 5. 多头预警
    # 前一根K线收盘价>EMA8 AND 收盘价<EMA21 AND J线上穿K线
    elif (prev_row['close'] > prev_row['EMA8'] and 
          prev_row['close'] < prev_row['EMA21'] and 
          current_row['J'] > current_row['K'] and 
          prev_row['J'] < prev_row['K']):
        signal_type = "多头预警信号"
        signal_strength = 1  # 降低预警信号强度
        if volume_confirmation:
            signal_strength += 1
        if williams_c_signal:  # 威廉指标确认可升级为进场信号
            signal_type = "多头进场信号(威廉确认)"
            signal_strength += 1
            williams_confirmation = "威廉C信号升级"

    # 6. 空头预警
    # 前一根K线收盘价<EMA8 AND 收盘价>EMA21 AND K线下穿J线
    elif (prev_row['close'] < prev_row['EMA8'] and 
          prev_row['close'] > prev_row['EMA21'] and 
          current_row['K'] > current_row['J'] and 
          prev_row['K'] < prev_row['J']):
        signal_type = "空头预警信号"
        signal_strength = 1  # 降低预警信号强度
        if volume_confirmation:
            signal_strength += 1
        if williams_p_signal:  # 威廉指标确认可升级为进场信号
            signal_type = "空头进场信号(威廉确认)"
            signal_strength += 1
            williams_confirmation = "威廉P信号升级"

    # 7. 纯威廉指标信号（当主策略无明确信号时）
    elif williams_c_signal:
        signal_type = "威廉超卖反弹信号"
        signal_strength = 1  # 降低威廉信号强度
        if volume_confirmation:
            signal_strength += 1
        williams_confirmation = "纯威廉C信号"
    elif williams_p_signal:
        signal_type = "威廉超买回调信号"
        signal_strength = 1  # 降低威廉信号强度
        if volume_confirmation:
            signal_strength += 1
        williams_confirmation = "纯威廉P信号"

    # 8. 强势突破信号（新增）
    # 价格创新高且成交量放大
    elif (current_row['close'] > data['close'].rolling(window=20).max().iloc[-2] and  # 创20日新高
          volume_confirmation):
        signal_type = "多头强势突破信号"
        signal_strength = 2
        williams_confirmation = "价格创新高"

    # 9. 弱势跌破信号（新增）
    # 价格创新低且成交量放大
    elif (current_row['close'] < data['close'].rolling(window=20).min().iloc[-2] and  # 创20日新低
          volume_confirmation):
        signal_type = "空头弱势跌破信号"
        signal_strength = 2
        williams_confirmation = "价格创新低"

    # 10. 成交量异常但无明确技术信号
    elif volume_confirmation:
        signal_type = "成交量异常信号"
        signal_strength = 1

    # 判断是否有信号（降低阈值）
    signal_detected = signal_strength >= 1  # 从2降低到1

    # 计算期货波动率
    futures_volatility = calculate_futures_volatility(data, period=20)
    vol_percentile = 0.5  # 默认值，期货市场可以根据历史数据计算

    market_data = {
        'symbol': symbol,
        'timestamp': current_row.name.strftime('%Y-%m-%d %H:%M:%S'),
        'price': current_row['close'],
        'signal_type': signal_type,
        'signal_strength': signal_strength,
        'volume_confirmation': volume_confirmation,
        'williams_confirmation': williams_confirmation,
        # 技术指标数据
        'EMA8': current_row['EMA8'],
        'EMA21': current_row['EMA21'],
        'EMA55': current_row['EMA55'],
        'EMA125': current_row['EMA125'],
        'K_value': current_row['K'],
        'D_value': current_row['D'],
        'J_value': current_row['J'],
        'DIF': current_row['DIF'],
        'DEA': current_row['DEA'],
        'MACD': current_row['MACD'],
        'volume': current_row['volume'],
        'vol_ma5': current_row['VOL_MA5'],
        'vol_ma10': current_row['VOL_MA10'],
        'vol_ratio': current_row['volume'] / current_row['VOL_MA10'] if current_row['VOL_MA10'] > 0 else 0,
        # 威廉指标数据
        'ZLS': current_row['ZLS'],
        'CZX': current_row['CZX'],
        'HLB': current_row['HLB'],
        'williams_c_signal': williams_c_signal,
        'williams_p_signal': williams_p_signal,
        # 期货特有数据
        'futures_volatility': futures_volatility,
        'vol_percentile': vol_percentile,
        'futures_type': symbol,
        'contract_month': 'main',  # 主连合约
        'price_change_pct': (current_row['close'] - prev_row['close']) / prev_row['close'] * 100 if prev_row['close'] > 0 else 0,
        # 日线趋势数据
        'daily_trend_short': daily_trend["short"],
        'daily_trend_medium': daily_trend["medium"],
        # 布林带分析数据
        'bb_position': daily_trend.get("bb_position", "未知"),
        'bb_overbought': daily_trend.get("bb_overbought", False),
        'bb_oversold': daily_trend.get("bb_oversold", False),
        'bb_trend_strength': daily_trend.get("bb_trend_strength", "中性"),
        # 趋势分析
        'trend_short': "上涨" if current_row['EMA8'] > current_row['EMA21'] else "下跌",
        'trend_medium': "上涨" if current_row['EMA21'] > current_row['EMA55'] else "下跌",
        'trend_long': "上涨" if current_row['EMA55'] > current_row['EMA125'] else "下跌",
        'signal': signal_type
    }

    if signal_detected:
        confirmation_info = f" ({williams_confirmation})" if williams_confirmation else ""
        logger.info(f"{symbol} 检测到信号: {signal_type} (强度: {signal_strength}){confirmation_info}")
    
    return market_data, signal_detected

# --- 策略分析模块 ---

def analyze_futures_data(symbol: str, symbol_info: dict):
    """
    /**
     * @description 分析单个期货标的数据并生成交易信号
     * @param {string} symbol - 期货代码
     * @param {dict} symbol_info - 期货信息字典
     * @returns {tuple} 包含市场数据的字典和信号检测标志的元组
     */
     """
    logger.info(f"开始分析 {symbol_info['name']} 数据...")
    
    # 获取分钟线数据
    futures_data = get_futures_minute_data(symbol_info['code'], period=str(CONFIG['period']))
    
    if futures_data is None or futures_data.empty:
        logger.error(f"无法获取 {symbol_info['name']} 数据，跳过分析。")
        return None, False

    # 获取日线数据
    daily_data = get_futures_daily_data(symbol_info['code'])
    
    # 计算技术指标
    futures_data = calculate_technical_indicators(futures_data)
    
    # 检测信号
    market_data, signal_detected = detect_futures_signals(futures_data, symbol_info['name'], daily_data)
    
    return market_data, signal_detected

# --- 任务调度模块 ---

def is_futures_trading_hours(test_mode=False):
    """
    /**
     * @description 判断当前是否在期货交易时段
     * @param {boolean} test_mode - 测试模式，如果为True则忽略交易时间限制
     * @returns {boolean} 如果是交易时间则返回True
     */
    """
    if test_mode:
        logger.info("测试模式：忽略交易时间限制")
        return True
        
    now = datetime.now()
    
    # 只在工作日运行
    if now.weekday() >= 5:
        logger.info("当前为周末，非交易日")
        return False
    
    # 期货交易时段: 
    # 日盘: 9:00-11:30 & 13:30-15:00
    # 夜盘: 21:00-02:30 (次日)
    day_morning_start = now.replace(hour=9, minute=0, second=0, microsecond=0).time()
    day_morning_end = now.replace(hour=11, minute=30, second=0, microsecond=0).time()
    day_afternoon_start = now.replace(hour=13, minute=30, second=0, microsecond=0).time()
    day_afternoon_end = now.replace(hour=15, minute=0, second=0, microsecond=0).time()
    night_start = now.replace(hour=21, minute=0, second=0, microsecond=0).time()
    night_end = now.replace(hour=2, minute=30, second=0, microsecond=0).time()
    
    current_time = now.time()
    
    # 日盘时段
    is_day_trading = ((day_morning_start <= current_time <= day_morning_end) or 
                      (day_afternoon_start <= current_time <= day_afternoon_end))
    
    # 夜盘时段（跨日处理）
    is_night_trading = (current_time >= night_start) or (current_time <= night_end)
    
    is_trading = is_day_trading or is_night_trading
    
    if not is_trading:
        logger.info(f"当前时间 {current_time} 不在期货交易时段")
    
    return is_trading

def job(test_mode=False, force_run=False):
    """
    /**
     * @description 定时执行的任务，分析所有配置的期货品种
     * @param {boolean} test_mode - 测试模式，忽略交易时间限制
     * @param {boolean} force_run - 强制运行一次
     */
    """
    if not test_mode and not force_run and not is_futures_trading_hours():
        logger.info("当前非期货交易时段，跳过运行。")
        return
        
    start_time = time.time()
    logger.info("开始期货期权策略定时任务...")
    
    for symbol, symbol_info in CONFIG['symbols'].items():
        try:
            market_data, signal_detected = analyze_futures_data(symbol, symbol_info)
            if signal_detected and market_data:
                logger.info(f"为 {symbol_info['name']} 检测到信号，正在获取AI导师分析...")
                master_analysis = get_master_analysis(market_data)
                logger.info(f"AI导师分析结果 for {symbol_info['name']}:\n{master_analysis}")
                # 发送邮件通知
                send_notification(f"--- AI导师期货期权分析: {symbol_info['name']} ---\n{master_analysis}", symbol_info['name'], market_data['signal_type'])
            elif market_data:
                logger.info(f"{symbol_info['name']} 未检测到明确交易信号。")
        except Exception as e:
            logger.error(f"分析 {symbol_info['name']} 数据时出错: {e}", exc_info=True)
            
    elapsed_time = time.time() - start_time
    logger.info(f"任务完成，耗时: {elapsed_time:.2f}秒")

def run_scheduler(test_mode=False):
    """
    /**
     * @description 启动定时任务调度器
     * @param {boolean} test_mode - 测试模式
     */
    """
    logger.info("启动期货期权策略定时任务调度器...")
    
    schedule.every(int(CONFIG['period'])).minutes.do(job, test_mode=test_mode)
    
    logger.info("立即执行一次任务...")
    job(test_mode=test_mode, force_run=True)
    
    logger.info(f"定时任务已设置，每{CONFIG['period']}分钟运行一次。")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到中断信号，退出程序。")
            break
        except Exception as e:
            logger.error(f"调度器出错: {str(e)}")
            send_notification(f"期货策略调度器出错: {str(e)}")
            time.sleep(60)

def init():
    """
    /**
     * @description 初始化程序，加载配置和检查API密钥
     */
    """
    logger.info("开始初始化期货期权策略跟踪系统...")
    
    # 1. 加载 .env 文件中的环境变量
    if not load_dotenv():
        logger.warning(".env 文件未找到。请确保在项目根目录下创建了 .env 文件，并已设置 DEEPSEEK_API_KEY。")
        logger.warning("例如: DEEPSEEK_API_KEY=\"your_key_here\"")

    # 2. 验证API密钥
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        logger.error("关键错误: DEEPSEEK_API_KEY 环境变量未设置。程序无法继续。")
        logger.info("请在终端使用 'export DEEPSEEK_API_KEY=\"your_key_here\"' 命令设置。")
        sys.exit(1)
    
    # 验证API密钥格式（基本检查）
    if len(api_key.strip()) < 10:
        logger.error("DEEPSEEK_API_KEY 格式可能不正确，长度过短")
        sys.exit(1)

    # 3. 初始化邮件发送模块
    try:
        smtp_server = os.getenv("SMTP_SERVER")
        sender_email = os.getenv("SENDER_EMAIL")
        sender_password = os.getenv("SENDER_PASSWORD")
        # 优先使用期货策略专用收件人，如果没有则使用通用收件人
        email_recipients = os.getenv("EMAIL_RECIPIENTS_FUTURES") or os.getenv("EMAIL_RECIPIENTS")
        
        if all([smtp_server, sender_email, sender_password, email_recipients]):
            # 处理多个收件人（用逗号分隔）
            to_addr_list = [addr.strip() for addr in email_recipients.split(',')]
            setup_email(smtp_server, sender_email, sender_password, to_addr_list)
            logger.info(f"邮件发送模块初始化成功，期货策略收件人: {email_recipients}")
        else:
            logger.warning("邮件配置不完整，将跳过邮件通知功能")
            logger.info("需要设置环境变量: SMTP_SERVER, SENDER_EMAIL, SENDER_PASSWORD, EMAIL_RECIPIENTS_FUTURES 或 EMAIL_RECIPIENTS")
    except Exception as e:
        logger.warning(f"邮件发送模块初始化失败: {e}")

    # 4. 加载AI导师配置
    load_master_agent_prompt()
    
    # 5. 检查AI导师配置文件
    if not os.path.exists(AGENT_PROMPT_JSON_PATH):
        logger.warning(f"AI导师配置文件 {AGENT_PROMPT_JSON_PATH} 不存在，将使用默认配置")
    
    logger.info("系统初始化完成")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='期货期权策略跟踪系统')
    parser.add_argument('--test-mode', action='store_true', help='测试模式：忽略交易时间限制')
    parser.add_argument('--force-run', action='store_true', help='强制运行一次分析')
    parser.add_argument('--run-once', action='store_true', help='运行一次性分析（兼容旧参数）')
    
    args = parser.parse_args()
    
    try:
        init()
        
        if not MASTER_AGENT_PROMPT:
            logger.error("AI导师配置未能加载，程序退出。")
            sys.exit(1)

        if args.run_once or args.force_run:
            logger.info("运行一次性分析...")
            job(test_mode=args.test_mode, force_run=True)
            logger.info("一次性分析完成。")
        else:
            run_scheduler(test_mode=args.test_mode)
            
    except Exception as e:
        error_msg = f"程序主流程运行出错: {str(e)}"
        logger.error(error_msg, exc_info=True)
        try:
            send_notification(f"期货策略程序运行出错: {str(e)}")
        except Exception as notify_e:
            logger.error(f"发送错误通知也失败了: {notify_e}")
