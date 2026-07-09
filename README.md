# AI Trending Tool

一个面向 AI 编程与内容分享场景的热点监控工具。它会从 Hacker News、GitHub Trending、Bing News、Google News、微博等来源采集内容，通过 OpenRouter 做相关性分析、摘要与趋势聚合，并把高价值信号展示在一个科技感、低干扰的 Vue 控制台里。

当前界面采用深色科技风格：重点突出“第一时间发现热点、快速判断是否值得打开、立即分享有价值内容”，避免复杂操作和过度动效影响使用效率。

## 功能特性

- 热点看板：按时间展示最新热点，支持来源筛选、分页加载、评分和标签展示。
- 原文跳转：卡片和 `Read now` 会优先使用 `url`，再回退到 `primary_url` / `raw_urls[0]`。
- 关键词监控：添加、暂停、删除关键词，针对关键词抓取 Hacker News、Bing News、Google News 和微博搜索结果。
- AI 分析：通过 OpenRouter 批量判断相关性、生成摘要、提取聚合趋势主题。
- 通知能力：支持邮件通知、每日摘要和通知记录查询。
- 定时任务：后端启动后通过 APScheduler 按配置周期自动执行监控任务。
- 本地数据库：默认使用 SQLite，首次启动会自动创建数据表。

## 技术栈

- 前端：Vue 3、Vite、Vue Router、原生 CSS
- UI 风格：Aceternity UI inspired 的 Vue 组件与动效，包括 spotlight、beams、bento card、glow button
- 后端：FastAPI、SQLAlchemy、SQLite、APScheduler
- AI：OpenRouter API
- 爬虫：httpx、BeautifulSoup4
- 通知：aiosmtplib、pywebpush

## 项目结构

```text
ai_trending_tool/
├── backend/
│   └── app/
│       ├── ai/              # OpenRouter AI 调用封装
│       ├── api/             # FastAPI 路由
│       ├── db/              # SQLAlchemy 模型与数据库初始化
│       ├── jobs/            # 定时任务与采集流程
│       └── services/        # 爬虫与通知服务
├── frontend/
│   └── src/
│       ├── components/      # Aceternity 风格组件
│       ├── services/        # 前端 API 封装
│       ├── styles/          # 全局主题样式
│       └── views/           # Dashboard / Keywords / Settings
└── STARTUP.md               # 更详细的本地启动说明
```

## 环境要求

- Python 3.10+
- Node.js 18+
- pip
- npm

## 快速启动

### 1. 配置后端环境变量

在 `backend/.env` 中写入：

```env
OPENROUTER_API_KEY=sk-or-...

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
NOTIFICATION_EMAIL=you@example.com

WEIBO_COOKIE=SUB=...; SUBP=...; SCF=...; ALF=...; SSOLoginState=...; _T_WM=...; MLOGIN=1; WEIBOCN_FROM=...; M_WEIBOCN_PARAMS=...; mweibo_short_token=...; XSRF-TOKEN=...
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
VAPID_SUBJECT=mailto:you@example.com

APP_URL=http://127.0.0.1:5173
BACKEND_PORT=8000
FRONTEND_PORT=5173
MONITOR_INTERVAL_MINUTES=30
```

注意：当前后端配置要求 `OPENROUTER_API_KEY`、`SMTP_USER`、`SMTP_PASS`、`NOTIFICATION_EMAIL` 存在。即使本地暂时不使用邮件，也建议先填入占位值，避免启动时配置校验失败。

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

后端启动后可访问：

- API 根路径：http://127.0.0.1:8000/
- 健康检查：http://127.0.0.1:8000/health
- Swagger 文档：http://127.0.0.1:8000/docs

### 3. 启动前端

新开一个终端：

```bash
cd frontend
npm install
npm run dev
```

访问：http://127.0.0.1:5173

Vite 已配置 `/api` 代理到 `http://127.0.0.1:8000`。

## 使用流程

1. 打开「关键词」页面，添加你关心的 AI、编程、产品或行业关键词。
2. 回到「热点」页面，点击「立即采集」触发关键词监控。
3. 等待 AI 分析完成后刷新列表，查看评分、摘要、标签和来源。
4. 点击卡片标题或 `Read now` 打开原文。
5. 在「设置」页面配置邮件通知、浏览器通知和每日摘要偏好。

## 主要接口

所有后端接口默认带 `/api/v1` 前缀。

```text
GET    /api/v1/trending/                 # 热点列表
GET    /api/v1/trending/{item_id}         # 热点详情
POST   /api/v1/trending/monitor/trigger  # 手动触发关键词监控
POST   /api/v1/trending/collect/trigger  # 手动触发全局热点采集

GET    /api/v1/keywords/                 # 关键词列表
POST   /api/v1/keywords/                 # 创建关键词
PATCH  /api/v1/keywords/{keyword_id}     # 更新关键词状态或来源
DELETE /api/v1/keywords/{keyword_id}     # 删除关键词

GET    /api/v1/settings/                 # 获取用户设置
PATCH  /api/v1/settings/                 # 更新用户设置

GET    /api/v1/notifications/            # 通知记录
POST   /api/v1/notifications/test-email  # 发送测试邮件
POST   /api/v1/notifications/daily-summary # 发送每日摘要
```

## 数据源说明

- Hacker News：免费 API，用于趋势与关键词搜索。
- GitHub Trending：页面爬取，用于全局技术趋势采集。
- Bing News：页面搜索结果爬取，用于关键词新闻监控。
- Google News：RSS 搜索结果抓取，用于补充新闻侧来源。
- 微博：通过 `m.weibo.cn` 的移动端 JSON 搜索接口抓取，必须提供有效的移动端登录 Cookie。

## 开发命令

后端语法检查：

```bash
python3 -m py_compile backend/app/ai/openrouter.py backend/app/api/schemas.py backend/app/db/models.py backend/app/jobs/monitor.py backend/app/services/scrapers/weibo.py
```

前端构建：

```bash
cd frontend
npm run build
```

查看 Git 状态：

```bash
git status --short
```

## 常见问题

### 后端启动时报配置错误

检查 `backend/.env` 是否存在，并确认 `OPENROUTER_API_KEY`、`SMTP_USER`、`SMTP_PASS`、`NOTIFICATION_EMAIL` 都已配置。

### 前端 API 请求失败

确认后端运行在 `8000` 端口，前端运行在 `5173` 端口。建议统一使用 `127.0.0.1`，不要混用 `localhost` 和 `127.0.0.1`。

### 点击卡片无法打开原文

新采集的数据会尽量保留原文链接。旧数据如果入库时没有 `url`、`primary_url` 或 `raw_urls`，前端会显示「原文缺失」，这类历史记录不会自动补齐。

### 邮件发送失败

如果使用 Gmail，需要开启两步验证，并使用 Gmail 应用专用密码作为 `SMTP_PASS`，不能使用普通登录密码。

### AI 分析没有结果

确认 `OPENROUTER_API_KEY` 有效，并检查后端日志中的 OpenRouter 调用错误。AI 失败时，部分采集流程会降级保留原始内容。

## 备注

项目早期设计规范是 warm paper 主题，但当前版本已经切换为更适合 AI 热点监控台的暗色科技风格。后续 UI 修改应优先保证信息密度、阅读效率、原文跳转和采集操作的可用性。
