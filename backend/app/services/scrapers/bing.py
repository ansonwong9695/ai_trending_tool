import asyncio
import re
import xml.etree.ElementTree as ET
from html import unescape
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


BING_NEWS_URL = "https://www.bing.com/news/search"
BING_SEARCH_URL = "https://www.bing.com/search"
BING_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/xml;q=0.8,*/*;q=0.7",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
}
BLOCKED_TITLES = {
    "图片",
    "视频",
    "翻译",
    "地图",
    "学术",
    "images",
    "videos",
    "translate",
    "maps",
    "academic",
}
LOW_VALUE_PATHS = {
    "",
    "/",
    "/learn",
    "/product",
    "/product/overview",
    "/pricing",
    "/login",
    "/signin",
    "/sign-in",
}
NEWSLIKE_HINTS = (
    "news",
    "blog",
    "announcement",
    "announcing",
    "launch",
    "release",
    "update",
    "report",
    "funding",
    "ipo",
    "partnership",
)
REFERENCE_HOST_HINTS = (
    "baike.baidu.com",
    "zhihu.com",
    "wikipedia.org",
)
ARTICLE_PATH_RE = re.compile(r"/20\d{2}/\d{2}/\d{2}/")


def _clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return " ".join(unescape(value).split())


def _extract_source_name(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host.startswith("cn."):
        host = host[3:]
    return host or "Bing"


def _looks_like_xml(text: str, content_type: str = "") -> bool:
    sample = text.lstrip()[:64].lower()
    content_type = (content_type or "").lower()
    return "xml" in content_type or sample.startswith("<?xml") or sample.startswith("<rss")


def _looks_like_bing_landing_page(text: str, final_url: str) -> bool:
    parsed = urlparse(final_url)
    sample = text[:1200].lower()
    return parsed.path in {"", "/"} and (
        "search - microsoft bing" in sample
        or "搜索 - microsoft 必应" in sample
        or "<title>search - microsoft bing</title>" in sample
    )


def _is_low_value_result(title: str, url: str, snippet: str = "") -> bool:
    normalized_title = _clean_text(title).lower()
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    combined = f"{normalized_title} {_clean_text(snippet).lower()} {path}"

    if not normalized_title or not host:
        return True

    if host.endswith("bing.com"):
        return True

    if normalized_title in BLOCKED_TITLES:
        return True

    if "sign in" in normalized_title or "login" in normalized_title:
        return True

    if path in LOW_VALUE_PATHS and not any(hint in combined for hint in NEWSLIKE_HINTS):
        return True

    return False


def _score_result(url: str, title: str, snippet: str = "") -> int:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    combined = f"{title.lower()} {snippet.lower()} {path}"
    score = 0

    if ARTICLE_PATH_RE.search(path):
        score += 4

    if any(hint in combined for hint in NEWSLIKE_HINTS):
        score += 2

    if any(token in path for token in ("/news", "/blog", "/press", "/post", "/article", "/articles")):
        score += 2

    if host.endswith(REFERENCE_HOST_HINTS):
        score -= 2

    if path in LOW_VALUE_PATHS:
        score -= 3

    return score


def _finalize_results(items: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    seen_urls = set()

    for item in items:
        title = _clean_text(item.get("title"))
        url = _clean_text(item.get("url") or item.get("link"))
        snippet = _clean_text(item.get("snippet"))

        if not title or not url or url in seen_urls:
            continue

        if _is_low_value_result(title, url, snippet):
            continue

        seen_urls.add(url)
        item["title"] = title
        item["url"] = url
        item["snippet"] = snippet
        item["source_name"] = _clean_text(item.get("source_name")) or _extract_source_name(url)
        item["source"] = "bing"
        item["_quality_score"] = _score_result(url, title, snippet)
        cleaned.append(item)

    cleaned.sort(key=lambda item: item["_quality_score"], reverse=True)

    for item in cleaned:
        item.pop("_quality_score", None)

    return cleaned[:limit]


def _parse_rss(text: str, limit: int) -> List[Dict[str, Any]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []

    results: List[Dict[str, Any]] = []
    for item in root.findall(".//item"):
        title = _clean_text(item.findtext("title"))
        link = _clean_text(item.findtext("link"))
        snippet = _clean_text(item.findtext("description"))
        source_name = _clean_text(item.findtext("source")) or _extract_source_name(link)
        pub_date = _clean_text(item.findtext("pubDate"))

        if not title:
            continue

        results.append(
            {
                "title": title,
                "url": link,
                "snippet": snippet,
                "source_name": source_name,
                "published_at": pub_date,
                "source": "bing",
            }
        )

        if len(results) >= limit:
            break

    return results


def _parse_html(text: str, limit: int) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(text, "html.parser")
    results: List[Dict[str, Any]] = []

    selectors = [
        "div.news-card",
        "article",
        "div.t_s",
        "li",
    ]

    nodes = []
    for selector in selectors:
        nodes = soup.select(selector)
        if nodes:
            break

    for node in nodes:
        try:
            title_elem = node.select_one("a.title, h2 a, h3 a, a[href]")
            if not title_elem:
                continue

            title = _clean_text(title_elem.get_text(" ", strip=True))
            href = title_elem.get("href", "")
            if not href:
                continue

            if href.startswith("/"):
                href = urljoin("https://www.bing.com", href)

            snippet_elem = node.select_one(".snippet, .sn_txt, p")
            source_elem = node.select_one(".source, .source_name, [class*='source']")

            results.append(
                {
                    "title": title,
                    "url": href,
                    "snippet": _clean_text(snippet_elem.get_text(" ", strip=True)) if snippet_elem else "",
                    "source_name": _clean_text(source_elem.get_text(" ", strip=True)) if source_elem else "Bing",
                    "source": "bing",
                }
            )

            if len(results) >= limit:
                break
        except Exception as e:
            print(f"Error parsing Bing result item: {e}")
            continue

    return results


async def search_bing(keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search Bing for a keyword, preferring Bing News and falling back to RSS search."""
    async with httpx.AsyncClient(
        timeout=30.0,
        headers=BING_HEADERS,
        follow_redirects=True,
    ) as client:
        try:
            await asyncio.sleep(0.5)

            rss_response = await client.get(
                BING_NEWS_URL,
                params={
                    "q": keyword,
                    "count": limit,
                    "format": "rss",
                },
            )
            rss_response.raise_for_status()

            results = []
            if _looks_like_xml(rss_response.text, rss_response.headers.get("content-type", "")):
                results = _parse_rss(rss_response.text, limit)

            results = _finalize_results(results, limit)
            if results:
                return results
        except Exception as e:
            print(f"Bing RSS search error for '{keyword}': {e}")

        try:
            html_response = await client.get(
                BING_NEWS_URL,
                params={
                    "q": keyword,
                    "count": limit,
                },
            )
            html_response.raise_for_status()
            if not _looks_like_bing_landing_page(str(html_response.text), str(html_response.url)):
                results = _finalize_results(_parse_html(html_response.text, limit), limit)
                if results:
                    return results
        except Exception as e:
            print(f"Error searching Bing for '{keyword}': {e}")

        try:
            fallback_response = await client.get(
                BING_SEARCH_URL,
                params={
                    "q": keyword,
                    "count": limit,
                    "format": "rss",
                    "ensearch": "1",
                },
            )
            fallback_response.raise_for_status()

            results = []
            if _looks_like_xml(fallback_response.text, fallback_response.headers.get("content-type", "")):
                results = _parse_rss(fallback_response.text, limit * 2)

            return _finalize_results(results, limit)
        except Exception as e:
            print(f"Bing search fallback error for '{keyword}': {e}")
            return []
