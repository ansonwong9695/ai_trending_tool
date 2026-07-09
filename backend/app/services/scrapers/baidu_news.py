import re
from html import unescape
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


BAIDU_NEWS_URL = "https://www.baidu.com/s"
BAIDU_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.baidu.com/",
}

LOW_VALUE_HOSTS = {
    "zhidao.baidu.com",
    "tieba.baidu.com",
}
LOW_VALUE_PATHS = {
    "",
    "/",
    "/index.html",
    "/login",
    "/signin",
}
NEWSLIKE_HINTS = (
    "news",
    "article",
    "blog",
    "press",
    "release",
    "announcing",
    "report",
    "快讯",
    "报道",
    "发布",
    "上线",
)
TIME_RE = re.compile(r"\b(\d+\s*(分钟|小时|天|周|月|年)前)\b")


def _clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return " ".join(unescape(value).split())


def _extract_source_name(meta_text: str, url: str) -> str:
    cleaned = _clean_text(meta_text)
    if cleaned:
        cleaned = TIME_RE.sub("", cleaned).strip(" -|/·")
        if cleaned:
            return cleaned.split()[0]

    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host or "Baidu News"


def _extract_published_at(meta_text: str) -> str:
    cleaned = _clean_text(meta_text)
    if not cleaned:
        return ""

    patterns = [
        r"\d+\s*分钟前",
        r"\d+\s*小时前",
        r"\d+\s*天前",
        r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}(?:[日]?\s*\d{1,2}:\d{2})?",
        r"\d{1,2}[-/月]\d{1,2}(?:[日]?\s*\d{1,2}:\d{2})?",
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            return match.group(0)
    return ""


def _score_result(url: str, title: str, snippet: str = "") -> int:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    combined = f"{title.lower()} {snippet.lower()} {path}"
    score = 0

    if host and not host.endswith("baidu.com"):
        score += 3

    if any(hint in combined for hint in NEWSLIKE_HINTS):
        score += 2

    if any(token in path for token in ("/news", "/blog", "/press", "/post", "/article", "/articles")):
        score += 2

    if path in LOW_VALUE_PATHS:
        score -= 3

    return score


def _is_low_value_result(title: str, url: str, snippet: str = "") -> bool:
    if not title or not url:
        return True

    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    combined = f"{title.lower()} {snippet.lower()} {path}"

    if host in LOW_VALUE_HOSTS:
        return True

    if host.endswith("baidu.com") and "baijiahao.baidu.com" not in host:
        return True

    if path in LOW_VALUE_PATHS and not any(hint in combined for hint in NEWSLIKE_HINTS):
        return True

    return False


def _finalize_results(items: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    seen_urls = set()

    for item in items:
        title = _clean_text(item.get("title"))
        url = _clean_text(item.get("url"))
        snippet = _clean_text(item.get("snippet"))
        source_name = _extract_source_name(item.get("source_name", ""), url)

        if not title or not url or url in seen_urls:
            continue
        if _is_low_value_result(title, url, snippet):
            continue

        seen_urls.add(url)
        item["title"] = title
        item["url"] = url
        item["snippet"] = snippet
        item["summary"] = snippet
        item["source_name"] = source_name
        item["source"] = "baidu_news"
        item["_quality_score"] = _score_result(url, title, snippet)
        cleaned.append(item)

    cleaned.sort(key=lambda item: item["_quality_score"], reverse=True)
    for item in cleaned:
        item.pop("_quality_score", None)
    return cleaned[:limit]


def _parse_html(text: str, limit: int) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(text, "html.parser")
    results: List[Dict[str, Any]] = []

    selectors = [
        "div.result",
        "div.result-op",
        "div.c-container",
    ]

    nodes = []
    for selector in selectors:
        nodes = soup.select(selector)
        if nodes:
            break

    for node in nodes:
        title_elem = node.select_one("h3 a, h4 a, a[href]")
        if not title_elem:
            continue

        title = _clean_text(title_elem.get_text(" ", strip=True))
        href = _clean_text(node.get("mu") or title_elem.get("href") or "")
        if not title or not href:
            continue

        snippet_elem = node.select_one(".c-summary, .content-right_8Zs40, .c-span-last p, span[class*='summary']")
        meta_elem = node.select_one(".c-color-gray2, .c-font-normal, span[class*='time'], span[class*='source']")

        results.append(
            {
                "title": title,
                "url": href,
                "snippet": _clean_text(snippet_elem.get_text(" ", strip=True)) if snippet_elem else "",
                "source_name": _clean_text(meta_elem.get_text(" ", strip=True)) if meta_elem else "",
                "published_at": _extract_published_at(meta_elem.get_text(" ", strip=True)) if meta_elem else "",
                "source": "baidu_news",
            }
        )

        if len(results) >= limit * 3:
            break

    return _finalize_results(results, limit)


async def search_baidu_news(keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search Baidu News results for a keyword without requiring an API key."""
    params = {
        "tn": "news",
        "rtt": "4",
        "bsst": "1",
        "cl": "2",
        "wd": keyword,
    }

    async with httpx.AsyncClient(timeout=30.0, headers=BAIDU_HEADERS, follow_redirects=True) as client:
        try:
            response = await client.get(BAIDU_NEWS_URL, params=params)
            response.raise_for_status()
            return _parse_html(response.text, limit)
        except Exception as exc:
            print(f"Baidu News search error for '{keyword}': {repr(exc)}")
            return []
