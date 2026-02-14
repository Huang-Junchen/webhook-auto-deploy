# Webhook 项目配置示例
#
# 使用说明：
# 1. 复制此文件为 config.py
# 2. 根据实际情况修改下面的配置
# 3. 在 docker-compose.yml 中挂载配置文件（已默认配置）

# 项目配置列表
PROJECTS = {
    # 示例：recipe 项目
    # 'recipe': {
    #     'path': '/volume1/docker/recipe',       # NAS 上的实际路径
    #     'compose_file': 'docker-compose.yml',     # Docker Compose 文件名
    #     'branch': 'main',                      # 监控的分支
    #     'description': '食谱系统'                 # 项目描述
    # },

    # 示例：blog 项目
    # 'blog': {
    #     'path': '/volume1/docker/blog',
    #     'compose_file': 'docker-compose.yml',
    #     'branch': 'main',
    #     'description': '博客系统'
    # },

    # 添加更多项目...
}

# Docker 配置
DOCKER_USE_SUDO = False  # Docker 命令是否需要 sudo（通常为 False）

# 日志级别
# 可选值：DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = 'INFO'
