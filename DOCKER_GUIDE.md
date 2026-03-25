# 🐳 Docker部署指南

## 📋 前置要求

### 系统要求
- **操作系统**: Windows 10/11, macOS, Linux
- **内存**: 建议4GB+
- **磁盘空间**: 建议2GB+
- **网络**: 需要访问期货数据API和DeepSeek API

### 软件要求
- **Docker Desktop**: 最新版本
- **docker-compose**: 通常随Docker Desktop一起安装

## 🚀 快速开始

### 1. 环境准备
```bash
# 克隆项目
git clone <repository-url>
cd battery_cost_monitor

# 配置环境变量
cp env_example.txt .env
# 编辑.env文件，至少设置DEEPSEEK_API_KEY
```

### 2. 一键启动

#### Windows用户
```cmd
# 双击运行或命令行执行
docker-start.bat
```

#### Linux/macOS用户
```bash
chmod +x docker-start.sh
./docker-start.sh
```

### 3. 访问系统
- **主仪表板**: http://localhost:5001
- **API状态**: http://localhost:5001/api/status

## 🎛️ 功能特性

### 🔄 手动刷新功能
- **按钮刷新**: 点击导航栏的"手动刷新"按钮
- **快捷键**: 支持 `Ctrl+R` 或 `F5` 快捷键
- **API刷新**: POST请求到 `/api/refresh`

### 📊 实时监控
- 自动数据更新（按原频率）
- 手动触发即时更新
- 实时通知提醒
- 数据持久化存储

### 🤖 AI智能分析
- DeepSeek AI导师分析
- 多重技术指标确认
- 智能投资建议
- 风险评估报告

## 🐳 Docker管理

### 常用命令
```bash
# 查看运行状态
docker-compose ps

# 查看实时日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f battery-monitor

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 完全清理（包括数据卷）
docker-compose down -v
```

### 服务管理
```bash
# 仅启动主服务
docker-compose up -d battery-monitor

# 启动包含nginx的完整服务
docker-compose --profile nginx up -d

# 重新构建镜像
docker-compose build --no-cache

# 更新服务
docker-compose pull && docker-compose up -d
```

## 📁 数据持久化

### 数据目录映射
- `./data` → `/app/data` (期货数据、成本历史)
- `./output` → `/app/output` (图表、报告、仪表板)
- `./logs` → `/app/logs` (系统日志)

### 备份数据
```bash
# 备份数据目录
tar -czf backup_$(date +%Y%m%d).tar.gz data output logs

# 恢复数据
tar -xzf backup_20241222.tar.gz
```

## 🔧 配置说明

### 环境变量
```bash
# 必需配置
DEEPSEEK_API_KEY=your_api_key_here

# 可选配置
SMTP_SERVER=smtp.gmail.com
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_password
EMAIL_RECIPIENTS=recipient@example.com

# 系统配置
LOG_LEVEL=INFO
CACHE_ENABLED=true
CACHE_EXPIRY=300
```

### 端口配置
- **5000**: 主应用端口
- **80**: nginx反向代理端口（可选）
- **443**: HTTPS端口（可选，需要SSL证书）

## 🔍 故障排除

### 常见问题

#### 1. 容器启动失败
```bash
# 检查日志
docker-compose logs battery-monitor

# 检查端口占用
netstat -tulpn | grep 5000

# 重新构建
docker-compose build --no-cache
```

#### 2. API连接失败
```bash
# 检查环境变量
docker-compose exec battery-monitor env | grep DEEPSEEK

# 测试网络连接
docker-compose exec battery-monitor curl -I https://api.deepseek.com
```

#### 3. 数据获取失败
```bash
# 检查akshare连接
docker-compose exec battery-monitor python -c "import akshare as ak; print(ak.__version__)"

# 手动测试数据获取
docker-compose exec battery-monitor python -c "
import akshare as ak
data = ak.futures_zh_minute_sina('LC0', '5')
print(data.head())
"
```

#### 4. 权限问题
```bash
# 修复数据目录权限
sudo chown -R $USER:$USER data output logs

# 或者使用Docker用户
docker-compose exec battery-monitor chown -R app:app /app/data
```

### 性能优化

#### 内存优化
```yaml
# 在docker-compose.yml中添加内存限制
services:
  battery-monitor:
    mem_limit: 1g
    memswap_limit: 1g
```

#### 缓存优化
```bash
# 清理Docker缓存
docker system prune -a

# 清理应用缓存
docker-compose exec battery-monitor rm -rf /app/data/futures_data/cache/*
```

## 🔒 安全建议

### 1. API密钥安全
- 不要在代码中硬编码API密钥
- 使用.env文件管理敏感信息
- 定期轮换API密钥

### 2. 网络安全
- 使用nginx反向代理
- 配置SSL证书（生产环境）
- 限制访问IP（如需要）

### 3. 数据安全
- 定期备份重要数据
- 使用Docker secrets管理敏感配置
- 监控系统访问日志

## 📈 监控和维护

### 健康检查
```bash
# 检查应用健康状态
curl http://localhost:5000/api/status

# 检查Docker健康状态
docker-compose ps
```

### 日志管理
```bash
# 查看最近100行日志
docker-compose logs --tail=100 battery-monitor

# 按时间过滤日志
docker-compose logs --since="2024-12-22T10:00:00" battery-monitor
```

### 性能监控
```bash
# 查看资源使用情况
docker stats

# 查看容器详细信息
docker inspect battery-cost-monitor
```

## 🆙 升级指南

### 更新应用
```bash
# 1. 备份数据
tar -czf backup_before_update.tar.gz data output

# 2. 拉取最新代码
git pull origin main

# 3. 重新构建并启动
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 4. 验证更新
curl http://localhost:5000/api/status
```

### 版本回滚
```bash
# 1. 停止当前服务
docker-compose down

# 2. 恢复代码版本
git checkout <previous-commit>

# 3. 恢复数据（如需要）
tar -xzf backup_before_update.tar.gz

# 4. 重新启动
docker-compose up -d
```

## 📞 技术支持

如果遇到问题，请：
1. 查看本文档的故障排除部分
2. 检查项目的GitHub Issues
3. 提供详细的错误日志和环境信息
