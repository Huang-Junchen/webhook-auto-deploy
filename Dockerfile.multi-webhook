FROM python:3.11-slim

WORKDIR /app

# 安装依赖
RUN pip install flask --no-cache-dir

# 复制 webhook 脚本
COPY webhook-multi.py /app/

EXPOSE 5000

CMD ["python", "webhook-multi.py"]
