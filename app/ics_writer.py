"""
ICS 生成器：将事件列表写入标准 iCalendar (.ics) 文件内容
使用 icalendar 库，符合 RFC 5545 标准
"""
from icalendar import Calendar, Event
from datetime import datetime
from typing import List, Dict
import uuid


def events_to_ics(events: List[Dict], calendar_name: str = "Calendar Crawler") -> bytes:
    """
    将事件列表转换为 ICS 文件二进制内容
    events: List[Dict]，每个 Dict 包含：
        title, start_time (ISO 8601), end_time, location, description, uid
    """
    cal = Calendar()
    cal.add("prodid", "-//CalendarCrawler//calendar-crawler 1.0//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", calendar_name)

    for ev in events:
        event = Event()
        uid = ev.get("uid") or str(uuid.uuid4())
        event.add("uid", uid)

        title = ev.get("title", "Untitled Event")
        event.add("summary", title)

        start_raw = ev.get("start_time")
        if start_raw:
            dt_start = _parse_iso(start_raw)
            if dt_start:
                event.add("dtstart", dt_start)

        end_raw = ev.get("end_time")
        if end_raw:
            dt_end = _parse_iso(end_raw)
            if dt_end:
                event.add("dtend", dt_end)
        elif dt_start:
            # 无结束时间，默认 1 小时
            from datetime import timedelta
            event.add("dtend", dt_start + timedelta(hours=1))

        if ev.get("location"):
            event.add("location", ev["location"])

        if ev.get("description"):
            event.add("description", ev["description"])

        event.add("dtstamp", datetime.utcnow())

        cal.add_component(event)

    return cal.to_ical()


def _parse_iso(val):
    """接受 ISO 8601 字符串或 datetime 对象，返回 datetime"""
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            # 尝试解析带时区和不带时区的格式
            from dateutil.parser import isoparse
            return isoparse(val)
        except Exception:
            return None
    return None
