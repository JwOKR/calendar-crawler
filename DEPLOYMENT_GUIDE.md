# Railway 部署完整指南

## 📋 部署步骤总览

1. ✅ 代码已准备好（本地 Git 仓库已初始化）
2. ⏳ 在 GitHub 上创建仓库
3. ⏳ 推送代码到 GitHub
4. ⏳ 部署到 Railway

---

## 第一步：在 GitHub 上创建仓库

1. 访问 https://github.com/new
2. 填写信息：
   - **Repository name**: `calendar-crawler`
   - **Description**: `Auto crawl websites for calendar events and generate ICS subscription feeds`
   - **Public/Private**: 选择你需要的可见性
   - ⚠️ **不要**勾选 "Initialize this repository with a README"（我们已经有代码了）
3. 点击 "Create repository"
4. 复制仓库地址（类似 `https://github.com/你的用户名/calendar-crawler.git`）

---

## 第二步：推送代码到 GitHub

在本地执行以下命令（替换为你的 GitHub 用户名）：

```bash
# 进入项目目录
cd "C:\Users\HJW55\WorkBuddy\2026-05-12-task-2\calendar-crawler"

# 添加远程仓库（替换为你的仓库地址）
git remote add origin https://github.com/你的用户名/calendar-crawler.git

# 推送代码
git push -u origin master
```

⚠️ **首次推送可能需要输入 GitHub 用户名和密码（或个人访问令牌）**

---

## 第三步：部署到 Railway

1. **注册/登录 Railway**
   - 访问 https://railway.app
   - 使用 GitHub 账号登录

2. **创建新项目**
   - 点击 "New Project"
   - 选择 "Deploy from GitHub repo"
   - 授权 Railway 访问你的 GitHub 账号
   - 选择 `calendar-crawler` 仓库

3. **等待部署完成**
   - Railway 会自动检测 `Dockerfile`
   - 构建过程可能需要 5-10 分钟（需要下载 Playwright 浏览器）
   - 部署完成后会显示 "Deployed Successfully"

4. **获取公网 URL**
   - 在项目详情页，点击 "Settings"
   - 找到 "Domains" 部分
   - Railway 会自动分配一个 `*.railway.app` 的域名
   - 例如：`https://calendar-crawler-production.up.railway.app`

---

## 第四步：测试部署

部署成功后，测试你的服务：

```bash
# 替换为你的实际域名
BASE_URL="https://你的域名.railway.app"

# 1. 健康检查
curl "$BASE_URL/health"

# 2. 创建订阅（替换为实际的日历网页 URL）
curl -X POST "$BASE_URL/subscribe" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/events",
    "name": "测试订阅",
    "crawl_interval_hours": 24
  }'

# 3. 获取 ICS 文件（使用上一步返回的 subscription_id）
curl "$BASE_URL/calendar/{subscription_id}.ics"
```

---

## 🔧 常见问题

### 1. 推送代码时提示 "Authentication failed"
**解决方案**：
- GitHub 已不再支持密码认证
- 需要创建 Personal Access Token (PAT)：
  1. 访问 https://github.com/settings/tokens
  2. 点击 "Generate new token (classic)"
  3. 勾选 `repo` 权限
  4. 复制生成的 token
  5. 推送时密码处粘贴这个 token

### 2. Railway 构建失败（Playwright 相关）
**解决方案**：
- 检查 `Dockerfile` 中是否正确安装了 Playwright 依赖
- 可以尝试简化 `Dockerfile`，先不用 Playwright（只用 HTTP 抓取）

### 3. 数据库不持久化
**原因**：
- Railway 的文件系统是临时性的
- 每次重新部署，`data/` 目录会被重置

**解决方案**（后续优化）：
- 迁移到 PostgreSQL 数据库
- Railway 提供免费的 PostgreSQL 插件

---

## 💰 费用说明

- **免费额度**：$5/月的 credit（足够小型项目使用）
- **超出后**：按使用量计费（约 $0.01/小时）
- **建议**：在项目设置中设置消费上限

---

## 🎉 部署成功后

你可以通过以下方式使用你的日历订阅服务：

1. **在 iOS 上订阅**：
   - 打开 "设置" → "日历" → "账户" → "添加账户" → "其他" → "添加订阅的日历"
   - 输入：`https://你的域名.railway.app/calendar/{subscription_id}.ics`

2. **在 Google Calendar 上订阅**：
   - 打开 Google Calendar
   - 点击 "其他日历" → "通过 URL 添加"
   - 输入 ICS 链接

3. **在 Outlook 上订阅**：
   - 打开 Outlook
   - "添加日历" → "从 Internet"
   - 输入 ICS 链接

---

需要帮助？随时告诉我！
