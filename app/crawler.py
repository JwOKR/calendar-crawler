"""
爬虫引擎：抓取网页中的日历/活动信息
优先解析结构化数据（JSON-LD / microdata），兜底使用启发式规则
支持 Playwright 渲染 JS 动态内容
"""
import json
import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
import httpx
from bs4 import BeautifulSoup, Tag
import dateparser

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Calendar-Crawler/1.0"
}


# ─────────────────────────────────────────────
# 日期解析工具
# ─────────────────────────────────────────────

def parse_date(text: str) -> Optional[datetime]:
    """用 dateparser 解析自然语言日期，返回带 UTC 时区的 datetime"""
    if not text:
        return None
    # 去掉多余空白和特殊字符
    text = re.sub(r"\s+", " ", text.strip())
    try:
        dt = dateparser.parse(
            text,
            settings={
                "TIMEZONE": "UTC",
                "RETURN_AS_TIMEZONE_AWARE": True,
                "PREFER_DATES_FROM": "future",
            }
        )
        if dt:
            # 确保时区为 UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
    except Exception:
        pass
    return None


def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


# ─────────────────────────────────────────────
# 结构化数据解析（JSON-LD / microdata）
# ─────────────────────────────────────────────

def _extract_json_ld(soup: BeautifulSoup) -> List[Dict]:
    """从 <script type="application/ld+json"> 提取 Event 数据"""
    events: List[Dict] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        # 可能是列表或单个对象
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            # 递归查找 @type=Event
            found = _find_events_in_jsonld(item)
            events.extend(found)
    return events


def _find_events_in_jsonld(obj) -> List[Dict]:
    """递归在 JSON-LD 对象中查找 Schema.org Event"""
    results = []
    if isinstance(obj, dict):
        if obj.get("@type") in ("Event", "SportsEvent", "TheaterEvent", "Festival"):
            ev = _jsonld_to_event(obj)
            if ev:
                results.append(ev)
        for v in obj.values():
            results.extend(_find_events_in_jsonld(v))
    elif isinstance(obj, list):
        for v in obj:
            results.extend(_find_events_in_jsonld(v))
    return results


def _jsonld_to_event(item: dict) -> Optional[Dict]:
    title = item.get("name") or item.get("headline", "")
    if not title:
        return None
    start = parse_date(item.get("startDate") or "")
    if not start:
        return None
    end = parse_date(item.get("endDate"))
    location = ""
    loc = item.get("location")
    if isinstance(loc, dict):
        location = loc.get("name", "")
    elif isinstance(loc, str):
        location = loc
    description = item.get("description", "")
    return {
        "title": title,
        "start_time": iso(start),
        "end_time": iso(end),
        "location": location,
        "description": description,
        "uid": item.get("@id", ""),
    }


def _extract_microdata(soup: BeautifulSoup) -> List[Dict]:
    """从 microdata / Open Graph 协议提取事件"""
    events: List[Dict] = []
    # Open Graph：og:type=article/event 等
    og_type = _get_meta(soup, "og:type")
    if og_type and "event" in og_type.lower():
        ev = _parse_og_event(soup)
        if ev:
            events.append(ev)
    # 简单 microdata：itemscope + itemtype=Event
    for el in soup.find_all(attrs={"itemtype": True}):
        typ = el.get("itemtype", "")
        if "Event" in typ:
            ev = _parse_microdata_event(el)
            if ev:
                events.append(ev)
    return events


def _get_meta(soup: BeautifulSoup, prop: str) -> str:
    tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
    return tag.get("content", "") if tag else ""


def _parse_og_event(soup: BeautifulSoup) -> Optional[Dict]:
    title = _get_meta(soup, "og:title") or soup.title.string if soup.title else ""
    start = parse_date(_get_meta(soup, "og:event:start_time") or _get_meta(soup, "article:published_time"))
    if not start:
        return None
    return {
        "title": title,
        "start_time": iso(start),
        "end_time": None,
        "location": _get_meta(soup, "og:event:location"),
        "description": _get_meta(soup, "og:description"),
        "uid": "",
    }


def _parse_microdata_event(el: Tag) -> Optional[Dict]:
    title = _find_itemprop(el, "name") or el.get_text()[:80]
    start_str = _find_itemprop(el, "startDate")
    start = parse_date(start_str)
    if not start:
        return None
    return {
        "title": title,
        "start_time": iso(start),
        "end_time": iso(parse_date(_find_itemprop(el, "endDate"))),
        "location": _find_itemprop(el, "location"),
        "description": _find_itemprop(el, "description"),
        "uid": "",
    }


def _find_itemprop(parent: Tag, prop: str) -> str:
    tag = parent.find(attrs={"itemprop": prop})
    if tag:
        return tag.get("content") or tag.get_text(strip=True)
    return ""


# ─────────────────────────────────────────────
# 启发式解析（兜底）
# ─────────────────────────────────────────────

# 常见日期格式正则
DATE_PATTERNS = [
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?",  # ISO 8601
    r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",                  # 2025-01-15 / 2025年01月15日
    r"\d{1,2}[-/月]\d{1,2}日?\s*\d{1,2}:\d{2}",            # 01-15 14:00 / 1月15日 14:00
    r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s*,?\s+\w+\s+\d{1,2}", # English
]
DATE_RE = re.compile("|".join(DATE_PATTERNS), re.IGNORECASE)


def _heuristic_extract(soup: BeautifulSoup, page_url: str) -> List[Dict]:
    """启发式：查找日期字符串 + 相邻文本作为标题"""
    events: List[Dict] = []
    seen_texts = set()

    # 优先查找 <time> 标签（常见静态事件页写法）
    for time_tag in soup.find_all("time"):
        dt_attr = time_tag.get("datetime") or time_tag.get_text(strip=True)
        dt = parse_date(dt_attr)
        if not dt:
            continue
        # 向上找最近的包含标题的父容器
        container = time_tag.find_parent(class_=re.compile("event|item|card|entry", re.I)) or time_tag.parent
        title_el = container and (container.find(["h1","h2","h3","h4"]) or container.find(class_=re.compile("title|name", re.I)))
        title = title_el.get_text(strip=True) if title_el else (time_tag.parent.get_text(" ", strip=True)[:80] if time_tag.parent else "")[:80]
        if not title or title in seen_texts:
            continue
        seen_texts.add(title)
        loc_el = container and container.find(class_=re.compile("location|venue|place", re.I))
        desc_el = container and container.find(class_=re.compile("desc|content|summary", re.I))
        events.append({
            "title": title,
            "start_time": iso(dt),
            "end_time": None,
            "location": loc_el.get_text(strip=True) if loc_el else "",
            "description": desc_el.get_text(strip=True) if desc_el else "",
            "uid": "",
        })

    if events:
        return events

    # 优先查找常见事件容器选择器
    containers = soup.select(
        ".event, .events, .calendar-item, .calendar-event, "
        "[class*='event'], [class*='calendar-item'], [class*='schedule']"
    )
    for el in containers:
        ev = _parse_container_event(el)
        if ev and ev["title"] not in seen_texts:
            seen_texts.add(ev["title"])
            events.append(ev)

    if events:
        return events

    # 更激进：全文扫描日期字符串
    text = soup.get_text(separator=" ", strip=True)
    for m in DATE_RE.finditer(text):
        date_str = m.group()
        dt = parse_date(date_str)
        if not dt:
            continue
        # 取日期前后 100 字符作为候选标题
        start = max(0, m.start() - 80)
        end = min(len(text), m.end() + 80)
        snippet = text[start:end].strip()
        # 取第一行非空作为标题
        title = next((l.strip() for l in snippet.split("\n") if l.strip()), "")[:100]
        if title and title not in seen_texts:
            seen_texts.add(title)
            events.append({
                "title": title,
                "start_time": iso(dt),
                "end_time": None,
                "location": "",
                "description": snippet,
                "uid": "",
            })
    return events


def _parse_container_event(el: Tag) -> Optional[Dict]:
    text = el.get_text(" ", strip=True)
    # 在容器内找日期
    m = DATE_RE.search(text)
    if not m:
        return None
    dt = parse_date(m.group())
    if not dt:
        return None
    # 标题：优先找标题标签
    title_el = el.find(["h1", "h2", "h3", "h4"]) or el.find(class_=re.compile("title|name", re.I))
    title = title_el.get_text(strip=True) if title_el else text[:80]
    # 地点
    loc_el = el.find(class_=re.compile("location|venue|place", re.I))
    location = loc_el.get_text(strip=True) if loc_el else ""
    desc_el = el.find(class_=re.compile("desc|content|summary", re.I))
    description = desc_el.get_text(strip=True) if desc_el else ""
    return {
        "title": title,
        "start_time": iso(dt),
        "end_time": None,
        "location": location,
        "description": description,
        "uid": "",
    }


# ─────────────────────────────────────────────
# Playwright 渲染（JS 动态内容兜底）
# ─────────────────────────────────────────────

def _fetch_with_playwright(url: str) -> str:
    """用 Playwright 渲染页面，返回最终 HTML"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=HEADERS["User-Agent"])
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            # 等待可能的动态内容加载
            page.wait_for_timeout(3000)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        logger.warning(f"Playwright 渲染失败: {e}")
        return ""


# ─────────────────────────────────────────────
# 公开接口
# ─────────────────────────────────────────────

def crawl_url(url: str) -> List[Dict]:
    """
    抓取给定 URL，返回标准化事件列表。
    优先静态抓取，若无结果且未禁用，则用 Playwright 渲染。
    """
    logger.info(f"开始抓取: {url}")

    # 1. 静态 HTTP 抓取
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        logger.warning(f"HTTP 抓取失败: {e}，尝试 Playwright")
        html = _fetch_with_playwright(url)
        if not html:
            return []

    soup = BeautifulSoup(html, "lxml")

    # 2. 所有解析方法都执行，结果合并去重
    events: List[Dict] = []
    seen_titles = set()

    for extractor in (_extract_json_ld, _extract_microdata):
        for ev in extractor(soup):
            title = ev.get("title", "")
            if title and title not in seen_titles:
                seen_titles.add(title)
                events.append(ev)

    # 启发式解析
    for ev in _heuristic_extract(soup, url):
        title = ev.get("title", "")
        if title and title not in seen_titles:
            seen_titles.add(title)
            events.append(ev)

    # 3. 若仍无结果，尝试 Playwright 渲染
    if not events:
        logger.info("静态解析无结果，尝试 Playwright 渲染...")
        html2 = _fetch_with_playwright(url)
        if html2:
            soup2 = BeautifulSoup(html2, "lxml")
            # 所有解析方法都执行，结果合并去重
            for extractor in (_extract_json_ld, _extract_microdata):
                for ev in extractor(soup2):
                    title = ev.get("title", "")
                    if title and title not in seen_titles:
                        seen_titles.add(title)
                        events.append(ev)
            for ev in _heuristic_extract(soup2, url):
                title = ev.get("title", "")
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    events.append(ev)

    # 补全 uid
    for ev in events:
        if not ev.get("uid"):
            ev["uid"] = f"{url}#{ev['title']}#{ev['start_time']}"

    logger.info(f"抓取完成: {url}，获得 {len(events)} 个事件")
    return events
