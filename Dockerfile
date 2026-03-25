# 使用稳定版 Debian bookworm 变体，避免 trixie 源波动导致 apt 失败
FROM python:3.12-slim-bookworm

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=web_server.py
ENV FLASK_ENV=production

# 安装运行时依赖；优先依赖 Python wheels，避免无必要的编译工具链
RUN set -eux; \
    apt-get -o Acquire::Retries=5 update; \
    for attempt in 1 2 3 4 5; do \
        apt-get install -y --fix-missing --no-install-recommends \
            wget \
            curl \
            tzdata && break; \
        if [ "$attempt" -eq 5 ]; then \
            exit 1; \
        fi; \
        sleep 5; \
        apt-get -o Acquire::Retries=5 update; \
    done; \
    rm -rf /var/lib/apt/lists/*

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p output/charts output/reports output/dashboard output/predictions \
    && mkdir -p data/futures_data data/cost_history \
    && mkdir -p logs \
    && mkdir -p src/charts src/core src/utils

# 设置权限
RUN chmod +x start_analysis.sh || true
RUN chmod +x web_server.py

# 暴露端口
EXPOSE 5001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/api/status || exit 1

# 启动命令
CMD ["python3", "web_server.py"]
