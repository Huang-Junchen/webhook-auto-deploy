FROM python:3.11-slim

WORKDIR /app

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY webhook-server.py /app/
COPY config.py /app/

EXPOSE 5000

CMD ["python", "webhook-server.py"]
