@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo 🐳 启动电池成本监测与价格预测系统 (Docker版)
echo 🎯 专注分析: 碳酸锂(LC)
echo 🤖 集成AI导师: 趋势研判智能体
echo 🌐 Web服务器: http://localhost:5000
echo ==========================================

REM 检查Docker是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Docker，请先安装Docker Desktop
    pause
    exit /b 1
)

REM 检查docker-compose是否安装
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到docker-compose，请先安装docker-compose
    pause
    exit /b 1
)

REM 检查项目目录
if not exist "docker-compose.yml" (
    echo ❌ 错误: 请在项目根目录下运行此脚本
    pause
    exit /b 1
)

REM 检查环境变量文件
if not exist ".env" (
    echo ⚠️  警告: 未找到.env文件
    echo    建议创建.env文件并设置必要的API密钥
    echo    可以复制 env_example.txt 为 .env 并填入DeepSeek API密钥
    echo.
    set /p continue="是否继续启动？(y/N): "
    if /i not "!continue!"=="y" (
        exit /b 1
    )
)

REM 创建必要的目录
echo 📁 创建必要的目录...
if not exist "output\charts" mkdir output\charts
if not exist "output\predictions" mkdir output\predictions
if not exist "output\dashboard" mkdir output\dashboard
if not exist "output\reports" mkdir output\reports
if not exist "data\futures_data" mkdir data\futures_data
if not exist "data\cost_history" mkdir data\cost_history
if not exist "logs" mkdir logs
if not exist "ssl" mkdir ssl

REM 停止现有容器
echo 🛑 停止现有容器...
docker-compose down

REM 构建并启动服务
echo 🔨 构建Docker镜像...
docker-compose build

echo 🚀 启动服务...
docker-compose up -d

REM 等待服务启动
echo ⏳ 等待服务启动...
timeout /t 10 /nobreak >nul

REM 检查服务状态
echo 🔍 检查服务状态...
docker-compose ps

REM 检查健康状态
echo 🏥 检查应用健康状态...
set /a count=0
:healthcheck
set /a count+=1
curl -f http://localhost:5000/api/status >nul 2>&1
if errorlevel 0 (
    echo ✅ 应用已就绪！
    goto :ready
)
if !count! geq 30 (
    echo ❌ 应用启动超时，请检查日志
    goto :ready
)
echo ⏳ 等待应用启动... (!count!/30)
timeout /t 2 /nobreak >nul
goto :healthcheck

:ready
echo.
echo ==========================================
echo 🎉 Docker部署完成！
echo.
echo 📱 访问地址:
echo    - 主仪表板: http://localhost:5000
echo    - API状态: http://localhost:5000/api/status
echo.
echo 🐳 Docker管理命令:
echo    - 查看日志: docker-compose logs -f
echo    - 停止服务: docker-compose down
echo    - 重启服务: docker-compose restart
echo    - 查看状态: docker-compose ps
echo.
echo 📊 功能特性:
echo    - ✅ 实时数据监控
echo    - ✅ 手动刷新按钮
echo    - ✅ AI智能分析
echo    - ✅ 自动数据持久化
echo    - ✅ 健康检查
echo.
echo 💡 提示:
echo    - 点击导航栏的'手动刷新'按钮可立即更新数据
echo    - 支持快捷键 Ctrl+R 或 F5 触发刷新
echo    - 数据会自动保存到 .\data 和 .\output 目录
echo ==========================================

REM 可选：启动nginx反向代理
set /p nginx="是否启动nginx反向代理？(y/N): "
if /i "!nginx!"=="y" (
    echo 🌐 启动nginx反向代理...
    docker-compose --profile nginx up -d
    echo ✅ nginx已启动，可通过 http://localhost 访问
)

echo.
echo 按任意键退出...
pause >nul
