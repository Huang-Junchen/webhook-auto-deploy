# GitHub Webhook 自动部署指南

使用 GitHub Webhook + cpolar 实现代码推送后自动更新 NAS。

## 🎯 优势

- 🚀 **实时更新**：git push 后 5 秒内 NAS 自动更新
- 🤖 **完全自动化**：无需人工干预
- 🔒 **安全可靠**：HMAC 签名验证

---

## 📋 设置步骤

### 第一步：在 NAS 上启动 Webhook 服务器

#### 1. 拉取最新代码
```bash
cd /path/to/recipe  # 进入项目目录
git pull origin main
```

#### 2. 修改配置

编辑 `webhook-server.py`：
```bash
nano webhook-server.py
```

修改这两处：
```python
# 第 10 行：改为强密码（任意字符串，但要复杂一些）
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'your-super-secret-password-12345')

# 第 36 行：改为实际的项目路径
PROJECT_DIR = '/volume1/docker/recipe'  # Synology 示例
```

#### 3. 启动 Webhook 服务
```bash
docker-compose -f docker-compose.webhook.yml up -d --build
```

#### 4. 验证服务运行
```bash
# 查看日志
docker logs -f recipe-webhook

# 测试健康检查
curl http://localhost:5000/health
# 应该返回：{"status":"ok"}
```

---

### 第二步：创建 cpolar 隧道

#### 1. SSH 连接到 NAS

#### 2. 启动 cpolar 隧道
```bash
# 前台运行（测试用）
cpolar http 5000

# 或者后台运行（推荐）
nohup cpolar http 5000 > cpolar.log 2>&1 &
```

#### 3. 获取公网 URL

cpolar 会显示类似这样的输出：
```
Tunnel URL          : https://abc123.cpolar.cn
Forwarding          : https://abc123.cpolar.cn -> http://localhost:5000
```

**记下这个 URL**，例如：`https://abc123.cpolar.cn`

---

### 第三步：在 GitHub 配置 Webhook

#### 1. 进入 GitHub 仓库设置
- 打开 https://github.com/Huang-Junchen/recipe
- 点击 **Settings** 标签
- 左侧菜单点击 **Webhooks**
- 点击 **Add webhook**

#### 2. 填写 Webhook 配置

**Payload URL：**
```
https://abc123.cpolar.cn/webhook
```
（替换为你的 cpolar URL）

**Content type：**
```
application/json
```

**Secret：**
```
your-super-secret-password-12345
```
（与 webhook-server.py 中设置的一致）

**Events：**
- ✅ 只勾选 **Just the push event**
- 取消其他事件

#### 3. 点击 **Add webhook**

#### 4. 测试 Webhook

在 Webhook 列表中，找到刚创建的 webhook：
1. 点击 webhook 名称
2. 滚动到 "Recent Deliveries"
3. 点击最新的推送记录
4. 查看响应状态

**成功示例：**
```
Response Status: 200 OK
Response Body:
{
  "status": "success",
  "message": "部署成功！"
}
```

---

## ✅ 测试自动部署

### 测试步骤

1. **在本地修改代码**
```bash
# 修改任意文件
echo "# Test" >> README.md
```

2. **提交并推送**
```bash
git add .
git commit -m "test: 测试自动部署"
git push origin main
```

3. **查看 NAS 日志**
```bash
# 在 NAS 上运行
docker logs -f recipe-webhook
```

**成功输出示例：**
```
[2024-02-14 12:00:00] 收到 GitHub push 事件
[2024-02-14 12:00:01] 拉取代码成功
[2024-02-14 12:00:05] Docker 容器重启成功
```

---

## 🔧 进阶配置

### 1. 设置 cpolar 开机自启动

在 NAS 上创建启动脚本：

**Synology NAS:**
```bash
# 创建任务计划
# 控制面板 -> 任务计划 -> 新增 -> 触发的任务 -> 用户定义的脚本

# 常规：
# 任务：cpolar-webhook
# 用户：root

# 任务设置 -> 用户定义的脚本：
cd /volume1/docker/recipe
nohup cpolar http 5000 > cpolar.log 2>&1 &
```

**其他 NAS:**
编辑 `/etc/crontab`：
```bash
@reboot root cd /path/to/recipe && nohup cpolar http 5000 > cpolar.log 2>&1 &
```

### 2. 设置 Webhook 服务开机自启

Webhook 服务已配置 `restart: unless-stopped`，Docker 启动时会自动运行。

### 3. 限制 GitHub IP（可选）

在 `webhook-server.py` 中添加 IP 白名单：
```python
ALLOWED_IPS = ['192.30.252.0/22', '185.199.108.0/22']  # GitHub IP 段

@app.before_request
def limit_remote_addr():
    if request.remote_addr not in ALLOWED_IPS:
        return jsonify({'error': 'IP not allowed'}), 403
```

---

## 📊 监控和日志

### 查看 Webhook 日志
```bash
# 实时监控
docker logs -f recipe-webhook

# 查看最近 100 行
docker logs --tail 100 recipe-webhook
```

### 查看 cpolar 日志
```bash
# 如果前台运行，直接查看输出

# 如果后台运行
cat cpolar.log
```

### 查看应用日志
```bash
docker-compose logs -f
```

---

## 🐛 故障排查

### 问题 1：GitHub Webhook 显示 "Unknown hook"

**原因：** URL 无法访问或服务未启动

**解决：**
```bash
# 1. 检查 webhook 服务是否运行
docker ps | grep recipe-webhook

# 2. 检查服务日志
docker logs recipe-webhook

# 3. 检查端口是否开放
curl http://localhost:5000/health

# 4. 测试 cpolar 隧道
curl https://abc123.cpolar.cn/health
```

### 问题 2：Webhook 返回 403 Forbidden

**原因：** 签名验证失败

**解决：**
1. 检查 GitHub Webhook Secret 是否与 `WEBHOOK_SECRET` 一致
2. 确保没有额外的空格或换行
3. 重新创建 Webhook

### 问题 3：Docker 容器重启失败

**原因：** Docker 权限问题

**解决：**
```bash
# 将用户添加到 docker 组
sudo usermod -aG docker $USER

# 或者使用 sudo 运行 docker-compose
```

### 问题 4：cpolar 隧道不稳定

**解决：**
1. 升级 cpolar 到付费版（稳定隧道）
2. 或者使用其他内网穿透服务（如 frp、ngrok）

---

## 🔒 安全建议

1. **使用强密码**作为 WEBHOOK_SECRET
   ```bash
   # 生成随机密码
   openssl rand -hex 32
   ```

2. **定期检查日志**，及时发现异常
   ```bash
   # 设置日志监控脚本
   watch -n 60 'docker logs --tail 20 recipe-webhook'
   ```

3. **备份重要数据**
   ```bash
   # 定期备份数据库
   docker-compose exec db pg_dump -U user recipe > backup.sql
   ```

4. **使用 HTTPS**（cpolar 默认提供）

---

## 📚 参考资料

- [GitHub Webhook 文档](https://docs.github.com/en/developers/webhooks-and-events/webhooks)
- [cpolar 官方文档](https://www.cpolar.com/docs)
- [Docker Compose 文档](https://docs.docker.com/compose/)

---

## 🎉 完成！

现在每次推送代码到 GitHub，NAS 都会自动更新并重启容器。

享受自动化带来的便利吧！🚀
