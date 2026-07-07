import random
import re
from html import unescape
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

import httpx

from app.config import settings


USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
]

TAG_RE = re.compile(r"<[^>]+>")
BASE_URL = "https://m.weibo.cn/api/container/getIndex"


def _strip_html(value: Optional[str]) -> str:
    if not value:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    text = TAG_RE.sub(" ", text)
    return " ".join(unescape(text).split())


def _build_headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://m.weibo.cn/",
        "User-Agent": random.choice(USER_AGENTS),
        "X-Requested-With": "XMLHttpRequest",
    }
    if settings.weibo_cookie_header:
        headers["Cookie"] = settings.weibo_cookie_header
    return headers


def _build_search_candidates(keyword: str, page: int) -> Sequence[Dict[str, Any]]:
    return [
        {
            "url": BASE_URL,
            "params": {
                "containerid": f"100103type=1&q={keyword}",
                "page_type": "searchall",
                "page": str(page),
            },
        },
        {
            "url": BASE_URL,
            "params": {
                "containerid": f"100103type=1&q={keyword}",
                "page": str(page),
            },
        },
        {
            "url": BASE_URL,
            "params": {
                "type": "wb",
                "q": keyword,
                "page": str(page),
            },
        },
    ]


def _iter_post_dicts(node: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(node, dict):
        mblog = node.get("mblog")
        if isinstance(mblog, dict):
            yield mblog

        has_post_shape = "id" in node and "text" in node and isinstance(node.get("user"), dict)
        if has_post_shape:
            yield node

        for value in node.values():
            yield from _iter_post_dicts(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_post_dicts(value)


def _build_permalink(post_id: str, user_id: Optional[Any], bid: Optional[str]) -> str:
    if user_id and bid:
        return f"https://weibo.com/{user_id}/{bid}"
    if post_id:
        return f"https://m.weibo.cn/detail/{post_id}"
    return ""


def _normalize_post(post: Dict[str, Any]) -> Dict[str, Any]:
    user = post.get("user") or {}
    post_id = str(post.get("id") or post.get("idstr") or "")
    bid = post.get("bid")
    user_id = user.get("id")
    text = _strip_html(post.get("text", ""))

    return {
        "id": post_id,
        "title": text[:280],
        "text": text,
        "summary": text,
        "url": _build_permalink(post_id, user_id, bid),
        "created_at": post.get("created_at") or "",
        "source": "weibo",
        "author_id": str(user_id) if user_id else "",
        "author_name": user.get("screen_name") or "",
        "public_metrics": {
            "reposts_count": post.get("reposts_count"),
            "comments_count": post.get("comments_count"),
            "attitudes_count": post.get("attitudes_count"),
        },
        "raw_data": post,
    }


def _extract_posts(payload: Dict[str, Any], limit: int, seen_ids: Set[str]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    for raw_post in _iter_post_dicts(payload):
        item = _normalize_post(raw_post)
        if not item["id"] or not item["title"] or item["id"] in seen_ids:
            continue
        seen_ids.add(item["id"])
        items.append(item)
        if len(items) >= limit:
            break

    return items


async def _search_page(
    client: httpx.AsyncClient,
    keyword: str,
    page: int,
    remaining: int,
    seen_ids: Set[str],
) -> List[Dict[str, Any]]:
    for candidate in _build_search_candidates(keyword, page):
        try:
            response = await client.get(candidate["url"], params=candidate["params"])
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            print(f"Weibo search request failed for '{keyword}' page {page}: {exc}")
            continue

        items = _extract_posts(payload, remaining, seen_ids)
        if items:
            return items

    return []


async def search_weibo(keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search Weibo mobile JSON endpoints for keyword-related posts."""
    if not settings.weibo_cookie_header:
        print(f"Weibo cookie missing, skip keyword '{keyword}'")
        return []

    max_pages = max(1, min(5, (limit + 9) // 10))
    items: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()

    async with httpx.AsyncClient(timeout=30.0, headers=_build_headers(), follow_redirects=True) as client:
        for page in range(1, max_pages + 1):
            remaining = limit - len(items)
            if remaining <= 0:
                break

            page_items = await _search_page(client, keyword, page, remaining, seen_ids)
            if not page_items:
                if page == 1:
                    print(f"Weibo search returned no posts for '{keyword}' on page 1")
                break
            items.extend(page_items)

    return items
