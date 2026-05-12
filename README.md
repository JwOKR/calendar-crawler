# Calendar Crawler — 自动抓取网页日历生成 ICS 订阅源

## 快速启动

```bash
cd calendar-crawler
./venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/subscribe` | POST | 提交 URL 创建订阅，返回 `{id, url, name, ...}` |
| `/calendar/{id}.ics` | GET | 获取 ICS 订阅文件（可直接导入 iOS/Android/Outlook/Google Calendar） |
| `/subscriptions` | GET | 列出所有订阅及状态 |
| `/refresh/{id}` | POST | 手动触发重新抓取 |
| `/subscribe/{id}` | DELETE | 删除订阅 |

## 创建订阅示例

```powershell
$body = @{ url = "https://example.com/events"; name = "My Events" } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/subscribe -Method Post -Body $body -ContentType "application/json"
```

返回示例：
```json
{
  "id": "874025d397aa",
  "url": "https://example.com/events",
  "name": "My Events",
  "last_crawled": null,
  "crawl_interval_hours": 24,
  "event_count": 0,
  "created_at": "2026-05-12T15:32:57.968097Z"
}
```

## 订阅到日历应用

用返回的 `id` 拼接 ICS 链接，直接在任何日历应用中订阅：

```
http://你的服务器IP:8000/calendar/874025d397aa.ics
```

- **iOS**：设置 → 日历 → 账户 → 添加账户 → 其他 → 订阅日历 → 输入 URL
- **Google Calendar**：左侧「其他日历」→ + → 通过 URL 添加 → 粘贴 URL
- **Outlook**：打开 ICS 文件自动导入

## 定时更新

每个订阅创建时会自动注册定时任务，默认每 24 小时重新抓取一次。
可在 `POST /subscribe` 时通过 `crawl_interval_hours` 字段自定义间隔。

## 爬虫说明

抓取优先级：
1. **JSON-LD** 结构化数据（`application/ld+json`）
2. **Microdata / Open Graph** 协议
3. **`<time>` 标签 + 启发式容器识别**
4. **Playwright JS 渲染兜底**（当以上均无结果时自动启用）

## 项目结构

```
calendar-crawler/
├── app/
│   ├── main.py          # FastAPI 入口
│   ├── crawler.py       # 爬虫引擎（静态+JS渲染）
│   ├── ics_writer.py   # ICS 文件生成
│   ├── db.py           # SQLite 操作
│   ├── scheduler.py    # APScheduler 定时任务
│   └── models.py       # Pydantic 数据模型
├── data/               # SQLite 数据库文件
├── venv/               # Python 虚拟环境
└── pyproject.toml     # 依赖声明
```
