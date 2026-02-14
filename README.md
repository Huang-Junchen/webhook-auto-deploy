# GitHub Webhook 自动部署服务

一个通用的 GitHub Webhook 服务器，支持管理 NAS 上多个项目的自动部署。

## ✨ 特性

- 🚀 **实时自动部署**：GitHub 推送后立即更新 NAS 上的项目
- 🎯 **多项目管理**：一个服务管理所有项目，互不干扰
- 🤖 **自动识别**：根据 GitHub 仓库名自动匹配项目
- 🔒 **安全可靠**：HMAC 签名验证，确保请求来自 GitHub
- 📊 **监控友好**：提供 API 端点用于监控和手动触发
- 🐳 **Docker 支持**：开箱即用的 Docker 部署方案

## 📋 适用场景

- NAS 上部署了多个 Docker 项目
- 希望代码推送后自动更新部署
- 需要统一管理多个项目的自动部署

## 🚀 快速开始

### 1. 克隆项目

```bash
cd /volume1/docker  # 或您的项目目录
git clone https://github.com/YOUR_USERNAME/webhook-auto-deploy.git
cd webhook-auto-deploy
```

### 2. 配置项目列表

编辑 `webhook-server.py`，修改 `PROJECTS` 字典：

```python
PROJECTS = {
    'recipe': {
        'path': '/volume1/docker/recipe',
        'compose_file': 'docker-compose.yml',
        'branch': 'main',
        'description': '食谱系统'
    },
    'blog': {
        'path': '/volume1/docker/blog',
        'compose_file': 'docker-compose.yml',
        'branch': 'main',
        'description': '博客系统'
    },
}
```

### 3. 启动服务

```bash
# 修改配置
nano docker-compose.yml
# 修改 WEBHOOK_SECRET 为强密码

# 构建并启动
docker-compose up -d --build

# 查看日志
docker logs -f webhook-auto-deploy
```

### 4. 配置内网穿透（推荐 cpolar）

```bash
# 启动 cpolar 隧道
nohup cpolar http 5000 > cpolar.log 2>&1 &

# 查看分配的公网 URL
tail -f cpolar.log
```

### 5. 在 GitHub 设置 Webhook

每个 GitHub 仓库配置：

- **Payload URL**: `https://你的cpolar地址/webhook`
- **Content type**: `application/json`
- **Secret**: 与 WEBHOOK_SECRET 一致
- **Events**: Just the push event

完成！推送代码后会自动部署。

## 📚 文档

- [完整部署指南](DEPLOYMENT.md) - 详细的部署和配置说明
- [API 参考](API.md) - API 端点文档
- [故障排查](TROUBLESHOOTING.md) - 常见问题解决

## 🔧 配置选项

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| WEBHOOK_SECRET | GitHub Webhook 密钥 | 必填 |
| WEBHOOK_PORT | 监听端口 | 5000 |
| DOCKER_USE_SUDO | Docker 是否需要 sudo | false |

### 项目配置

每个项目支持以下配置：

```python
{
    'path': '/path/to/project',           # 项目路径（必填）
    'compose_file': 'docker-compose.yml', # Docker Compose 文件（可选）
    'branch': 'main',                    # 监控的分支（可选）
    'description': '项目描述'             # 项目说明（可选）
}
```

## 📊 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/webhook` | POST | 自动识别并部署项目 |
| `/webhook/<name>` | POST | 部署指定项目 |
| `/health` | GET | 健康检查 |
| `/projects` | GET | 列出所有项目 |
| `/deploy/<name>` | POST | 手动触发部署 |

详细文档请参考 [API.md](API.md)

## 🐳 Docker 部署

### 使用 Docker Compose（推荐）

```bash
docker-compose up -d --build
```

### 手动运行

```bash
docker build -t webhook-auto-deploy .
docker run -d \
  --name webhook \
  -p 5000:5000 \
  -e WEBHOOK_SECRET=your-secret \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /path/to/projects:/projects:ro \
  webhook-auto-deploy
```

## 🔒 安全建议

1. **使用强密码**作为 WEBHOOK_SECRET
   ```bash
   openssl rand -hex 32
   ```

2. **限制访问**：使用防火墙或反向代理限制访问

3. **定期更新**：保持 Docker 镜像和依赖更新

4. **监控日志**：定期检查异常访问

## 📝 开发

### 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 配置项目
cp webhook-server.py.example webhook-server.py
nano webhook-server.py  # 编辑配置

# 运行服务
python webhook-server.py
```

### 运行测试

```bash
python -m pytest tests/
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🔗 相关项目

- [cpolar](https://www.cpolar.com/) - 内网穿透工具
- [Docker](https://www.docker.com/) - 容器化平台

---

**注意**：本项目仅用于个人学习和内部使用，请根据实际需求调整配置。
