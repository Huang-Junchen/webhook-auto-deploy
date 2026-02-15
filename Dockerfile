FROM python:3.11-slim

WORKDIR /app

# 先复制依赖文件
COPY requirements.txt /app/

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY webhook-server.py /app/
COPY config.example.py /app/

EXPOSE 5000

CMD ["python", "webhook-server.py"]
