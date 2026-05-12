"""
FastAPI 主入口：日历抓取 & ICS 订阅源服务
"""
import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import Response
import uvicorn

from .db import (
    init_db,
    create_subscription,
    get_subscription,
    list_subscriptions,
    delete_subscription,
    replace_events,
    get_events_for_ics,
    update_last_crawled,
)
from .crawler import crawl_url
from .ics_writer import events_to_ics
from .scheduler import init_scheduler, add_job_for_subscription
from .models import SubscriptionCreate, SubscriptionResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Calendar Crawler",
    description="自动抓取网页日历/活动信息，生成 ICS 订阅源",
    version="1.0.0",
)

# ── 启动事件 ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    init_db()
    init_scheduler(app)
    logger.info("Calendar Crawler 服务已启动")


# ── 接口 ─────────────────────────────────────────────────────────────────────

@app.post("/subscribe", response_model=SubscriptionResponse)
def subscribe(body: SubscriptionCreate, background_tasks: BackgroundTasks):
    """
    提交一个 URL，创建订阅。
    首次抓取在后台异步执行，完成后可通过 /calendar/{id}.ics 获取 ICS。
    """
    sub_id = create_subscription(
        url=body.url,
        name=body.name,
        crawl_interval_hours=body.crawl_interval_hours,
    )
    # 后台异步抓取
    background_tasks.add_task(_do_crawl, sub_id, body.url)

    # 注册定时任务
    add_job_for_subscription(sub_id, body.url, body.crawl_interval_hours)

    sub = get_subscription(sub_id)
    ev_count = 0  # 首次尚未抓取完成
    return SubscriptionResponse(
        id=sub["id"],
        url=sub["url"],
        name=sub["name"],
        last_crawled=None,
        crawl_interval_hours=sub["crawl_interval_hours"],
        event_count=ev_count,
        created_at=datetime.fromisoformat(sub["created_at"]),
    )


@app.get("/calendar/{sub_id}.ics")
def get_calendar(sub_id: str):
    """
    获取 ICS 订阅文件。
    直接在 iOS / Android / Google Calendar / Outlook 中订阅此 URL。
    """
    sub = get_subscription(sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")

    events = get_events_for_ics(sub_id)
    if not events:
        # 尚未抓取过，先同步抓取一次（或返回空日历）
        crawl_url_result = crawl_url(sub["url"])
        if crawl_url_result:
            replace_events(sub_id, crawl_url_result)
            update_last_crawled(sub_id)
            events = get_events_for_ics(sub_id)

    ics_bytes = events_to_ics(events, calendar_name=sub["name"] or "Calendar")

    return Response(
        content=ics_bytes,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{sub_id}.ics"',
            "Cache-Control": "max-age=3600",
        },
    )


@app.get("/subscriptions")
def get_subscriptions():
    """列出所有订阅及其状态"""
    return list_subscriptions()


@app.post("/refresh/{sub_id}")
def refresh_subscription(sub_id: str):
    """手动触发重新抓取某个订阅"""
    sub = get_subscription(sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")
    events = crawl_url(sub["url"])
    replace_events(sub_id, events)
    update_last_crawled(sub_id)
    return {"status": "ok", "event_count": len(events)}


@app.delete("/subscribe/{sub_id}")
def delete_sub(sub_id: str):
    """删除订阅"""
    sub = get_subscription(sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")
    delete_subscription(sub_id)
    # 移除定时任务
    try:
        from .scheduler import scheduler
        scheduler.remove_job(f"crawl_{sub_id}")
    except Exception:
        pass
    return {"status": "deleted"}


@app.get("/health")
def health():
    return {"status": "ok"}


# ── 内部工具函数 ─────────────────────────────────────────────────────────────

def _do_crawl(sub_id: str, url: str):
    """后台抓取任务"""
    logger.info(f"后台抓取启动: {sub_id} <- {url}")
    try:
        events = crawl_url(url)
        if events:
            replace_events(sub_id, events)
        update_last_crawled(sub_id)
        logger.info(f"后台抓取完成: {sub_id}，获得 {len(events)} 个事件")
    except Exception as e:
        logger.error(f"后台抓取失败 {sub_id}: {e}")


# ── 本地运行入口 ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
