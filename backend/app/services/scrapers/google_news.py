import asyncio
import xml.etree.ElementTree as ET
from html import unescape
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx


GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"
GOOGLE_NEWS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.7",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
}


def _clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return " ".join(unescape(value).split())


def _extract_source_name(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host or "Google News"


def _parse_rss(text: str, limit: int) -> List[Dict[str, Any]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []

    items: List[Dict[str, Any]] = []
    seen_urls = set()

    for item in root.findall(".//item"):
        title = _clean_text(item.findtext("title"))
        link = _clean_text(item.findtext("link"))
        pub_date = _clean_text(item.findtext("pubDate"))
        description = _clean_text(item.findtext("description"))
        source_name = _extract_source_name(link)

        if not title or not link or link in seen_urls:
            continue

        seen_urls.add(link)
        items.append(
            {
                "title": title,
                "url": link,
                "snippet": description,
                "summary": description,
                "published_at": pub_date,
                "source_name": source_name,
                "source": "google_news",
            }
        )

        if len(items) >= limit:
            break

    return items


async def search_google_news(keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search Google News RSS for keyword-related news."""
    params = {
        "q": keyword,
        "hl": "zh-CN",
        "gl": "CN",
        "ceid": "CN:zh-Hans",
    }

    async with httpx.AsyncClient(
        timeout=45.0,
        headers=GOOGLE_NEWS_HEADERS,
        follow_redirects=True,
    ) as client:
        for attempt in range(2):
            try:
                response = await client.get(GOOGLE_NEWS_RSS_URL, params=params)
                response.raise_for_status()
                return _parse_rss(response.text, limit)
            except Exception as exc:
                if attempt == 1:
                    print(f"Google News RSS search error for '{keyword}': {repr(exc)}")
                    return []
                await asyncio.sleep(1.0)

    return []
