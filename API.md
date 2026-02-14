# API 参考文档

本文档描述 GitHub Webhook 自动部署服务的 API 端点。

## 基础信息

- **Base URL**: `http://localhost:5000` 或您的公网域名
- **Content-Type**: `application/json`
- **认证**: HMAC 签名验证（GitHub Webhook 端点）

---

## 端点列表

### 1. `/webhook` - 自动识别并部署项目

**方法**: `POST`

**说明**: 接收 GitHub Webhook 请求，自动根据仓库名识别并部署对应项目

**请求头**:
```
Content-Type: application/json
X-Hub-Signature-256: sha256=<signature>
```

**请求体**: GitHub Webhook Payload (JSON)

**成功响应** (200 OK):
```json
{
  "status": "success",
  "project": "recipe",
  "repository": "recipe",
  "message": "项目 'recipe' 部署成功"
}
```

**忽略响应** (200 OK):
```json
{
  "status": "ignored",
  "message": "忽略分支 refs/heads/develop，只部署 refs/heads/main"
}
```

**错误响应** (403 Forbidden):
```json
{
  "error": "签名验证失败"
}
```

**错误响应** (500 Internal Server Error):
```json
{
  "status": "error",
  "project": "recipe",
  "message": "Git pull 失败: ..."
}
```

---

### 2. `/webhook/<project_name>` - 部署指定项目

**方法**: `POST`

**说明**: 部署指定的项目（不自动识别）

**参数**:
- `project_name` (路径参数): 项目名称，如 `recipe`, `blog`

**请求头**:
```
Content-Type: application/json
X-Hub-Signature-256: sha256=<signature>
```

**请求体**: GitHub Webhook Payload (JSON)

**成功响应** (200 OK):
```json
{
  "status": "success",
  "project": "recipe",
  "message": "项目 'recipe' 部署成功"
}
```

**错误响应** (404 Not Found):
```json
{
  "status": "error",
  "message": "项目 'unknown' 未配置"
}
```

---

### 3. `/health` - 健康检查

**方法**: `GET`

**说明**: 检查服务运行状态

**成功响应** (200 OK):
```json
{
  "status": "ok",
  "projects": ["recipe", "blog", "api"],
  "timestamp": "Sat Feb 14 12:00:00 CST 2026"
}
```

**使用示例**:
```bash
curl http://localhost:5000/health
```

---

### 4. `/projects` - 列出所有项目

**方法**: `GET`

**说明**: 获取所有已配置的项目列表

**成功响应** (200 OK):
```json
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
    {
      "name": "blog",
      "description": "博客系统",
      "path": "/volume1/docker/blog",
      "branch": "main",
      "compose_file": "docker-compose.yml"
    },
    {
      "name": "api",
      "description": "API 服务",
      "path": "/volume1/docker/api",
      "branch": "main",
      "compose_file": "docker-compose.prod.yml"
    }
  ]
}
```

**使用示例**:
```bash
curl http://localhost:5000/projects
```

---

### 5. `/deploy/<project_name>` - 手动触发部署

**方法**: `POST`

**说明**: 手动触发指定项目的部署（用于测试）

**参数**:
- `project_name` (路径参数): 项目名称

**成功响应** (200 OK):
```json
{
  "status": "success",
  "project": "recipe",
  "message": "项目 'recipe' 部署成功"
}
```

**错误响应** (404 Not Found):
```json
{
  "status": "error",
  "project": "unknown",
  "message": "项目 'unknown' 未配置"
}
```

**使用示例**:
```bash
# 部署 recipe 项目
curl -X POST http://localhost:5000/deploy/recipe

# 部署 blog 项目
curl -X POST http://localhost:5000/deploy/blog
```

---

## 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求格式错误（如无效的 JSON） |
| 403 | 签名验证失败 |
| 404 | 项目不存在 |
| 500 | 服务器内部错误（部署失败） |

---

## 部署流程

当 Webhook 触发部署时，服务执行以下步骤：

1. **验证签名**: 使用 HMAC-SHA256 验证请求来自 GitHub
2. **识别项目**: 根据 GitHub 仓库名匹配配置的项目
3. **检查分支**: 确认推送的是目标分支（默认 main）
4. **拉取代码**: 执行 `git pull` 更新代码
5. **重启容器**: 执行 `docker-compose down && docker-compose up -d --build`
6. **返回结果**: 返回部署状态

---

## GitHub Webhook 配置

### 必需的请求头

- `X-Hub-Signature-256`: HMAC 签名（用于验证）
- `Content-Type`: 必须是 `application/json`

### GitHub Payload 结构

服务主要使用以下字段：

```json
{
  "ref": "refs/heads/main",
  "repository": {
    "name": "recipe",
    "full_name": "username/recipe"
  },
  "pusher": {
    "name": "username"
  }
}
```

---

## 安全说明

### 签名验证

所有 POST 请求到 `/webhook` 和 `/webhook/<name>` 的端点都需要通过 HMAC-SHA256 签名验证。

签名计算方式：
```python
import hmac
import hashlib

signature = hmac.new(
    SECRET.encode(),
    msg=request.data,
    digestmod=hashlib.sha256
).hexdigest()
```

### 环境变量

通过环境变量配置安全密钥：

```bash
WEBHOOK_SECRET=your-random-32-char-secret
```

生成强密钥：
```bash
openssl rand -hex 32
```

---

## 错误处理

### 常见错误

1. **签名验证失败 (403)**
   - 原因: WEBHOOK_SECRET 不匹配
   - 解决: 检查 GitHub Webhook 配置中的 Secret

2. **项目不存在 (404)**
   - 原因: 项目名未在 PROJECTS 字典中配置
   - 解决: 在 webhook-server.py 中添加项目配置

3. **部署失败 (500)**
   - 原因: Git 或 Docker 命令失败
   - 解决: 查看服务器日志，检查项目路径和权限

---

## 示例代码

### 使用 curl 测试

```bash
# 健康检查
curl http://localhost:5000/health

# 列出项目
curl http://localhost:5000/projects

# 手动部署
curl -X POST http://localhost:5000/deploy/recipe
```

### 使用 Python

```python
import requests

# 健康检查
response = requests.get('http://localhost:5000/health')
print(response.json())

# 列出项目
response = requests.get('http://localhost:5000/projects')
print(response.json())

# 手动部署
response = requests.post('http://localhost:5000/deploy/recipe')
print(response.json())
```

### 使用 JavaScript (fetch)

```javascript
// 健康检查
fetch('http://localhost:5000/health')
  .then(res => res.json())
  .then(data => console.log(data));

// 列出项目
fetch('http://localhost:5000/projects')
  .then(res => res.json())
  .then(data => console.log(data));

// 手动部署
fetch('http://localhost:5000/deploy/recipe', { method: 'POST' })
  .then(res => res.json())
  .then(data => console.log(data));
```

---

## 版本历史

- **v1.0** - 初始版本，支持多项目自动部署
