#!/bin/bash

# 电池成本监测与价格预测系统 - Docker启动脚本

echo "🐳 启动电池成本监测与价格预测系统 (Docker版)"
echo "🎯 专注分析: 碳酸锂(LC)"
echo "🤖 集成AI导师: 趋势研判智能体"
echo "🌐 Web服务器: http://localhost:5000"
echo "=========================================="

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: 未找到Docker，请先安装Docker"
    exit 1
fi

# 检查docker-compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ 错误: 未找到docker-compose，请先安装docker-compose"
    exit 1
fi

# 检查项目目录
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ 错误: 请在项目根目录下运行此脚本"
    exit 1
fi

# 检查环境变量文件
if [ ! -f ".env" ]; then
    echo "⚠️  警告: 未找到.env文件"
    echo "   建议创建.env文件并设置必要的API密钥"
    echo "   可以复制 env_example.txt 为 .env 并填入DeepSeek API密钥"
    echo ""
    read -p "是否继续启动？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p output/{charts,predictions,dashboard,reports}
mkdir -p data/{futures_data,cost_history}
mkdir -p logs
mkdir -p ssl  # nginx SSL证书目录

# 设置权限
chmod +x docker-start.sh
chmod +x start_analysis.sh || true

# 停止现有容器
echo "🛑 停止现有容器..."
docker-compose down

# 构建并启动服务
echo "🔨 构建Docker镜像..."
docker-compose build

echo "🚀 启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose ps

# 检查健康状态
echo "🏥 检查应用健康状态..."
for i in {1..30}; do
    if curl -f http://localhost:5000/api/status &>/dev/null; then
        echo "✅ 应用已就绪！"
        break
    fi
    echo "⏳ 等待应用启动... ($i/30)"
    sleep 2
done

# 显示访问信息
echo ""
echo "=========================================="
echo "🎉 Docker部署完成！"
echo ""
echo "📱 访问地址:"
echo "   - 主仪表板: http://localhost:5000"
echo "   - API状态: http://localhost:5000/api/status"
echo ""
echo "🐳 Docker管理命令:"
echo "   - 查看日志: docker-compose logs -f"
echo "   - 停止服务: docker-compose down"
echo "   - 重启服务: docker-compose restart"
echo "   - 查看状态: docker-compose ps"
echo ""
echo "📊 功能特性:"
echo "   - ✅ 实时数据监控"
echo "   - ✅ 手动刷新按钮"
echo "   - ✅ AI智能分析"
echo "   - ✅ 自动数据持久化"
echo "   - ✅ 健康检查"
echo ""
echo "💡 提示:"
echo "   - 点击导航栏的'手动刷新'按钮可立即更新数据"
echo "   - 支持快捷键 Ctrl+R 或 F5 触发刷新"
echo "   - 数据会自动保存到 ./data 和 ./output 目录"
echo "=========================================="

# 可选：启动nginx反向代理
read -p "是否启动nginx反向代理？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🌐 启动nginx反向代理..."
    docker-compose --profile nginx up -d
    echo "✅ nginx已启动，可通过 http://localhost 访问"
fi
