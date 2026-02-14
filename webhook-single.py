#!/usr/bin/env python3
"""
GitHub Webhook 服务器
监听 GitHub push 事件，自动更新并重启 Docker 容器
"""
from flask import Flask, request, jsonify
import subprocess
import os
import hmac
import hashlib

app = Flask(__name__)

# 配置
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'your-secret-key-change-this')  # 请修改为强密码
PROJECT_DIR = '/path/to/recipe'  # 请修改为实际项目路径

def verify_signature(payload, signature):
    """验证 GitHub Webhook 签名"""
    if 'X-Hub-Signature-256' not in request.headers:
        return False

    hash_algorithm, github_signature = request.headers['X-Hub-Signature-256'].split('=', 1)
    algorithm = hashlib.sha256

    mac = hmac.new(WEBHOOK_SECRET.encode(), msg=payload, digestmod=algorithm)
    expected_signature = mac.hexdigest()

    return hmac.compare_digest(expected_signature, github_signature)

def deploy():
    """执行部署操作"""
    try:
        os.chdir(PROJECT_DIR)

        # 1. 拉取最新代码
        subprocess.run(['git', 'pull', 'origin', 'main'], check=True)

        # 2. 重建并重启 Docker 容器
        subprocess.run(['docker-compose', 'down'], check=True)
        subprocess.run(['docker-compose', 'up', '-d', '--build'], check=True)

        return True, "部署成功！"
    except subprocess.CalledProcessError as e:
        return False, f"部署失败: {str(e)}"
    except Exception as e:
        return False, f"错误: {str(e)}"

@app.route('/webhook', methods=['POST'])
def webhook():
    """处理 GitHub Webhook 请求"""
    # 验证签名
    if not verify_signature(request.data, request.headers.get('X-Hub-Signature-256')):
        return jsonify({'error': '签名验证失败'}), 403

    # 解析 payload
    payload = request.json

    # 检查是否是 push 事件
    if payload.get('ref') == 'refs/heads/main':
        success, message = deploy()
        if success:
            return jsonify({'status': 'success', 'message': message}), 200
        else:
            return jsonify({'status': 'error', 'message': message}), 500

    return jsonify({'status': 'ignored', 'message': '不是 main 分支的 push 事件'}), 200

@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    # 从环境变量读取端口
    port = int(os.environ.get('WEBHOOK_PORT', 5000))
    app.run(host='0.0.0.0', port=port)
