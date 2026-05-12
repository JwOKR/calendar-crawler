"""
定时调度器：用 APScheduler 定时重新抓取所有订阅源
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
from .db import get_all_subscriptions_for_scheduler, update_last_crawled, replace_events
from .crawler import crawl_url

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(daemon=True)


def _crawl_job(sub_id: str, url: str):
    """单个订阅的抓取任务"""
    logger.info(f"定时抓取任务启动: {sub_id} <- {url}")
    try:
        events = crawl_url(url)
        if events:
            replace_events(sub_id, events)
        update_last_crawled(sub_id)
        logger.info(f"定时抓取完成: {sub_id}，获得 {len(events)} 个事件")
    except Exception as e:
        logger.error(f"定时抓取失败 {sub_id}: {e}")


def init_scheduler(app=None):
    """初始化调度器，为数据库中所有订阅注册定时任务"""
    scheduler.start()
    logger.info("调度器已启动")

    subs = get_all_subscriptions_for_scheduler()
    for sub in subs:
        sub_id = sub["id"]
        url = sub["url"]
        hours = sub.get("crawl_interval_hours") or 24
        trigger = IntervalTrigger(hours=hours)
        scheduler.add_job(
            _crawl_job,
            trigger=trigger,
            args=[sub_id, url],
            id=f"crawl_{sub_id}",
            replace_existing=True,
            next_run_time=None,  # 不立即执行，等间隔到了再执行
        )
        logger.info(f"已注册定时任务: {sub_id}，间隔 {hours}h")

    if app:
        @app.on_event("shutdown")
        def _shutdown():
            scheduler.shutdown(wait=False)


def add_job_for_subscription(sub_id: str, url: str, hours: int = 24):
    """为新创建的订阅添加定时任务"""
    trigger = IntervalTrigger(hours=hours)
    scheduler.add_job(
        _crawl_job,
        trigger=trigger,
        args=[sub_id, url],
        id=f"crawl_{sub_id}",
        replace_existing=True,
    )
    logger.info(f"新增定时任务: {sub_id}，间隔 {hours}h")
