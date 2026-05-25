# ============================================
# 公考数量关系 AI 学习系统 - Dockerfile
# ============================================
FROM python:3.10-slim

LABEL maintainer="gaokao-number"
LABEL description="公考数量关系 AI 个性化学习系统"

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p data

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 默认启动 Web 服务
CMD ["python", "web_server.py"]
