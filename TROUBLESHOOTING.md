# GitHub Webhook 故障排查指南

## 问题：git push 后 NAS 容器没有自动更新

---

## 排查步骤

### 1️⃣ 检查 webhook 容器是否运行

在 NAS 上执行：

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

**正常情况**：容器状态为 `Up`，日志显示服务启动成功

---

### 2️⃣ 测试 cpolar 隧道是否可访问

```bash
# 测试健康检查端点
curl http://localhost:5000/health

# 应该返回：
# {"status": "ok", "projects": ["recipe", ...], "timestamp": "..."}

# 通过 cpolar 公网访问测试
curl https://webhook.vip.cpolar.cn/health
```

**如果失败**：
- 检查 cpolar 是否正在运行：`ps | grep cpolar`
- 查看隧道状态：`curl http://localhost:9200/api/tunnels`
- 重启 cpolar 隧道

---

### 3️⃣ 检查项目配置

```bash
# 查看已配置的项目
curl http://localhost:5000/projects

# 检查项目路径是否存在
ls -la /volume1/docker/recipe

# 检查项目目录权限
ls -ld /volume1/docker/recipe
```

**如果项目不存在**：
需要编辑 `webhook-server.py`，修改 `PROJECTS` 字典中的路径。

---

### 4️⃣ 验证 GitHub Webhook 配置

#### 4.1 检查 Webhook 是否配置正确

1. 进入 GitHub 仓库：https://github.com/Huang-Junchen/recipe/settings/hooks
2. 找到 webhook 配置
3. 检查以下内容：

**Payload URL**: `https://webhook.vip.cpolar.cn/webhook`
**Content type**: `application/json`
**Secret**: 与 WEBHOOK_SECRET 一致
**Events**: ✅ Just the push event

#### 4.2 测试 Webhook 交付

在 GitHub Webhook 页面：
1. 点击最近一次的交付记录
2. 查看 **Response** 标签页
3. 检查返回状态码和内容

**成功响应** (200 OK):
```json
{
  "status": "success",
  "project": "recipe",
  "message": "项目 'recipe' 部署成功"
}
```

**失败响应** (403 Forbidden):
```json
{
  "error": "签名验证失败"
}
```
→ Secret 密钥不匹配！

**失败响应** (500 Internal Server Error):
```json
{
  "status": "error",
  "message": "..."
}
```
→ 部署失败，查看服务器日志

---

### 5️⃣ 检查签名验证

#### 5.1 在 NAS 上查看 WEBHOOK_SECRET

```bash
# 查看环境变量
docker exec webhook-auto-deploy env | grep WEBHOOK_SECRET

# 或查看 docker-compose 配置
cat docker-compose.yml | grep WEBHOOK_SECRET
```

#### 5.2 重新生成密钥（如需要）

```bash
# 生成随机密钥
openssl rand -hex 32

# 假设生成：abc123def456...
# 记住这个密钥
```

#### 5.3 更新配置

**在 NAS 上**：
```bash
# 编辑 docker-compose.yml
nano docker-compose.yml

# 修改环境变量
environment:
  - WEBHOOK_SECRET=abc123def456...  # 替换为新生成的密钥

# 重启容器
docker-compose -f docker-compose.webhook.yml restart
```

**在 GitHub 上**：
1. 进入 Webhook 设置
2. 点击 webhook 旁边的 "Edit" 按钮
3. 修改 Secret 为新密钥
4. 点击 "Update webhook"

---

### 6️⃣ 手动触发部署测试

在 NAS 上执行：

```bash
# 手动触发 recipe 项目部署
curl -X POST http://localhost:5000/deploy/recipe

# 查看返回结果
```

**如果成功**：
```json
{
  "status": "success",
  "project": "recipe",
  "message": "项目 'recipe' 部署成功"
}
```

**如果失败**：查看错误信息并修复

---

### 7️⃣ 检查 GitHub 仓库匹配

Webhook 服务器根据 GitHub 仓库名自动匹配项目。

#### 7.1 查看仓库实际名称

```bash
# 在项目目录查看远程仓库
cd /volume1/docker/recipe
git remote -v

# 输出示例：
# origin  https://github.com/Huang-Junchen/recipe (fetch)
#                                       ^^^^^^ 仓库名
```

#### 7.2 检查 webhook 配置

编辑 `webhook-server.py` 中的 `PROJECTS` 字典：

```python
PROJECTS = {
    'recipe': {  # 这个名字需要与 GitHub 仓库名匹配
        'path': '/volume1/docker/recipe',
        'compose_file': 'docker-compose.yml',
        'branch': 'main',
        'description': '食谱系统'
    },
}
```

**仓库名匹配规则**：
- GitHub 仓库：`Huang-Junchen/recipe` → 仓库名 `recipe`
- 项目配置：`'recipe'` → 匹配成功
- GitHub 仓库：`Huang-Junchen/my-blog` → 仓库名 `my-blog`
- 项目配置需要添加 `'my-blog'`

---

## 常见问题解决

### 问题 1：容器运行但无法访问

**症状**：`curl http://localhost:5000/health` 无法连接

**解决方案**：

```bash
# 检查端口映射
docker port webhook-auto-deploy

# 应该显示：
# 5000/tcp -> 0.0.0.0:5000

# 如果没有端口映射，检查 docker-compose.yml
# ports:
#   - "5000:5000"

# 重启容器
docker-compose -f docker-compose.webhook.yml restart
```

---

### 问题 2：签名验证失败（403）

**症状**：GitHub Webhook 返回 403

**解决方案**：

1. 确保 GitHub Webhook Secret 和 NAS 的 WEBHOOK_SECRET 完全一致
2. 注意区分大小写
3. 检查是否有额外空格或换行符

```bash
# 测试签名验证
# 在 webhook-server.py 中临时添加调试日志
logger.info(f"Received signature: {signature}")
logger.info(f"Expected signature: {github_signature}")
```

---

### 问题 3：项目部署失败（500）

**症状**：返回 500 错误，日志显示部署失败

**解决方案**：

```bash
# 查看完整错误日志
docker logs --tail 100 webhook-auto-deploy

# 常见错误：
# 1. Git pull 失败 → 检查网络和仓库地址
# 2. Docker 权限不足 → 添加 DOCKER_USE_SUDO=true
# 3. 路径错误 → 检查 PROJECTS 中的路径是否正确
```

---

### 问题 4：cpolar 隧道不稳定

**症状**：有时候能访问，有时候不能

**解决方案**：

1. **升级 cpolar 到付费版**（稳定隧道）
2. **使用其他内网穿透服务**：
   - frp
   - ngrok
   - Cloudflare Tunnel
3. **使用 NAS 的公网 IP**（如果有）

---

### 问题 5：GitHub Webhook 请求未到达

**症状**：GitHub 显示 "We could not deliver this payload"

**可能原因**：
1. cpolar 隧道未运行
2. NAS 防火墙阻止请求
3. WEBHOOK_SECRET 验证失败
4. webhook 服务崩溃

**排查命令**：

```bash
# 1. 检查 cpolar
ps aux | grep cpolar

# 2. 检查 webhook 服务
docker ps | grep webhook

# 3. 查看服务日志
docker logs -f webhook-auto-deploy

# 4. 测试端点
curl -v http://localhost:5000/health
```

---

## 调试模式

### 启用详细日志

编辑 `webhook-server.py`：

```python
# 在文件开头添加
import logging
logging.basicConfig(
    level=logging.DEBUG,  # 改为 DEBUG
    format='[%(asctime)s] %(levelname)s - %(message)s',
)
```

重启容器：

```bash
docker-compose -f docker-compose.webhook.yml restart
```

查看详细日志：

```bash
docker logs -f webhook-auto-deploy
```

---

## 测试清单

使用此清单确认每个环节都正常：

- [ ] **webhook 容器运行中**
  ```bash
  docker ps | grep webhook
  ```

- [ ] **健康检查正常**
  ```bash
  curl http://localhost:5000/health
  ```

- [ ] **cpolar 隧道可访问**
  ```bash
  curl https://webhook.vip.cpolar.cn/health
  ```

- [ ] **项目列表正确**
  ```bash
  curl http://localhost:5000/projects
  ```

- [ ] **手动部署成功**
  ```bash
  curl -X POST http://localhost:5000/deploy/recipe
  ```

- [ ] **GitHub Webhook 配置正确**
  - Payload URL 正确
  - Secret 一致
  - Events 正确

- [ ] **Git 仓库名匹配**
  ```bash
  cd /volume1/docker/recipe
  git remote -v
  ```

- [ ] **查看日志无错误**
  ```bash
  docker logs -f webhook-auto-deploy
  ```

---

## 快速修复脚本

保存为 `fix-webhook.sh` 并运行：

```bash
#!/bin/bash

echo "=== GitHub Webhook 故障修复脚本 ==="

# 1. 检查容器
echo "[1/6] 检查 webhook 容器..."
if docker ps | grep -q webhook; then
    echo "✓ 容器运行中"
else
    echo "✗ 容器未运行，正在启动..."
    docker-compose -f docker-compose.webhook.yml up -d
fi

# 2. 健康检查
echo "[2/6] 健康检查..."
if curl -s http://localhost:5000/health > /dev/null; then
    echo "✓ 服务正常"
else
    echo "✗ 服务异常，请检查日志"
    docker logs --tail 20 webhook-auto-deploy
    exit 1
fi

# 3. 检查项目
echo "[3/6] 检查项目配置..."
curl -s http://localhost:5000/projects | grep recipe
if [ $? -eq 0 ]; then
    echo "✓ 项目配置正确"
else
    echo "✗ 项目配置错误，请检查 webhook-server.py"
fi

# 4. 测试手动部署
echo "[4/6] 测试手动部署..."
read -p "是否测试手动部署？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    curl -X POST http://localhost:5000/deploy/recipe
fi

# 5. 查看日志
echo "[5/6] 查看日志（最近 20 行）..."
docker logs --tail 20 webhook-auto-deploy

# 6. cpolar 状态
echo "[6/6] 检查 cpolar..."
if pgrep -x cpolar > /dev/null; then
    echo "✓ cpolar 运行中"
else
    echo "✗ cpolar 未运行"
fi

echo ""
echo "=== 修复完成 ==="
echo "如果问题仍存在，请查看完整日志："
echo "docker logs -f webhook-auto-deploy"
```

使用方法：

```bash
chmod +x fix-webhook.sh
./fix-webhook.sh
```

---

## 联系支持

如果以上步骤都无法解决问题，请提供以下信息：

1. **webhook 容器日志**：
   ```bash
   docker logs webhook-auto-deploy > webhook.log
   ```

2. **GitHub Webhook 交付记录截图**
   - Response 状态码
   - Response body

3. **系统信息**：
   - NAS 型号和系统版本
   - Docker 版本：`docker --version`
   - cpolar 版本

4. **配置信息**（脱敏后）：
   - docker-compose.yml 配置
   - webhook-server.py 的 PROJECTS 配置
