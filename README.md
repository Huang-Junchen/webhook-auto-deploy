# GitHub Webhook 自动部署服务

一个通用的 GitHub Webhook 服务器，支持管理 NAS 上多个项目的自动部署。

## 📑 目录

- [特性](#-特性)
- [快速开始](#-快速开始)
- [详细部署指南](#-详细部署指南)
- [API 参考](#-api-参考)
- [故障排查](#-故障排查)
- [开发指南](#-开发指南)
- [更新日志](#-更新日志)

---

## ✨ 特性

- 🚀 **实时自动部署**：GitHub 推送后立即更新 NAS 上的项目
- 🎯 **多项目管理**：一个服务管理所有项目，互不干扰
- 🤖 **自动识别**：根据 GitHub 仓库名自动匹配项目
- 🔒 **安全可靠**：HMAC 签名验证，确保请求来自 GitHub
- 📊 **监控友好**：提供 API 端点用于监控和手动触发
- 🐳 **Docker 支持**：开箱即用的 Docker 部署方案
- 🔐 **类型安全**：完整的类型提示，提升代码可靠性
- 📦 **uv 包管理**：使用 uv 快速管理 Python 环境

## 📋 适用场景

- NAS 上部署了多个 Docker 项目
- 希望代码推送后自动更新部署
- 需要统一管理多个项目的自动部署

---

## 🚀 快速开始

### 1. 克隆项目

```bash
cd /volume1/docker  # 或您的项目目录
git clone https://github.com/YOUR_USERNAME/webhook-auto-deploy.git
cd webhook-auto-deploy
```

### 2. 配置项目列表

编辑 `config.py` 文件：

```bash
# 复制示例配置
cp config.example.py config.py

# 编辑配置
nano config.py
```

修改项目配置：

```python
from typing import Dict, Any

PROJECTS: Dict[str, Dict[str, Any]] = {
    'recipe': {
        'path': '/volume1/docker/recipe',       # NAS 上的实际路径
        'compose_file': 'docker-compose.yml',     # Docker Compose 文件名
        'branch': 'main',                      # 监控的分支
        'description': '食谱系统'                 # 项目描述
    },
    'blog': {
        'path': '/volume1/docker/blog',
        'compose_file': 'docker-compose.yml',
        'branch': 'main',
        'description': '博客系统'
    },
    # 添加更多项目...
}

# Docker 配置
DOCKER_USE_SUDO: bool = False

# 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL: str = 'INFO'
```

### 3. 配置环境变量

编辑 `docker-compose.yml`：

```yaml
environment:
  - WEBHOOK_SECRET=your-strong-password-here  # 修改为强密码
  - WEBHOOK_PORT=5000
  - LOG_LEVEL=INFO
```

生成强密码：

```bash
openssl rand -hex 32
```

### 4. 启动服务

```bash
# 构建并启动
docker-compose up -d --build

# 查看日志
docker logs -f webhook-auto-deploy
```

### 5. 配置内网穿透（推荐 cpolar）

```bash
# 启动 cpolar 隧道
nohup cpolar http 5000 > cpolar.log 2>&1 &

# 查看分配的公网 URL
tail -f cpolar.log
```

### 6. 在 GitHub 设置 Webhook

每个 GitHub 仓库配置：

- **Payload URL**: `https://你的cpolar地址/webhook`
- **Content type**: `application/json`
- **Secret**: 与 WEBHOOK_SECRET 一致
- **Events**: Just the push event

完成！推送代码后会自动部署。

---

## 📚 详细部署指南

### 🎯 架构说明

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

### 🔧 配置选项

#### 环境变量

| 变量 | 说明 | 默认值 | 必填 |
|------|------|--------|------|
| WEBHOOK_SECRET | GitHub Webhook 密钥 | - | 是 |
| WEBHOOK_PORT | 监听端口 | 5000 | 否 |
| LOG_LEVEL | 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL) | INFO | 否 |
| GITHUB_WEBHOOK_SECRET | GitHub Webhook 密钥（别名） | - | 否 |

#### 项目配置

每个项目支持以下配置：

```python
{
    'path': '/path/to/project',           # 项目路径（必填）
    'compose_file': 'docker-compose.yml', # Docker Compose 文件（可选）
    'branch': 'main',                    # 监控的分支（可选）
    'description': '项目描述'             # 项目说明（可选）
}
```

#### 高级配置

**不同分支的部署：**

```python
from typing import Dict, Any

PROJECTS: Dict[str, Dict[str, Any]] = {
    'recipe': {
        'path': '/volume1/docker/recipe',
        'compose_file': 'docker-compose.yml',
        'branch': 'main',  # 监听 main 分支
        'description': '生产环境'
    },
    'recipe-dev': {
        'path': '/volume1/docker/recipe-dev',
        'compose_file': 'docker-compose.yml',
        'branch': 'develop',  # 监听 develop 分支
        'description': '开发环境'
    },
}
```

**需要 sudo 的 Docker：**

```python
# 在 config.py 中设置
DOCKER_USE_SUDO: bool = True
```

或在 `docker-compose.yml` 中设置：

```yaml
environment:
  - DOCKER_USE_SUDO=true
```

### 📡 配置 GitHub Webhooks

#### 方式 1：自动识别（推荐）

每个 GitHub 仓库配置相同的 Webhook URL：

**所有仓库的 Webhook URL：**
```
https://abc123.cpolar.cn/webhook
```

**工作原理：**
- Webhook 服务器根据 GitHub 仓库的 `repository.name` 自动识别项目
- 自动匹配到配置的项目列表

#### 方式 2：指定项目名（可选）

**URL 格式：** `https://abc123.cpolar.cn/webhook/项目名`

示例：
- recipe 项目: `https://abc123.cpolar.cn/webhook/recipe`
- blog 项目: `https://abc123.cpolar.cn/webhook/blog`

### 🧪 测试部署

#### 测试 1：健康检查

```bash
# 检查服务状态
curl http://localhost:5000/health

# 返回示例
{
  "status": "ok",
  "projects": ["recipe", "blog", "api"],
  "timestamp": "Sat Feb 15 12:00:00 CST 2026"
}
```

#### 测试 2：查看项目列表

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

#### 测试 3：手动触发部署

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

### 📊 监控和日志

#### 查看 Webhook 日志

```bash
# 实时监控
docker logs -f webhook-auto-deploy

# 查看最近 100 行
docker logs --tail 100 webhook-auto-deploy

# 带时间戳
docker logs -f webhook-auto-deploy | while read line; do echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line"; done
```

#### 设置日志轮转

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

### 🔒 安全建议

1. **使用强密码**作为 WEBHOOK_SECRET
   ```bash
   openssl rand -hex 32
   ```

2. **限制访问**：使用防火墙或反向代理限制访问

3. **定期更新**：保持 Docker 镜像和依赖更新
   ```bash
   docker-compose pull
   docker-compose up -d --build
   ```

4. **监控日志**：定期检查异常访问
   ```bash
   docker logs -f webhook-auto-deploy
   ```

5. **使用 HTTPS**：生产环境建议使用反向代理（如 Nginx）启用 HTTPS

---

## 📖 API 参考

### 基础信息

- **Base URL**: `http://localhost:5000` 或您的公网域名
- **Content-Type**: `application/json`
- **认证**: HMAC 签名验证（GitHub Webhook 端点）

### 端点列表

#### 1. `/webhook` - 自动识别并部署项目

**方法**: `POST`

**说明**: 接收 GitHub Webhook 请求，自动根据仓库名识别并部署对应项目

**请求头**:
```
Content-Type: application/json
X-Hub-Signature-256: sha256=<signature>
```

**成功响应** (200 OK):
```json
{
  "status": "success",
  "project": "recipe",
  "repository": "recipe",
  "message": "项目 'recipe' 部署成功"
}
```

**错误响应** (403 Forbidden):
```json
{
  "error": "签名验证失败"
}
```

#### 2. `/webhook/<project_name>` - 部署指定项目

**方法**: `POST`

**说明**: 部署指定的项目（不自动识别）

**参数**:
- `project_name` (路径参数): 项目名称，如 `recipe`, `blog`

#### 3. `/health` - 健康检查

**方法**: `GET`

**使用示例**:
```bash
curl http://localhost:5000/health
```

#### 4. `/projects` - 列出所有项目

**方法**: `GET`

**使用示例**:
```bash
curl http://localhost:5000/projects
```

#### 5. `/deploy/<project_name>` - 手动触发部署

**方法**: `POST`

**说明**: 手动触发指定项目的部署（用于测试）

**使用示例**:
```bash
curl -X POST http://localhost:5000/deploy/recipe
```

### 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求格式错误（如无效的 JSON） |
| 403 | 签名验证失败 |
| 404 | 项目不存在 |
| 500 | 服务器内部错误（部署失败） |

### 部署流程

当 Webhook 触发部署时，服务执行以下步骤：

1. **验证签名**: 使用 HMAC-SHA256 验证请求来自 GitHub
2. **识别项目**: 根据 GitHub 仓库名匹配配置的项目
3. **检查分支**: 确认推送的是目标分支（默认 main）
4. **拉取代码**: 执行 `git pull` 更新代码
5. **重启容器**: 执行 `docker-compose down && docker-compose up -d --build`
6. **返回结果**: 返回部署状态

### 示例代码

#### 使用 curl 测试

```bash
# 健康检查
curl http://localhost:5000/health

# 列出项目
curl http://localhost:5000/projects

# 手动部署
curl -X POST http://localhost:5000/deploy/recipe
```

#### 使用 Python

```python
import requests

# 健康检查
response = requests.get('http://localhost:5000/health')
print(response.json())

# 手动部署
response = requests.post('http://localhost:5000/deploy/recipe')
print(response.json())
```

---

## 🐛 故障排查

### 问题：git push 后 NAS 容器没有自动更新

#### 排查步骤

**1️⃣ 检查 webhook 容器是否运行**

```bash
# SSH 到 NAS
ssh admin@your-nas-ip

# 检查容器状态
docker ps | grep webhook

# 查看容器日志（最后 50 行）
docker logs --tail 50 webhook-auto-deploy

# 实时监控日志
docker logs -f webhook-auto-deploy
```

**2️⃣ 测试健康检查**

```bash
curl http://localhost:5000/health

# 应该返回：
# {"status": "ok", "projects": ["recipe", ...], "timestamp": "..."}
```

**3️⃣ 检查项目配置**

```bash
# 查看已配置的项目
curl http://localhost:5000/projects

# 检查项目路径是否存在
ls -la /volume1/docker/recipe
```

**4️⃣ 验证 GitHub Webhook 配置**

**Payload URL**: `https://webhook.vip.cpolar.cn/webhook`
**Content type**: `application/json`
**Secret**: 与 WEBHOOK_SECRET 一致
**Events**: ✅ Just the push event

**5️⃣ 手动触发部署测试**

```bash
# 手动触发 recipe 项目部署
curl -X POST http://localhost:5000/deploy/recipe

# 查看返回结果
```

### 常见问题解决

#### 问题 1：签名验证失败（403）

**症状**：GitHub Webhook 返回 403

**解决方案**：

1. 确保 GitHub Webhook Secret 和 NAS 的 WEBHOOK_SECRET 完全一致
2. 注意区分大小写
3. 检查是否有额外空格或换行符

#### 问题 2：Docker 权限错误

**症状**： "permission denied while trying to connect to the Docker daemon"

**解决方案**：

方法 1 - 在 config.py 中设置：
```python
DOCKER_USE_SUDO: bool = True
```

方法 2 - 在 docker-compose.yml 中设置：
```yaml
environment:
  - DOCKER_USE_SUDO=true
```

方法 3 - 添加用户到 docker 组（推荐）：
```bash
sudo usermod -aG docker $USER
# 需要重启服务
```

#### 问题 3：端口冲突

**症状**： "address already in use"

**解决**：
```bash
# 检查端口占用
netstat -tulpn | grep 5000

# 修改端口
environment:
  - WEBHOOK_PORT=5001

ports:
  - "5001:5001"
```

#### 问题 4：Git pull 失败

**症状**： "Git pull 失败"

**解决**：
1. 检查网络连接
2. 确认 Git 仓库地址正确
3. 检查分支名称是否匹配

### 测试清单

- [ ] **webhook 容器运行中**
- [ ] **健康检查正常**
- [ ] **cpolar 隧道可访问**
- [ ] **项目列表正确**
- [ ] **手动部署成功**
- [ ] **GitHub Webhook 配置正确**
- [ ] **Git 仓库名匹配**
- [ ] **查看日志无错误**

---

## 🛠️ 开发指南

### 前置要求

- Python 3.9+
- [uv](https://github.com/astral-sh/uv) - 快速的 Python 包管理器

### 安装 uv

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 使用 pip
pip install uv
```

### 本地运行

```bash
# 1. 同步依赖
uv sync

# 2. 配置项目
cp config.example.py config.py
nano config.py  # 编辑配置

# 3. 设置环境变量
export WEBHOOK_SECRET=your-test-secret

# 4. 运行服务
uv run python webhook-server.py
```

### 代码质量检查

```bash
# 语法检查
uv run python -m py_compile webhook-server.py

# 类型检查（可选，需要安装 mypy）
uv run mypy webhook-server.py

# 代码格式化（可选，需要安装 black）
uv run black webhook-server.py
```

### 项目结构

```
webhook-auto-deploy/
├── webhook-server.py      # 主服务器文件（包含类型提示）
├── config.py              # 项目配置文件
├── config.example.py      # 配置示例
├── requirements.txt       # Python 依赖
├── docker-compose.yml     # Docker Compose 配置
└── Dockerfile             # Docker 镜像配置
```

### 代码特性

- ✅ **完整的类型提示**：所有函数都有类型注解
- ✅ **TypedDict 配置**：结构化的项目配置类型
- ✅ **辅助函数提取**：消除重复代码
- ✅ **常量管理**：提取魔法值为命名常量
- ✅ **统一响应格式**：标准化的 API 响应
- ✅ **详细文档字符串**：每个函数都有清晰的说明

### 提交代码

欢迎提交 Issue 和 Pull Request！

在提交 PR 前，请确保：

1. ✅ 代码通过语法检查
2. ✅ 添加了必要的类型提示
3. ✅ 更新了相关文档
4. ✅ 测试了新功能

---

## 📦 依赖说明

### 运行时依赖

- **Flask >= 3.0.0** - Web 框架

### 开发依赖（可选）

```bash
# 类型检查
uv add --dev mypy

# 代码格式化
uv add --dev black

# 测试框架
uv add --dev pytest pytest-cov
```

所有类型提示均使用 Python 标准库的 `typing` 模块，无需额外安装类型检查包。

---

## 📄 许可证

MIT License

---

## 🔗 相关项目

- [cpolar](https://www.cpolar.com/) - 内网穿透工具
- [Docker](https://www.docker.com/) - 容器化平台
- [Flask](https://flask.palletsprojects.com/) - Web 框架
- [uv](https://github.com/astral-sh/uv) - Python 包管理器

---

## 📝 更新日志

### [2.0.0] - 2026-02-15

**代码质量提升**:
- ✅ 添加完整的类型提示（TypedDict, Optional, Tuple 等）
- ✅ 重构代码结构，提取辅助函数消除重复
- ✅ 统一响应格式（success_response, error_response, ignored_response）
- ✅ 提取魔法值为命名常量
- ✅ 改进文档字符串，添加详细的 Args/Returns 说明
- ✅ 使用 uv 作为包管理器

**API 变更**:
- API 接口保持向后兼容
- 响应格式保持一致
- 新增类型定义用于更好的 IDE 支持

**文档改进**:
- ✅ 整合所有文档到单一 README.md
- ✅ 添加详细的目录导航
- ✅ 完善部署和故障排查指南
- ✅ 添加开发指南和代码规范

### [1.0.0] - 2026-02-14

- ✅ 初始版本，支持多项目自动部署
- ✅ GitHub Webhook 自动识别
- ✅ Docker Compose 集成
- ✅ HMAC 签名验证

---

**注意**：本项目仅用于个人学习和内部使用，请根据实际需求调整配置。
