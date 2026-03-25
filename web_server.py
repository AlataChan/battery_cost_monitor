#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电池成本监测与价格预测系统 - Web服务器
提供API端点和静态文件服务，支持手动刷新功能
"""

import os
import sys
import json
import threading
import time
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

load_dotenv()

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cost_calculator import BatteryCostCalculator
from chart_generator import ChartGenerator
from dashboard_generator import DashboardGenerator
from config import API_CONFIG
from src.services import AnalysisSnapshot

# 导入新的图表生成器
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'charts'))
try:
    from prediction_charts import PredictionChartGenerator
    from technical_charts import TechnicalChartGenerator
except ImportError:
    print("⚠️ 警告: 无法导入预测和技术图表生成器，将使用基础功能")
    PredictionChartGenerator = None
    TechnicalChartGenerator = None

app = Flask(__name__)
CORS(app, origins=API_CONFIG['cors_origins'])

# 全局变量
last_analysis_time = None
analysis_lock = threading.Lock()
analysis_snapshot = AnalysisSnapshot()


def error_response(code, message, status_code):
    return jsonify({
        'error': True,
        'code': code,
        'message': message,
        'timestamp': datetime.now().isoformat(timespec='seconds')
    }), status_code


@app.before_request
def check_api_key():
    protected_paths = {'/api/latest', '/api/refresh'}
    if request.path not in protected_paths:
        return None

    provided_api_key = request.headers.get('X-API-Key', '')
    expected_api_key = API_CONFIG['api_key']
    if not expected_api_key or provided_api_key != expected_api_key:
        return error_response('AUTH_FAILED', 'Invalid or missing API Key', 401)

    return None


@app.errorhandler(404)
def handle_not_found(_error):
    return error_response('NOT_FOUND', 'Resource not found', 404)


@app.errorhandler(401)
def handle_unauthorized(_error):
    return error_response('AUTH_FAILED', 'Unauthorized', 401)


@app.errorhandler(500)
def handle_internal_error(_error):
    return error_response('INTERNAL_ERROR', 'Internal server error', 500)

def run_full_analysis():
    """执行完整的分析流程"""
    global last_analysis_time
    
    with analysis_lock:
        print("🚀 开始执行完整分析...")
        
        try:
            # 1. 初始化组件
            cost_calculator = BatteryCostCalculator()
            cost_chart_gen = ChartGenerator()
            dashboard_gen = DashboardGenerator()
            
            # 初始化高级图表生成器（如果可用）
            prediction_chart_gen = PredictionChartGenerator() if PredictionChartGenerator else None
            technical_chart_gen = TechnicalChartGenerator() if TechnicalChartGenerator else None
            
            # 2. 执行成本分析
            cost_data = cost_calculator.calculate_current_cost()
            
            # 3. 获取AI导师洞察
            try:
                ai_insights = cost_calculator.get_ai_insights(cost_data)
            except Exception as e:
                print(f"⚠️ 获取AI洞察失败: {e}")
                ai_insights = {'error': True, 'error_message': str(e)}
            
            # 4. 保存成本历史
            cost_calculator.save_cost_history(cost_data)
            
            # 5. 生成图表
            all_charts = {}
            
            # 基础成本图表
            try:
                comp_chart = cost_chart_gen.generate_cost_composition_chart(cost_data)
                if comp_chart:
                    all_charts['cost_composition'] = comp_chart
                
                trend_chart = cost_chart_gen.generate_cost_trend_chart('data/cost_history.csv')
                if trend_chart:
                    all_charts['cost_trend'] = trend_chart
            except Exception as e:
                print(f"❌ 基础图表生成失败: {e}")
            
            # 高级图表（如果可用）
            if prediction_chart_gen and cost_data.get('predictions'):
                try:
                    prediction_charts = prediction_chart_gen.generate_all_charts(cost_data['predictions'])
                    all_charts.update(prediction_charts)
                except Exception as e:
                    print(f"❌ 预测图表生成失败: {e}")
            
            if technical_chart_gen and cost_data.get('predictions'):
                try:
                    technical_charts = technical_chart_gen.generate_all_charts(cost_data['predictions'])
                    all_charts.update(technical_charts)
                except Exception as e:
                    print(f"❌ 技术图表生成失败: {e}")
            
            # 6. 生成仪表板
            dashboard_path = dashboard_gen.generate_dashboard(cost_data, all_charts)
            
            last_analysis_time = datetime.now()
            
            print(f"✅ 分析完成！仪表板: {dashboard_path}")
            return {
                'success': True,
                'message': '分析完成',
                'timestamp': last_analysis_time.strftime('%Y-%m-%d %H:%M:%S'),
                'dashboard_path': dashboard_path,
                'total_cost': cost_data['total_cost'],
                'cost_change': cost_data['cost_change'],
                'cost_change_pct': cost_data['cost_change_pct'],
                'charts_count': len(all_charts)
            }
            
        except Exception as e:
            print(f"❌ 分析失败: {e}")
            return {
                'success': False,
                'message': f'分析失败: {str(e)}',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

@app.route('/')
def index():
    """主页 - 重定向到仪表板"""
    return send_from_directory('output', 'dashboard.html')

@app.route('/dashboard')
def dashboard():
    """仪表板页面"""
    dashboard_path = 'output/dashboard.html'
    if os.path.exists(dashboard_path):
        return send_from_directory('output', 'dashboard.html')
    else:
        # 如果仪表板不存在，先运行一次分析
        result = run_full_analysis()
        if result['success']:
            return send_from_directory('output', 'dashboard.html')
        else:
            return f"<h1>错误</h1><p>{result['message']}</p>", 500

@app.route('/api/refresh', methods=['POST'])
def manual_refresh():
    """手动刷新API端点"""
    global last_analysis_time

    print("📱 收到手动刷新请求...")
    snapshot = analysis_snapshot.get_snapshot(force_refresh=True)
    last_analysis_time = datetime.now()
    return jsonify({
        'success': True,
        'message': '分析刷新完成',
        'snapshot': snapshot,
    })


@app.route('/api/latest')
def api_latest():
    """获取最新分析快照"""
    global last_analysis_time

    snapshot = analysis_snapshot.get_snapshot()
    cached_at = snapshot.get('snapshot_cached_at')
    if cached_at:
        last_analysis_time = datetime.fromisoformat(cached_at)

    return jsonify(snapshot)

@app.route('/api/status')
def get_status():
    """获取系统状态"""
    cache_status = analysis_snapshot.get_cache_status()

    return jsonify({
        'status': 'running',
        'last_analysis_time': cache_status['cached_at'] or (last_analysis_time.strftime('%Y-%m-%d %H:%M:%S') if last_analysis_time else None),
        'snapshot_cached': cache_status['cached'],
        'snapshot_age_seconds': cache_status['age_seconds'],
        'snapshot_ttl_seconds': cache_status['ttl_seconds'],
        'timestamp': datetime.now().isoformat(timespec='seconds')
    })

@app.route('/output/<path:filename>')
def serve_output_files(filename):
    """提供输出文件服务"""
    return send_from_directory('output', filename)

@app.route('/output/charts/<path:filename>')
def serve_chart_files(filename):
    """提供图表文件服务"""
    return send_from_directory('output/charts', filename)

@app.route('/charts/<path:filename>')
def serve_charts(filename):
    """提供图表文件服务（兼容路径）"""
    return send_from_directory('output/charts', filename)

@app.route('/output/reports/<path:filename>')
def serve_report_files(filename):
    """提供报告文件服务"""
    return send_from_directory('output/reports', filename)

@app.route('/favicon.ico')
def favicon():
    """提供favicon"""
    return '', 204  # 返回空内容，状态码204

def create_app():
    """创建Flask应用"""
    # 确保输出目录存在
    os.makedirs('output/charts', exist_ok=True)
    os.makedirs('output/reports', exist_ok=True)
    os.makedirs('output/dashboard', exist_ok=True)
    os.makedirs('data/futures_data', exist_ok=True)
    os.makedirs('data/cost_history', exist_ok=True)
    
    return app

if __name__ == '__main__':
    print("🚀 启动电池成本监测与价格预测系统Web服务器...")
    print("🎯 专注分析: 碳酸锂(LC)")
    print("🤖 集成AI导师: 趋势研判智能体")
    print("🌐 Web服务器: http://localhost:5001")
    print("=" * 60)
    
    app = create_app()
    
    # 启动时运行一次分析
    print("🔍 启动时执行初始分析...")
    initial_result = run_full_analysis()
    if initial_result['success']:
        print(f"✅ 初始分析完成: {initial_result['message']}")
    else:
        print(f"⚠️ 初始分析失败: {initial_result['message']}")
    
    # 启动Web服务器
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
