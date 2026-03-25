import os

from dotenv import load_dotenv


load_dotenv()


# 电池材料配置
BATTERY_CONFIG = {
    'baseline_total_cost': 3308,  # 基准总成本 (82700/1000 * 40 = 3308)
    'baseline_date': '2024-08-18',  # 基准日期
    'materials': {
        'LC': {  # 碳酸锂
            'name': '锂(电池级碳酸锂)',
            'baseline_price': 82700,  # 元/吨
            'standard_usage': 40,     # kg
            'baseline_cost': 3308,    # 基准成本 (82700/1000 * 40)
        }
        # 移除NI配置，专注LC分析
    }
}

# 图表配置
CHART_CONFIG = {
    'figure_size': (12, 8),
    'dpi': 100,
    'save_format': 'png'
}

# AI导师配置
AI_MENTOR_CONFIG = {
    'prompt_file': 'options_trading_prompt.json',
    'model': 'deepseek-chat',
    'temperature': 0.7,
    'max_tokens': 2000
}

# API 配置
API_CONFIG = {
    'api_key': os.getenv('API_KEY', ''),
    'snapshot_cache_ttl': int(os.getenv('SNAPSHOT_CACHE_TTL', '300')),
    'cors_origins': [origin.strip() for origin in os.getenv('CORS_ORIGINS', 'http://localhost:5001').split(',') if origin.strip()],
}
