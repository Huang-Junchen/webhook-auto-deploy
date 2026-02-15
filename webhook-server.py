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
- WEBHOOK_PORT: 服务端口，默认 5000
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
from typing import TypedDict, Optional, Tuple, Any, Dict, List
from dataclasses import dataclass

# ============ 类型定义 ============

class ProjectConfig(TypedDict):
    """项目配置类型"""
    path: str
    compose_file: str
    branch: str
    description: str


class WebhookResponse(TypedDict):
    """Webhook 响应类型"""
    status: str
    message: str


class ErrorResponse(TypedDict):
    """错误响应类型"""
    error: str


# ============ 常量定义 ============

DEFAULT_WEBHOOK_PORT = 5000
DEFAULT_LOG_LEVEL = 'INFO'
DEFAULT_BRANCH = 'main'
DEFAULT_COMPOSE_FILE = 'docker-compose.yml'
COMMAND_TIMEOUT = 300  # 5分钟超时
HASH_ALGORITHM = 'sha256'
REF_PREFIX = 'refs/heads/'
SIGNATURE_HEADER = 'X-Hub-Signature-256'


# ============ Flask 应用初始化 ============

app = Flask(__name__)

# 导入配置
PROJECTS: Dict[str, ProjectConfig] = {}
DOCKER_USE_SUDO = False
LOG_LEVEL = DEFAULT_LOG_LEVEL

try:
    from config import PROJECTS, DOCKER_USE_SUDO, LOG_LEVEL
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("未找到 config.py，使用空配置")
    PROJECTS = {}
    DOCKER_USE_SUDO = False
    LOG_LEVEL = DEFAULT_LOG_LEVEL

# 配置日志
log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 全局配置
WEBHOOK_SECRET: str = os.environ.get('WEBHOOK_SECRET', '')
GITHUB_WEBHOOK_SECRET: str = os.environ.get('GITHUB_WEBHOOK_SECRET', WEBHOOK_SECRET)

if not WEBHOOK_SECRET:
    logger.error("未设置 WEBHOOK_SECRET 环境变量！")
    logger.error("请设置：export WEBHOOK_SECRET=your-secret-key")
    sys.exit(1)


def verify_signature(payload: bytes, signature: Optional[str]) -> bool:
    """验证 GitHub Webhook 签名"""
    if not signature:
        logger.warning("缺少签名")
        return False

    try:
        hash_algorithm, github_signature = signature.split('=', 1)
        if hash_algorithm != HASH_ALGORITHM:
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


def run_command(cmd: List[str], cwd: Optional[str] = None) -> Tuple[bool, str]:
    """执行 shell 命令"""
    try:
        logger.info(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT
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


def deploy_project(project_name: str) -> Tuple[bool, str]:
    """部署指定项目

    Args:
        project_name: 项目名称

    Returns:
        (是否成功, 消息)
    """
    if project_name not in PROJECTS:
        return False, f"项目 '{project_name}' 未配置"

    project = PROJECTS[project_name]
    project_path = project['path']
    compose_file = project.get('compose_file', DEFAULT_COMPOSE_FILE)
    target_branch = project.get('branch', DEFAULT_BRANCH)

    logger.info(f"开始部署项目: {project_name} ({project.get('description', '')})")

    try:
        # 0. 配置 Git 安全目录（解决所有权问题）
        success, output = run_command(['git', 'config', '--global', '--add', 'safe.directory', project_path], cwd=project_path)
        if not success:
            logger.warning(f"Git 安全目录配置失败: {output}")

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


# ============ 辅助函数 ============

def validate_webhook_request() -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """验证 Webhook 请求并返回 payload

    Returns:
        (是否有效, payload对象, 错误信息)
    """
    # 验证签名
    if not verify_signature(request.data, request.headers.get(SIGNATURE_HEADER)):
        return False, None, '签名验证失败'

    # 解析 payload
    try:
        payload = request.json
    except Exception as e:
        logger.error(f"解析 payload 失败: {e}")
        return False, None, '无效的 JSON'

    return True, payload, None


def check_branch_match(ref: str, project_name: str) -> bool:
    """检查推送的分支是否匹配项目配置的分支

    Args:
        ref: GitHub payload 中的 ref 字段
        project_name: 项目名称

    Returns:
        是否匹配
    """
    expected_ref = f'{REF_PREFIX}{PROJECTS[project_name].get("branch", DEFAULT_BRANCH)}'
    return ref == expected_ref


def get_repository_project(payload: Dict[str, Any]) -> Optional[str]:
    """从 payload 中获取匹配的项目名

    Args:
        payload: GitHub webhook payload

    Returns:
        项目名或 None
    """
    repository_name = payload.get('repository', {}).get('name', '').lower()

    if not repository_name:
        return None

    # 查找对应的项目
    for name, config in PROJECTS.items():
        if repository_name in config['path'].lower() or name == repository_name:
            return name

    return None


def success_response(data: Dict[str, Any], status: int = 200) -> Tuple[Any, int]:
    """返回成功的 JSON 响应"""
    return jsonify(data), status


def error_response(message: str, status: int = 500) -> Tuple[Any, int]:
    """返回错误的 JSON 响应"""
    return jsonify({'error': message}), status


def ignored_response(message: str) -> Tuple[Any, int]:
    """返回忽略的 JSON 响应"""
    return jsonify({'status': 'ignored', 'message': message}), 200


@app.route('/webhook/<project_name>', methods=['POST'])
def webhook_project(project_name: str):
    """处理特定项目的 Webhook"""
    # 验证请求
    valid, payload, error = validate_webhook_request()
    if not valid:
        return error_response(error, 403 if error == '签名验证失败' else 400)

    # 检查分支
    ref = payload.get('ref', '')
    if not check_branch_match(ref, project_name):
        expected_ref = f'{REF_PREFIX}{PROJECTS[project_name].get("branch", DEFAULT_BRANCH)}'
        logger.info(f"忽略非目标分支的推送: {ref}")
        return ignored_response(f'忽略分支 {ref}，只部署 {expected_ref}')

    # 执行部署
    success, message = deploy_project(project_name)

    if success:
        return success_response({
            'status': 'success',
            'project': project_name,
            'message': message
        })
    else:
        return success_response({
            'status': 'error',
            'project': project_name,
            'message': message
        }, 500)


@app.route('/webhook', methods=['POST'])
def webhook():
    """处理默认 Webhook（自动识别项目）"""
    # 验证请求
    valid, payload, error = validate_webhook_request()
    if not valid:
        return error_response(error, 403 if error == '签名验证失败' else 400)

    # 从 GitHub payload 中获取仓库名
    repository_name = payload.get('repository', {}).get('name', '').lower()

    if not repository_name:
        return error_response('无法识别仓库', 400)

    # 查找对应的项目
    project_name = get_repository_project(payload)

    if not project_name:
        logger.warning(f"未找到匹配的项目: {repository_name}")
        logger.info(f"已配置的项目: {list(PROJECTS.keys())}")
        return ignored_response(f'未配置项目 {repository_name}')

    # 检查分支
    ref = payload.get('ref', '')
    if not check_branch_match(ref, project_name):
        expected_ref = f'{REF_PREFIX}{PROJECTS[project_name].get("branch", DEFAULT_BRANCH)}'
        logger.info(f"忽略非目标分支的推送: {ref}")
        return ignored_response(f'忽略分支 {ref}，只部署 {expected_ref}')

    # 执行部署
    success, message = deploy_project(project_name)

    if success:
        return success_response({
            'status': 'success',
            'project': project_name,
            'repository': repository_name,
            'message': message
        })
    else:
        return success_response({
            'status': 'error',
            'project': project_name,
            'repository': repository_name,
            'message': message
        }, 500)


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    try:
        timestamp = subprocess.run(['date'], capture_output=True, text=True).stdout.strip()
    except Exception:
        from datetime import datetime
        timestamp = datetime.now().isoformat()

    return success_response({
        'status': 'ok',
        'projects': list(PROJECTS.keys()),
        'timestamp': timestamp
    })


@app.route('/projects', methods=['GET'])
def list_projects():
    """列出所有配置的项目"""
    projects_info = []
    for name, config in PROJECTS.items():
        projects_info.append({
            'name': name,
            'description': config.get('description', ''),
            'path': config['path'],
            'branch': config.get('branch', DEFAULT_BRANCH),
            'compose_file': config.get('compose_file', DEFAULT_COMPOSE_FILE)
        })

    return success_response({
        'total': len(projects_info),
        'projects': projects_info
    })


@app.route('/deploy/<project_name>', methods=['POST'])
def manual_deploy(project_name: str):
    """手动触发部署（用于测试）"""
    success, message = deploy_project(project_name)

    if success:
        return success_response({
            'status': 'success',
            'project': project_name,
            'message': message
        })
    else:
        return success_response({
            'status': 'error',
            'project': project_name,
            'message': message
        }, 500)


if __name__ == '__main__':
    port = int(os.environ.get('WEBHOOK_PORT', DEFAULT_WEBHOOK_PORT))

    logger.info("=" * 60)
    logger.info("通用 GitHub Webhook 服务器启动")
    logger.info(f"监听端口: {port}")
    logger.info(f"已配置项目: {', '.join(PROJECTS.keys())}")
    logger.info("=" * 60)

    # 打印项目列表
    for name, config in PROJECTS.items():
        logger.info(f"  - {name}: {config.get('description', '')} ({config['path']})")

    app.run(host='0.0.0.0', port=port)
