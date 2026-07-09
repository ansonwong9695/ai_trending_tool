import random
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
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
LOW_SIGNAL_PATTERNS = (
    "转发微博",
    "哈哈",
    "哈哈哈",
    "来了",
    "支持",
    "打卡",
    "蹲一个",
    "mark",
)
ACCOUNT_KEYWORD_HINTS = (
    "官方",
    "微博",
    "博主",
    "作者",
    "official",
    "founder",
    "ceo",
    "创始人",
    "研究院",
    "实验室",
    "团队",
    "账号",
)


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


def _build_account_search_candidates(keyword: str, page: int) -> Sequence[Dict[str, Any]]:
    return [
        {
            "url": BASE_URL,
            "params": {
                "containerid": f"100103type=3&q={keyword}",
                "page_type": "searchall",
                "page": str(page),
            },
        },
        {
            "url": BASE_URL,
            "params": {
                "containerid": f"100103type=3&q={keyword}",
                "page": str(page),
            },
        },
        {
            "url": BASE_URL,
            "params": {
                "type": "user",
                "q": keyword,
                "page": str(page),
            },
        },
    ]


def _build_account_timeline_candidates(user_id: str, page: int) -> Sequence[Dict[str, Any]]:
    return [
        {
            "url": BASE_URL,
            "params": {
                "containerid": f"107603{user_id}",
                "page": str(page),
            },
        },
        {
            "url": BASE_URL,
            "params": {
                "type": "uid",
                "value": str(user_id),
                "containerid": f"107603{user_id}",
                "page": str(page),
            },
        },
        {
            "url": BASE_URL,
            "params": {
                "containerid": f"100505{user_id}",
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


def _iter_user_dicts(node: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(node, dict):
        user = node.get("user")
        if isinstance(user, dict) and user.get("screen_name") and user.get("id"):
            yield user

        has_user_shape = node.get("screen_name") and node.get("id")
        has_profile_fields = any(
            key in node for key in ("followers_count", "verified", "profile_url", "statuses_count", "description")
        )
        if has_user_shape and has_profile_fields:
            yield node

        for value in node.values():
            yield from _iter_user_dicts(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_user_dicts(value)


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
        "is_retweet": bool(post.get("retweeted_status")),
        "raw_data": post,
    }


def _contains_cjk(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in value)


def _normalize_account_token(value: str) -> str:
    normalized = (value or "").strip().lower()
    normalized = normalized.lstrip("@")
    normalized = re.sub(r"\s+", "", normalized)
    return normalized


def _looks_like_account_keyword(keyword: str) -> bool:
    normalized = (keyword or "").strip()
    lowered = normalized.lower()
    if normalized.startswith("@"):
        return True
    if any(token in lowered for token in ACCOUNT_KEYWORD_HINTS):
        return True
    if _contains_cjk(normalized) and 2 <= len(normalized) <= 8 and " " not in normalized:
        return True
    return False


def _account_similarity(keyword: str, screen_name: str) -> float:
    left = _normalize_account_token(keyword)
    right = _normalize_account_token(screen_name)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if left in right or right in left:
        return min(len(left), len(right)) / max(len(left), len(right))
    return SequenceMatcher(None, left, right).ratio()


def _normalize_account(user: Dict[str, Any]) -> Dict[str, Any]:
    user_id = str(user.get("id") or user.get("idstr") or "")
    screen_name = _strip_html(user.get("screen_name") or "")
    description = _strip_html(
        user.get("description")
        or user.get("desc1")
        or user.get("remark")
        or user.get("profile_url")
        or ""
    )

    return {
        "id": user_id,
        "screen_name": screen_name,
        "description": description,
        "followers_count": _as_int(user.get("followers_count") or user.get("fansNum")),
        "friends_count": _as_int(user.get("follow_count") or user.get("friends_count")),
        "statuses_count": _as_int(user.get("statuses_count")),
        "verified": bool(user.get("verified")),
        "verified_reason": _strip_html(user.get("verified_reason") or ""),
        "profile_image_url": user.get("profile_image_url") or user.get("avatar_hd") or "",
        "url": f"https://weibo.com/u/{user_id}" if user_id else "",
    }


def _score_account_match(keyword: str, account: Dict[str, Any]) -> float:
    similarity = _account_similarity(keyword, account.get("screen_name", ""))
    score = similarity * 100.0
    if account.get("verified"):
        score += 6.0
    score += min(8.0, account.get("followers_count", 0) / 100000.0)
    return round(score, 1)


def _should_use_account_route(keyword: str, account: Dict[str, Any]) -> bool:
    if not _looks_like_account_keyword(keyword):
        return False

    similarity = _account_similarity(keyword, account.get("screen_name", ""))
    if keyword.strip().startswith("@"):
        return similarity >= 0.7

    if similarity >= 0.92:
        return True

    return bool(account.get("verified")) and similarity >= 0.85


def _build_account_summary(account: Dict[str, Any]) -> str:
    parts = [account.get("description", "").strip()]
    if account.get("verified_reason"):
        parts.append(f"认证: {account['verified_reason']}")

    metrics = []
    if account.get("followers_count"):
        metrics.append(f"粉丝 {account['followers_count']}")
    if account.get("friends_count"):
        metrics.append(f"关注 {account['friends_count']}")
    if account.get("statuses_count"):
        metrics.append(f"博文 {account['statuses_count']}")
    if metrics:
        parts.append("，".join(metrics))

    return " | ".join(part for part in parts if part)


def _build_account_item(account: Dict[str, Any], keyword: str) -> Dict[str, Any]:
    return {
        "id": f"weibo-account-{account['id']}",
        "title": f"{account['screen_name']}（微博账号）",
        "text": account.get("description", ""),
        "summary": _build_account_summary(account),
        "url": account.get("url", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "weibo",
        "entity_type": "account",
        "keyword": keyword,
        "author_id": account.get("id", ""),
        "author_name": account.get("screen_name", ""),
        "public_metrics": {
            "followers_count": account.get("followers_count"),
            "friends_count": account.get("friends_count"),
            "statuses_count": account.get("statuses_count"),
        },
        "quality_score": 30 + min(40, account.get("followers_count", 0) / 5000.0),
        "raw_data": {
            "account": account,
            "entity_type": "account",
        },
    }


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _score_post_quality(item: Dict[str, Any]) -> int:
    metrics = item.get("public_metrics") or {}
    reposts = _as_int(metrics.get("reposts_count"))
    comments = _as_int(metrics.get("comments_count"))
    likes = _as_int(metrics.get("attitudes_count"))
    text = (item.get("text") or "").strip()
    lowered = text.lower()
    score = 0

    score += min(reposts, 20) * 2
    score += min(comments, 20) * 3
    score += min(likes, 50)

    if len(text) >= 60:
        score += 8
    elif len(text) >= 30:
        score += 4
    else:
        score -= 8

    if any(pattern in lowered for pattern in LOW_SIGNAL_PATTERNS):
        score -= 12

    if item.get("is_retweet"):
        score -= 10

    return score


def _is_high_quality_post(item: Dict[str, Any]) -> bool:
    text = (item.get("text") or "").strip()
    if len(text) < 18:
        return False

    quality_score = _score_post_quality(item)
    item["quality_score"] = quality_score

    metrics = item.get("public_metrics") or {}
    reposts = _as_int(metrics.get("reposts_count"))
    comments = _as_int(metrics.get("comments_count"))
    likes = _as_int(metrics.get("attitudes_count"))
    engagement = reposts + comments + likes

    if comments >= 3 or reposts >= 2:
        return quality_score >= 8

    return engagement >= 12 and quality_score >= 15


def _extract_accounts(payload: Dict[str, Any], keyword: str, limit: int) -> List[Dict[str, Any]]:
    accounts: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()

    for raw_user in _iter_user_dicts(payload):
        account = _normalize_account(raw_user)
        if not account["id"] or not account["screen_name"] or account["id"] in seen_ids:
            continue
        account["match_score"] = _score_account_match(keyword, account)
        seen_ids.add(account["id"])
        accounts.append(account)

    accounts.sort(key=lambda item: item.get("match_score", 0.0), reverse=True)
    return accounts[:limit]


def _extract_posts(payload: Dict[str, Any], limit: int, seen_ids: Set[str]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    for raw_post in _iter_post_dicts(payload):
        item = _normalize_post(raw_post)
        if not item["id"] or not item["title"] or item["id"] in seen_ids:
            continue
        if not _is_high_quality_post(item):
            continue
        seen_ids.add(item["id"])
        items.append(item)
        if len(items) >= limit:
            break

    return items


def _dedupe_weibo_items(items: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    deduped: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()
    seen_urls: Set[str] = set()
    seen_titles: Set[str] = set()

    for item in items:
        item_id = str(item.get("id") or "").strip()
        url = str(item.get("url") or "").strip()
        title = _strip_html(item.get("title") or "").strip().lower()

        if item_id and item_id in seen_ids:
            continue
        if url and url in seen_urls:
            continue
        if title and title in seen_titles:
            continue

        if item_id:
            seen_ids.add(item_id)
        if url:
            seen_urls.add(url)
        if title:
            seen_titles.add(title)

        deduped.append(item)
        if len(deduped) >= limit:
            break

    return deduped


async def _search_accounts(
    client: httpx.AsyncClient,
    keyword: str,
    limit: int,
) -> List[Dict[str, Any]]:
    for page in range(1, 3):
        for candidate in _build_account_search_candidates(keyword, page):
            try:
                response = await client.get(candidate["url"], params=candidate["params"])
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                print(f"Weibo account search request failed for '{keyword}' page {page}: {exc}")
                continue

            accounts = _extract_accounts(payload, keyword, limit)
            if accounts:
                return accounts

    return []


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


async def _fetch_account_posts(
    client: httpx.AsyncClient,
    account: Dict[str, Any],
    limit: int,
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()
    max_pages = max(1, min(3, (limit + 4) // 5))

    for page in range(1, max_pages + 1):
        remaining = limit - len(items)
        if remaining <= 0:
            break

        page_items: List[Dict[str, Any]] = []
        for candidate in _build_account_timeline_candidates(account["id"], page):
            try:
                response = await client.get(candidate["url"], params=candidate["params"])
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                print(f"Weibo account timeline request failed for '{account['screen_name']}' page {page}: {exc}")
                continue

            page_items = _extract_posts(payload, remaining, seen_ids)
            if page_items:
                break

        if not page_items:
            break

        for item in page_items:
            item["matched_account"] = account["screen_name"]
            item["entity_type"] = "account_post"
        items.extend(page_items)

    return items


async def search_weibo(keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search Weibo mobile JSON endpoints and merge direct-account matches with keyword discussion results."""
    if not settings.weibo_cookie_header:
        print(f"Weibo cookie missing, skip keyword '{keyword}'")
        return []

    async with httpx.AsyncClient(timeout=30.0, headers=_build_headers(), follow_redirects=True) as client:
        accounts = await _search_accounts(client, keyword, limit=3)
        if accounts and _should_use_account_route(keyword, accounts[0]):
            account = accounts[0]
            account_post_limit = min(4, max(0, limit - 1))
            keyword_limit = min(10, limit)
            posts = await _fetch_account_posts(client, account, account_post_limit)
            account_item = _build_account_item(account, keyword)
            account_item["raw_data"]["recent_posts_count"] = len(posts)
            print(
                f"Weibo keyword '{keyword}' matched account '{account['screen_name']}' "
                f"with score {account.get('match_score', 0)}"
            )
            keyword_items: List[Dict[str, Any]] = []
            seen_ids: Set[str] = set()
            max_pages = max(1, min(5, (keyword_limit + 9) // 10))

            for page in range(1, max_pages + 1):
                remaining = keyword_limit - len(keyword_items)
                if remaining <= 0:
                    break

                page_items = await _search_page(client, keyword, page, remaining, seen_ids)
                if not page_items:
                    if page == 1:
                        print(f"Weibo keyword discussion search returned no posts for '{keyword}' on page 1")
                    break
                keyword_items.extend(page_items)

            return _dedupe_weibo_items([account_item, *posts, *keyword_items], limit)

        max_pages = max(1, min(5, (limit + 9) // 10))
        items: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()

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
