# 多项目 GitHub Webhook 自动部署指南

一个 Webhook 服务器管理 NAS 上多个项目的自动部署。

---

## 🎯 适用场景

- ✅ NAS 上部署了多个 Docker 项目
- ✅ 希望一个 Webhook 服务管理所有项目
- ✅ 各项目独立部署，互不影响
- ✅ 支持自动识别或手动指定项目

---

## 📦 架构说明

```
GitHub Push Event
       ↓
cpolar Tunnel (公网访问)
       ↓
Multi-Webhook Server (localhost:5000)
       ↓
   根据仓库识别项目
       ↓
   ┌─────────┬─────────┬─────────┐
   ↓         ↓         ↓         ↓
 recipe    blog      api     other-project
(独立部署) (独立部署) (独立部署)
```

---

## 🚀 快速开始

### 第一步：配置项目列表

编辑 `webhook-multi.py`，修改 `PROJECTS` 字典：

```python
PROJECTS = {
    'recipe': {
        'path': '/volume1/docker/recipe',        # 项目实际路径
        'compose_file': 'docker-compose.yml',     # Docker Compose 文件名
        'branch': 'main',                        # 监控的分支
        'description': '食谱系统'                 # 项目描述
    },
    'blog': {
        'path': '/volume1/docker/blog',
        'compose_file': 'docker-compose.yml',
        'branch': 'main',
        'description': '博客系统'
    },
    'api': {
        'path': '/volume1/docker/api',
        'compose_file': 'docker-compose.prod.yml',
        'branch': 'main',
        'description': 'API 服务'
    },
}
```

### 第二步：启动 Webhook 服务

```bash
# 1. 修改配置
nano docker-compose.multi-webhook.yml
# 修改 WEBHOOK_SECRET 为强密码
# 修改 volumes 映射到实际的项目目录

# 2. 构建镜像
docker build -f Dockerfile.multi-webhook -t multi-webhook .

# 3. 启动服务
docker-compose -f docker-compose.multi-webhook.yml up -d

# 4. 查看日志
docker logs -f multi-webhook
```

### 第三步：配置 cpolar 隧道

```bash
# 启动 cpolar（映射 5000 端口）
nohup cpolar http 5000 > cpolar.log 2>&1 &

# 查看分配的公网 URL
tail -f cpolar.log
```

记下公网 URL，例如：`https://abc123.cpolar.cn`

---

## 📡 配置 GitHub Webhooks

### 方式 1：自动识别（推荐）

每个 GitHub 仓库配置相同的 Webhook URL：

**所有仓库的 Webhook URL：**
```
https://abc123.cpolar.cn/webhook
```

**工作原理：**
- Webhook 服务器根据 GitHub 仓库的 `repository.name` 自动识别项目
- 自动匹配到配置的项目列表

**配置示例：**

1. **recipe 仓库的 Webhook：**
   - Payload URL: `https://abc123.cpolar.cn/webhook`
   - Secret: 你的 WEBHOOK_SECRET
   - Events: Just the push event

2. **blog 仓库的 Webhook：**
   - Payload URL: `https://abc123.cpolar.cn/webhook`
   - Secret: 你的 WEBHOOK_SECRET（相同）
   - Events: Just the push event

### 方式 2：指定项目名（可选）

如果需要明确指定项目：

**URL 格式：** `https://abc123.cpolar.cn/webhook/项目名`

示例：
- recipe 项目: `https://abc123.cpolar.cn/webhook/recipe`
- blog 项目: `https://abc123.cpolar.cn/webhook/blog`

**注意：** 方式 1（自动识别）更简洁，推荐使用。

---

## 🧪 测试部署

### 测试 1：健康检查

```bash
# 检查服务状态
curl http://localhost:5000/health

# 返回示例
{
  "status": "ok",
  "projects": ["recipe", "blog", "api"],
  "timestamp": "Sat Feb 14 12:00:00 CST 2026"
}
```

### 测试 2：查看项目列表

```bash
curl http://localhost:5000/projects

# 返回示例
{
  "total": 3,
  "projects": [
    {
      "name": "recipe",
      "description": "食谱系统",
      "path": "/volume1/docker/recipe",
      "branch": "main",
      "compose_file": "docker-compose.yml"
    },
    ...
  ]
}
```

### 测试 3：手动触发部署

```bash
# 部署指定项目
curl -X POST http://localhost:5000/deploy/recipe

# 返回示例
{
  "status": "success",
  "project": "recipe",
  "message": "项目 'recipe' 部署成功"
}
```

### 测试 4：实际推送代码

```bash
# 在本地修改代码并推送
git push origin main

# 查看 webhook 日志
docker logs -f multi-webhook
```

**成功输出：**
```
[2026-02-14 12:00:00] INFO - 开始部署项目: recipe (食谱系统)
[2026-02-14 12:00:00] INFO - [1/3] 拉取 main 分支最新代码...
[2026-02-14 12:00:01] INFO - 执行命令: git fetch origin
[2026-02-14 12:00:05] INFO - [2/3] 停止 Docker 容器...
[2026-02-14 12:00:08] INFO - [3/3] 启动 Docker 容器...
[2026-02-14 12:00:15] INFO - 项目 recipe 部署成功！
```

---

## 🔧 高级配置

### 1. 不同分支的部署

```python
PROJECTS = {
    'recipe': {
        'path': '/volume1/docker/recipe',
        'compose_file': 'docker-compose.yml',
        'branch': 'main',  # 监听 main 分支
    },
    'recipe-dev': {
        'path': '/volume1/docker/recipe-dev',
        'compose_file': 'docker-compose.yml',
        'branch': 'develop',  # 监听 develop 分支
    },
}
```

### 2. 不同的 Docker Compose 文件

```python
PROJECTS = {
    'blog': {
        'path': '/volume1/docker/blog',
        'compose_file': 'docker-compose.prod.yml',  # 生产环境配置
        'branch': 'main',
    },
    'blog-staging': {
        'path': '/volume1/docker/blog-staging',
        'compose_file': 'docker-compose.staging.yml',  # 测试环境配置
        'branch': 'main',
    },
}
```

### 3. 需要 sudo 的 Docker

如果 Docker 需要 sudo 权限：

```yaml
# docker-compose.multi-webhook.yml
environment:
  - DOCKER_USE_SUDO=true
```

### 4. 自定义部署脚本

如果项目不使用 Docker Compose，可以修改 `deploy_project` 函数添加自定义部署逻辑。

---

## 📊 监控和日志

### 查看 Webhook 日志

```bash
# 实时监控
docker logs -f multi-webhook

# 查看最近 100 行
docker logs --tail 100 multi-webhook

# 带时间戳
docker logs -f multi-webhook | while read line; do echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line"; done
```

### 查看各项目日志

```bash
# recipe 项目
docker-compose -f /path/to/recipe/docker-compose.yml logs -f

# blog 项目
docker-compose -f /path/to/blog/docker-compose.yml logs -f
```

### 设置日志轮转

编辑 `/etc/logrotate.d/docker`：

```
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    size 10M
    missingok
    delaycompress
    copytruncate
}
```

---

## 🔒 安全建议

### 1. 使用强密码

```bash
# 生成随机密码
openssl rand -hex 32
```

### 2. 限制 GitHub IP（可选）

在 `webhook-multi.py` 中添加：

```python
ALLOWED_IPS = ['192.30.252.0/22', '185.199.108.0/22']

@app.before_request
def limit_remote_addr():
    if request.endpoint not in ['health', 'projects']:
        if request.remote_addr not in ALLOWED_IPS:
            return jsonify({'error': 'IP not allowed'}), 403
```

### 3. 启用 HTTPS（推荐）

cpolar 默认提供 HTTPS，无需额外配置。

### 4. 定期备份

```bash
# 备份脚本
#!/bin/bash
BACKUP_DIR="/volume1/backups"
DATE=$(date +%Y%m%d)

# 备份各项目的数据库
docker-compose -f /path/to/recipe/docker-compose.yml exec db pg_dump -U user recipe > $BACKUP_DIR/recipe_$DATE.sql
docker-compose -f /path/to/blog/docker-compose.yml exec db pg_dump -U user blog > $BACKUP_DIR/blog_$DATE.sql

# 保留最近 7 天
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
```

---

## 🐛 故障排查

### 问题 1：无法识别项目

**症状：** 日志显示 "未找到匹配的项目"

**解决：**
1. 检查 GitHub 仓库名是否在 PROJECTS 中配置
2. 或者在 GitHub Webhook 中使用 `/webhook/项目名` 格式

### 问题 2：Docker 权限错误

**症状：** "permission denied while trying to connect to the Docker daemon"

**解决：**
```yaml
# docker-compose.multi-webhook.yml
environment:
  - DOCKER_USE_SUDO=true
```

或添加用户到 docker 组：
```bash
sudo usermod -aG docker $USER
```

### 问题 3：端口冲突

**症状：** "address already in use"

**解决：**
```bash
# 检查端口占用
netstat -tulpn | grep 5000

# 修改端口
environment:
  - WEBHOOK_PORT=5001

ports:
  - "5001:5001"
```

### 问题 4：Git pull 失败

**症状：** "Git pull 失败"

**解决：**
1. 检查网络连接
2. 确认 Git 仓库地址正确
3. 检查分支名称是否匹配

---

## 📚 API 参考

### Webhook 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/webhook` | POST | 自动识别并部署项目 |
| `/webhook/<项目名>` | POST | 部署指定项目 |
| `/health` | GET | 健康检查 |
| `/projects` | GET | 列出所有项目 |
| `/deploy/<项目名>` | POST | 手动触发部署 |

### 请求/响应示例

**请求：**
```bash
curl -X POST http://localhost:5000/deploy/recipe
```

**成功响应：** (200 OK)
```json
{
  "status": "success",
  "project": "recipe",
  "message": "项目 'recipe' 部署成功"
}
```

**失败响应：** (500 Internal Server Error)
```json
{
  "status": "error",
  "project": "recipe",
  "message": "Git pull 失败: ..."
}
```

---

## 🎉 完成！

现在您可以使用 **一个 Webhook 服务器管理 NAS 上的所有项目**！

每个项目推送代码后都会自动更新部署，互不干扰。

享受自动化的便利吧！🚀
