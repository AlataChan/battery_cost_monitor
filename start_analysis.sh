#!/bin/bash

# 电池成本监测与价格预测系统启动脚本

echo "🚀 启动电池成本监测与价格预测系统..."
echo "🎯 专注分析: 碳酸锂(LC)"
echo "🤖 集成AI导师: 趋势研判智能体"
echo "=========================================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3，请先安装Python3"
    exit 1
fi

# 检查项目目录
if [ ! -f "requirements.txt" ]; then
    echo "❌ 错误: 请在项目根目录下运行此脚本"
    exit 1
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p output/{charts,predictions,dashboard,reports}
mkdir -p data/{futures_data,cost_history}
mkdir -p logs

# 检查依赖
echo "📦 检查Python依赖..."
if [ ! -d "venv" ]; then
    echo "🔧 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📦 安装项目依赖..."
pip install -r requirements.txt

# 检查环境变量
if [ ! -f ".env" ]; then
    echo "⚠️  警告: 未找到.env文件，将使用默认配置"
    echo "   建议创建.env文件并设置必要的API密钥"
    echo "   可以复制 env_example.txt 为 .env 并填入DeepSeek API密钥"
fi

# 运行分析
echo "🔍 开始运行分析..."
echo "=========================================="

# 运行完整分析
python3 scripts/run_full_analysis.py

echo "=========================================="
echo "🎉 分析完成！"
echo "📁 请查看以下文件:"
echo "   - 仪表板: output/dashboard.html"
echo "   - 图表: output/charts/"
echo "   - 报告: output/reports/"
echo ""
echo "💡 提示: 可以设置定时任务来自动运行分析"
echo "   例如: crontab -e 添加: 0 */4 * * * cd /path/to/battery_cost_monitor && ./start_analysis.sh"
