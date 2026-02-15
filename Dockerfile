FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    openssh-client \
    docker-compose \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件
COPY requirements.txt /app/

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY webhook-server.py /app/
COPY config.example.py /app/

EXPOSE 5000

CMD ["python", "webhook-server.py"]
