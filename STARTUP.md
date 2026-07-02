# 启动指南

## 环境要求

- Python 3.10+
- Node.js 18+
- pip / npm

---

## 1. 配置环境变量

编辑 `backend/.env`，填入以下配置：

```env
# ✅ 必填 —— 没有这个 AI 分析和摘要功能无法运行
OPENROUTER_API_KEY=sk-or-...

# ⚙️ 必填（如果启用邮件通知）
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com         # Gmail 账号
SMTP_PASS=xxxx xxxx xxxx xxxx          # Gmail 应用专用密码（不是登录密码）
NOTIFICATION_EMAIL=you@example.com     # 接收通知的邮箱

# 🐦 可选 —— Twitter 数据源（当前已停用，保留字段兼容旧配置）
TWITTER_API_KEY=

# 🔔 可选 —— Web Push 浏览器推送（不填则禁用）
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
VAPID_SUBJECT=mailto:you@example.com

# 🔧 通常不需要改
APP_URL=http://127.0.0.1:5173
BACKEND_PORT=8000
MONITOR_INTERVAL_MINUTES=30
```

建议本地开发时前后端统一使用同一种主机名，推荐全部使用 `127.0.0.1`，避免 `localhost` / `127.0.0.1` 混用导致代理或 CORS 判断不一致。

### Gmail 应用专用密码获取方式

1. 打开 Google 账号 → 安全性 → 两步验证（需先开启）
2. 搜索"应用专用密码" → 选择"邮件" → 生成
3. 将生成的 16 位密码填入 `SMTP_PASS`

---

## 2. 启动后端

```bash
cd backend

# 首次运行：安装依赖（建议在虚拟环境中）
pip install -r requirements.txt

# 启动服务（默认端口 8000）
uvicorn app.main:app --reload --port 8000
```

启动成功后会看到：

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Scheduler started
```

数据库文件 `trending_monitor.db` 会自动创建。

---

## 3. 启动前端

新开一个终端窗口：

```bash
cd frontend

# 首次运行：安装依赖
npm install

# 启动开发服务器（默认端口 5173）
npm run dev
```

打开浏览器访问：**http://127.0.0.1:5173**

---

## 4. 功能验收

| 页面 | 验证项 |
|------|--------|
| 热点页 | 空列表正常显示，"触发监控"按钮可点击 |
| 关键词页 | 添加 / 暂停 / 删除关键词 |
| 设置页 | 保存邮箱配置，发送测试邮件 |

添加关键词后，点击"触发监控"可立即测试（无需等待 30 分钟定时任务）。

---

## 5. 功能开关说明

| 功能 | 依赖配置 | 未配置时的行为 |
|------|---------|--------------|
| AI 内容分析 | `OPENROUTER_API_KEY` | 监控任务报错，内容不会被分析 |
| 邮件通知 | `SMTP_*` + 设置页开启 | 发送静默失败，不影响其他功能 |
| Twitter 数据源 | `TWITTER_API_KEY` | 当前已停用，不参与采集 |
| Web Push | `VAPID_*` | 禁用，不影响邮件和应用内通知 |
| Hacker News | 无需配置 | 始终可用 |
| Bing 新闻 | 无需配置 | 始终可用（注意频率限制） |

---

## 6. 常见问题

**后端启动报 `ModuleNotFoundError`**  
→ 确认已激活虚拟环境，或重新执行 `pip install -r requirements.txt`

**前端访问报 `502 Bad Gateway` / API 请求失败**  
→ 确认后端已在 8000 端口运行

**测试邮件发送失败**  
→ 检查 `SMTP_PASS` 是否为应用专用密码（非 Gmail 登录密码）；确认 Gmail 已开启两步验证

**`OPENROUTER_API_KEY` 未填时触发监控**  
→ 后端日志会显示 API 错误，热点列表保持空，属于正常降级行为

**Bing 新闻抓不到内容**  
→ 先确认关键词本身有相关新闻；如果页面结构变动，日志里会看到 Bing 解析错误，后端会返回空列表
