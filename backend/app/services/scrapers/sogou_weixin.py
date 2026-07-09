from html import unescape
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


SOGOU_WEIXIN_URL = "https://weixin.sogou.com/weixin"
SOGOU_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://weixin.sogou.com/",
}

LOW_VALUE_PATH_HINTS = (
    "/weixin",
    "/websearch",
    "/login",
)


def _clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return " ".join(unescape(value).split())


def _extract_source_name(url: str, fallback: str = "") -> str:
    if fallback:
        return _clean_text(fallback)

    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host or "WeChat"


def _extract_published_at(value: str) -> str:
    cleaned = _clean_text(value)
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


def _is_low_value_result(title: str, url: str, snippet: str = "") -> bool:
    if not title or not url:
        return True

    parsed = urlparse(url)
    combined = f"{title.lower()} {snippet.lower()} {parsed.path.lower()}"
    if parsed.netloc.lower().endswith("sogou.com") and not parsed.path.lower().startswith("/link"):
        return True

    if any(hint in parsed.path.lower() for hint in LOW_VALUE_PATH_HINTS):
        return True

    if "免责声明" in combined or "版权归原作者所有" in combined:
        return True

    return False


def _score_result(url: str, title: str, snippet: str = "") -> int:
    parsed = urlparse(url)
    combined = f"{title.lower()} {snippet.lower()} {parsed.path.lower()}"
    score = 0

    if parsed.netloc:
        score += 2

    if len(title) >= 18:
        score += 1

    if any(token in combined for token in ("发布", "观察", "解读", "指南", "分析", "newsletter")):
        score += 2

    return score


def _finalize_results(items: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    seen_urls = set()

    for item in items:
        title = _clean_text(item.get("title"))
        url = _clean_text(item.get("url"))
        snippet = _clean_text(item.get("snippet"))

        if not title or not url or url in seen_urls:
            continue
        if _is_low_value_result(title, url, snippet):
            continue

        seen_urls.add(url)
        item["title"] = title
        item["url"] = url
        item["snippet"] = snippet
        item["summary"] = snippet
        item["source_name"] = _extract_source_name(url, item.get("source_name", ""))
        item["source"] = "sogou_weixin"
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
        "ul.news-list li",
        "div.news-box ul li",
        "li[class*='news-list']",
    ]

    nodes = []
    for selector in selectors:
        nodes = soup.select(selector)
        if nodes:
            break

    for node in nodes:
        title_elem = node.select_one("h3 a, a[href]")
        if not title_elem:
            continue

        href = _clean_text(title_elem.get("href") or "")
        if href.startswith("/"):
            href = urljoin("https://weixin.sogou.com", href)

        title = _clean_text(title_elem.get_text(" ", strip=True))
        if not title or not href:
            continue

        snippet_elem = node.select_one(".txt-info, .s-p, p")
        account_elem = node.select_one(".account, .s-p a, .wx-name, .account-name")
        meta_text = node.get_text(" ", strip=True)

        results.append(
            {
                "title": title,
                "url": href,
                "snippet": _clean_text(snippet_elem.get_text(" ", strip=True)) if snippet_elem else "",
                "source_name": _clean_text(account_elem.get_text(" ", strip=True)) if account_elem else "",
                "published_at": _extract_published_at(meta_text),
                "source": "sogou_weixin",
            }
        )

        if len(results) >= limit * 3:
            break

    return _finalize_results(results, limit)


async def search_sogou_weixin(keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search Sogou Weixin articles for a keyword without requiring an API key."""
    params = {
        "type": "2",
        "query": keyword,
        "ie": "utf8",
    }

    async with httpx.AsyncClient(timeout=30.0, headers=SOGOU_HEADERS, follow_redirects=True) as client:
        try:
            response = await client.get(SOGOU_WEIXIN_URL, params=params)
            response.raise_for_status()
            return _parse_html(response.text, limit)
        except Exception as exc:
            print(f"Sogou Weixin search error for '{keyword}': {repr(exc)}")
            return []
