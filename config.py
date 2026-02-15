# Webhook 项目配置文件
#
# 使用说明：
# 1. 复制此文件为 config_local.py
# 2. 修改下面的项目配置
# 3. 在 docker-compose.yml 中挂载配置文件
#
# 或者直接修改此文件用于生产环境

from typing import Dict, Any

# 项目配置列表
# 格式：'项目名': {'path': '项目路径', 'compose_file': 'compose文件', 'branch': '分支', 'description': '描述'}
PROJECTS: Dict[str, Dict[str, Any]] = {
    'recipe': {
        'path': '/volume1/docker/recipe',       # 项目在 NAS 上的实际路径
        'compose_file': 'docker-compose.yml',     # Docker Compose 文件名
        'branch': 'main',                      # 监控的 Git 分支
        'description': '食谱系统'                 # 项目描述
    },
    # 添加更多项目...
    # 'blog': {
    #     'path': '/volume1/docker/blog',
    #     'compose_file': 'docker-compose.yml',
    #     'branch': 'main',
    #     'description': '博客系统'
    # },
}

# Docker 配置
DOCKER_USE_SUDO: bool = False  # Docker 命令是否需要 sudo

# 日志级别
# 可选值：DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL: str = 'INFO'
