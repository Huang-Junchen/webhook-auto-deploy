#!/usr/bin/env python3
"""
通用 GitHub Webhook 服务器 - 支持多个项目自动部署

配置说明：
1. 编辑 config.py 配置项目列表
2. 每个项目指定：路径、compose 文件、分支
3. GitHub Webhook URL: http://your-server:5000/webhook
4. 服务器会自动根据 GitHub 仓库名匹配项目

环境变量：
- WEBHOOK_SECRET: GitHub Webhook 密钥（必填）
- LOG_LEVEL: 日志级别，默认 INFO
"""
from flask import Flask, request, jsonify
import subprocess
import os
import hmac
import hashlib
import logging
import sys
from pathlib import Path

app = Flask(__name__)

# 导入配置
try:
    from config import PROJECTS, DOCKER_USE_SUDO, LOG_LEVEL
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("未找到 config.py，使用空配置")
    PROJECTS = {}
    DOCKER_USE_SUDO = False
    LOG_LEVEL = 'INFO'

# 配置日志
log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 全局配置
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', '')
GITHUB_WEBHOOK_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET', WEBHOOK_SECRET)

if not WEBHOOK_SECRET:
    logger.error("未设置 WEBHOOK_SECRET 环境变量！")
    logger.error("请设置：export WEBHOOK_SECRET=your-secret-key")
    sys.exit(1)


def verify_signature(payload, signature):
    """验证 GitHub Webhook 签名"""
    if not signature:
        logger.warning("缺少签名")
        return False

    try:
        hash_algorithm, github_signature = signature.split('=', 1)
        if hash_algorithm != 'sha256':
            logger.warning(f"不支持的哈希算法: {hash_algorithm}")
            return False

        mac = hmac.new(GITHUB_WEBHOOK_SECRET.encode(), msg=payload, digestmod=hashlib.sha256)
        expected_signature = mac.hexdigest()

        if not hmac.compare_digest(expected_signature, github_signature):
            logger.warning("签名验证失败")
            return False

        return True
    except Exception as e:
        logger.error(f"签名验证异常: {e}")
        return False


def run_command(cmd, cwd=None):
    """执行 shell 命令"""
    try:
        logger.info(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )

        if result.returncode != 0:
            logger.error(f"命令失败: {result.stderr}")
            return False, result.stderr

        logger.info(f"命令成功: {result.stdout}")
        return True, result.stdout
    except subprocess.TimeoutExpired:
        logger.error("命令执行超时")
        return False, "命令执行超时"
    except Exception as e:
        logger.error(f"命令执行异常: {e}")
        return False, str(e)


def deploy_project(project_name):
    """部署指定项目"""
    if project_name not in PROJECTS:
        return False, f"项目 '{project_name}' 未配置"

    project = PROJECTS[project_name]
    project_path = project['path']
    compose_file = project.get('compose_file', 'docker-compose.yml')
    target_branch = project.get('branch', 'main')

    logger.info(f"开始部署项目: {project_name} ({project.get('description', '')})")

    # 检查项目目录
    if not os.path.exists(project_path):
        return False, f"项目路径不存在: {project_path}"

    try:
        # 1. 拉取最新代码
        logger.info(f"[1/3] 拉取 {target_branch} 分支最新代码...")
        success, output = run_command(['git', 'fetch', 'origin'], cwd=project_path)
        if not success:
            return False, f"Git fetch 失败: {output}"

        success, output = run_command(['git', 'checkout', target_branch], cwd=project_path)
        if not success:
            return False, f"Git checkout 失败: {output}"

        success, output = run_command(['git', 'pull', 'origin', target_branch], cwd=project_path)
        if not success:
            return False, f"Git pull 失败: {output}"

        # 2. 停止容器
        logger.info(f"[2/3] 停止 Docker 容器...")
        docker_cmd = ['docker-compose']
        if DOCKER_USE_SUDO:
            docker_cmd = ['sudo'] + docker_cmd

        success, output = run_command(
            docker_cmd + ['-f', compose_file, 'down'],
            cwd=project_path
        )
        if not success:
            logger.warning(f"停止容器失败: {output}")

        # 3. 启动容器
        logger.info(f"[3/3] 启动 Docker 容器...")
        success, output = run_command(
            docker_cmd + ['-f', compose_file, 'up', '-d', '--build'],
            cwd=project_path
        )
        if not success:
            return False, f"启动容器失败: {output}"

        logger.info(f"项目 {project_name} 部署成功！")
        return True, f"项目 '{project_name}' 部署成功"

    except Exception as e:
        logger.error(f"部署异常: {e}")
        return False, f"部署异常: {str(e)}"


@app.route('/webhook/<project_name>', methods=['POST'])
def webhook_project(project_name):
    """处理特定项目的 Webhook"""
    # 验证签名
    if not verify_signature(request.data, request.headers.get('X-Hub-Signature-256')):
        return jsonify({'error': '签名验证失败'}), 403

    # 解析 payload
    try:
        payload = request.json
    except Exception as e:
        logger.error(f"解析 payload 失败: {e}")
        return jsonify({'error': '无效的 JSON'}), 400

    # 检查分支
    ref = payload.get('ref', '')
    expected_ref = f'refs/heads/{PROJECTS[project_name].get("branch", "main")}'

    if ref != expected_ref:
        logger.info(f"忽略非目标分支的推送: {ref}")
        return jsonify({
            'status': 'ignored',
            'message': f'忽略分支 {ref}，只部署 {expected_ref}'
        }), 200

    # 执行部署
    success, message = deploy_project(project_name)

    if success:
        return jsonify({
            'status': 'success',
            'project': project_name,
            'message': message
        }), 200
    else:
        return jsonify({
            'status': 'error',
            'project': project_name,
            'message': message
        }), 500


@app.route('/webhook', methods=['POST'])
def webhook():
    """处理默认 Webhook（自动识别项目）"""
    # 验证签名
    if not verify_signature(request.data, request.headers.get('X-Hub-Signature-256')):
        return jsonify({'error': '签名验证失败'}), 403

    # 解析 payload
    try:
        payload = request.json
    except Exception as e:
        logger.error(f"解析 payload 失败: {e}")
        return jsonify({'error': '无效的 JSON'}), 400

    # 从 GitHub payload 中获取仓库名
    repository_name = payload.get('repository', {}).get('name', '').lower()

    if not repository_name:
        return jsonify({'error': '无法识别仓库'}), 400

    # 查找对应的项目
    project_name = None
    for name, config in PROJECTS.items():
        if repository_name in config['path'].lower() or name == repository_name:
            project_name = name
            break

    if not project_name:
        logger.warning(f"未找到匹配的项目: {repository_name}")
        logger.info(f"已配置的项目: {list(PROJECTS.keys())}")
        return jsonify({
            'status': 'ignored',
            'message': f'未配置项目 {repository_name}'
        }), 200

    # 检查分支
    ref = payload.get('ref', '')
    expected_ref = f'refs/heads/{PROJECTS[project_name].get("branch", "main")}'

    if ref != expected_ref:
        logger.info(f"忽略非目标分支的推送: {ref}")
        return jsonify({
            'status': 'ignored',
            'message': f'忽略分支 {ref}，只部署 {expected_ref}'
        }), 200

    # 执行部署
    success, message = deploy_project(project_name)

    if success:
        return jsonify({
            'status': 'success',
            'project': project_name,
            'repository': repository_name,
            'message': message
        }), 200
    else:
        return jsonify({
            'status': 'error',
            'project': project_name,
            'repository': repository_name,
            'message': message
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    try:
        import subprocess
        timestamp = subprocess.run(['date'], capture_output=True, text=True).stdout.strip()
    except:
        from datetime import datetime
        timestamp = datetime.now().isoformat()

    return jsonify({
        'status': 'ok',
        'projects': list(PROJECTS.keys()),
        'timestamp': timestamp
    }), 200


@app.route('/projects', methods=['GET'])
def list_projects():
    """列出所有配置的项目"""
    projects_info = []
    for name, config in PROJECTS.items():
        projects_info.append({
            'name': name,
            'description': config.get('description', ''),
            'path': config['path'],
            'branch': config.get('branch', 'main'),
            'compose_file': config.get('compose_file', 'docker-compose.yml')
        })

    return jsonify({
        'total': len(projects_info),
        'projects': projects_info
    }), 200


@app.route('/deploy/<project_name>', methods=['POST'])
def manual_deploy(project_name):
    """手动触发部署（用于测试）"""
    success, message = deploy_project(project_name)

    if success:
        return jsonify({
            'status': 'success',
            'project': project_name,
            'message': message
        }), 200
    else:
        return jsonify({
            'status': 'error',
            'project': project_name,
            'message': message
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('WEBHOOK_PORT', 5000))
    logger.info("=" * 60)
    logger.info("通用 GitHub Webhook 服务器启动")
    logger.info(f"监听端口: {port}")
    logger.info(f"已配置项目: {', '.join(PROJECTS.keys())}")
    logger.info("=" * 60)

    # 打印项目列表
    for name, config in PROJECTS.items():
        logger.info(f"  - {name}: {config.get('description', '')} ({config['path']})")

    app.run(host='0.0.0.0', port=port)
