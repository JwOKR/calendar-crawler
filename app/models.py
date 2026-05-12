"""
Pydantic 数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class EventItem(BaseModel):
    """标准化事件数据结构（爬虫输出）"""
    title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None


class SubscriptionCreate(BaseModel):
    """创建订阅请求"""
    url: str
    name: Optional[str] = None
    crawl_interval_hours: int = 24


class SubscriptionResponse(BaseModel):
    """订阅响应"""
    id: str
    url: str
    name: Optional[str]
    last_crawled: Optional[datetime]
    crawl_interval_hours: int
    event_count: int = 0
    created_at: datetime


class CalendarSubscription(BaseModel):
    """订阅数据库模型"""
    id: str
    url: str
    name: Optional[str]
    last_crawled: Optional[datetime]
    crawl_interval_hours: int
    created_at: datetime
