import asyncio
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import List, Dict, Any
from sqlalchemy import select

from app.db.database import async_session_maker
from app.db.models import Keyword, TrendingItem
from app.ai.openrouter import analyze_relevance_batch
from app.services.scrapers.hackernews import fetch_hn_trending, search_hn_by_keyword
from app.services.scrapers.github import fetch_github_trending
from app.services.scrapers.bing import search_bing
from app.services.scrapers.google_news import search_google_news
from app.services.scrapers.baidu_news import search_baidu_news
from app.services.scrapers.sogou_weixin import search_sogou_weixin
from app.services.scrapers.weibo import search_weibo


DEFAULT_KEYWORD_SOURCES = ["hackernews", "bing", "google_news", "baidu_news", "sogou_weixin", "weibo"]
TRENDING_NEWS_QUERY = '"AI" OR "LLM" OR "agent" OR "OpenAI" OR "Anthropic" OR "Gemini"'
LEGACY_DEFAULT_KEYWORD_SOURCES = {"hackernews", "bing", "google_news", "weibo"}
CHINA_TZ = timezone(timedelta(hours=8))
RECENCY_WINDOWS_HOURS = {
    "weibo": 168,
    "hackernews": 168,
    "bing": 168,
    "google_news": 168,
    "baidu_news": 168,
    "sogou_weixin": 168,
}
ALWAYS_FRESH_SOURCES = {"github"}
STRICT_RECENCY_SOURCES = {"weibo", "hackernews", "bing", "google_news", "baidu_news", "sogou_weixin"}
CN_RELATIVE_PATTERNS = (
    (re.compile(r"(\d+)\s*分钟前"), "minutes"),
    (re.compile(r"(\d+)\s*小时前"), "hours"),
    (re.compile(r"(\d+)\s*天前"), "days"),
    (re.compile(r"(\d+)\s*周前"), "weeks"),
)
EN_RELATIVE_PATTERNS = (
    (re.compile(r"(\d+)\s*minutes?\s*ago", re.IGNORECASE), "minutes"),
    (re.compile(r"(\d+)\s*hours?\s*ago", re.IGNORECASE), "hours"),
    (re.compile(r"(\d+)\s*days?\s*ago", re.IGNORECASE), "days"),
)


def _normalize_sources(sources: List[str]) -> set:
    normalized = set(sources)
    if "nitter" in normalized:
        normalized.discard("nitter")
        normalized.add("weibo")
    if "google" in normalized:
        normalized.discard("google")
        normalized.add("google_news")
    if "baidu" in normalized:
        normalized.discard("baidu")
        normalized.add("baidu_news")
    if "sogou" in normalized or "weixin" in normalized:
        normalized.discard("sogou")
        normalized.discard("weixin")
        normalized.add("sogou_weixin")
    if normalized == LEGACY_DEFAULT_KEYWORD_SOURCES:
        normalized.update({"baidu_news", "sogou_weixin"})
    return normalized


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").strip().lower())


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    if isinstance(value, (int, float)):
        if value <= 0:
            return None
        return datetime.fromtimestamp(float(value), tz=timezone.utc)

    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    if text.isdigit():
        return datetime.fromtimestamp(float(text), tz=timezone.utc)

    # RFC2822/RSS dates, e.g. "Wed, 09 Jul 2026 08:30:00 GMT"
    try:
        parsed = parsedate_to_datetime(text)
        if parsed:
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, IndexError):
        pass

    # Weibo mobile format, e.g. "Tue Jul 09 12:34:56 +0800 2026"
    try:
        return datetime.strptime(text, "%a %b %d %H:%M:%S %z %Y")
    except ValueError:
        pass

    try:
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    return None


def _parse_relative_datetime(text: str, now: datetime) -> datetime | None:
    for pattern, unit in CN_RELATIVE_PATTERNS + EN_RELATIVE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        value = int(match.group(1))
        if unit == "minutes":
            return now - timedelta(minutes=value)
        if unit == "hours":
            return now - timedelta(hours=value)
        if unit == "days":
            return now - timedelta(days=value)
        if unit == "weeks":
            return now - timedelta(weeks=value)

    match = re.search(r"(今天|昨日|昨天)\s*(\d{1,2}:\d{2})?", text)
    if match:
        day_token = match.group(1)
        time_token = match.group(2) or "00:00"
        hours, minutes = [int(part) for part in time_token.split(":")]
        base = now.astimezone(CHINA_TZ).replace(hour=hours, minute=minutes, second=0, microsecond=0)
        if day_token in {"昨日", "昨天"}:
            base -= timedelta(days=1)
        return base

    absolute_patterns = [
        (r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})[日]?\s*(\d{1,2}:\d{2})?", True),
        (r"(\d{1,2})[-/月](\d{1,2})[日]?\s*(\d{1,2}:\d{2})?", False),
    ]
    local_now = now.astimezone(CHINA_TZ)
    for pattern, has_year in absolute_patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        if has_year:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            time_token = match.group(4)
        else:
            year = local_now.year
            month = int(match.group(1))
            day = int(match.group(2))
            time_token = match.group(3)

        hour = 0
        minute = 0
        if time_token:
            hour, minute = [int(part) for part in time_token.split(":")]

        try:
            parsed = datetime(year, month, day, hour, minute, tzinfo=CHINA_TZ)
        except ValueError:
            continue

        if not has_year and parsed > local_now + timedelta(days=1):
            parsed = parsed.replace(year=parsed.year - 1)
        return parsed

    return None


def _extract_item_datetime(item: Dict[str, Any], now: datetime) -> datetime | None:
    source = item.get("source")

    candidates = []
    if source == "hackernews":
        candidates.append(item.get("time"))
    if item.get("published_at") is not None:
        candidates.append(item.get("published_at"))
    if item.get("created_at") is not None:
        candidates.append(item.get("created_at"))
    if isinstance(item.get("raw_data"), dict):
        raw_data = item["raw_data"]
        for key in ("published_at", "created_at", "time"):
            if raw_data.get(key) is not None:
                candidates.append(raw_data.get(key))

    for candidate in candidates:
        parsed = _coerce_datetime(candidate)
        if parsed:
            return parsed
        if isinstance(candidate, str):
            parsed = _parse_relative_datetime(candidate, now)
            if parsed:
                return parsed

    return None


def _filter_recent_items(items: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], Dict[str, Dict[str, int]]]:
    now = datetime.now(timezone.utc)
    kept: List[Dict[str, Any]] = []
    stats = {
        "kept": Counter(),
        "stale": Counter(),
        "unknown_time": Counter(),
    }

    for item in items:
        source = item.get("source", "unknown")
        if source in ALWAYS_FRESH_SOURCES:
            stats["kept"][source] += 1
            kept.append(item)
            continue

        published_at = _extract_item_datetime(item, now)
        if published_at is None:
            if source in STRICT_RECENCY_SOURCES:
                stats["unknown_time"][source] += 1
                continue
            stats["kept"][source] += 1
            kept.append(item)
            continue

        published_at_utc = published_at.astimezone(timezone.utc)
        item["published_at_resolved"] = published_at_utc.isoformat()
        max_age_hours = RECENCY_WINDOWS_HOURS.get(source, 168)
        if published_at_utc < now - timedelta(hours=max_age_hours):
            stats["stale"][source] += 1
            continue

        stats["kept"][source] += 1
        kept.append(item)

    return kept, {key: dict(counter) for key, counter in stats.items()}


def _dedupe_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: List[Dict[str, Any]] = []
    seen_urls = set()
    seen_titles = set()

    for item in items:
        title = _normalize_title(item.get("title", ""))
        url = (item.get("url") or item.get("primary_url") or item.get("link") or "").strip()

        if url and url in seen_urls:
            continue
        if title and title in seen_titles:
            continue

        if url:
            seen_urls.add(url)
        if title:
            seen_titles.add(title)
        deduped.append(item)

    return deduped


def _sort_trending_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    source_order = ["hackernews", "github", "baidu_news", "bing", "google_news", "weibo", "sogou_weixin"]
    grouped: Dict[str, List[Dict[str, Any]]] = {source: [] for source in source_order}
    extras: List[Dict[str, Any]] = []

    def sort_key(item: Dict[str, Any]) -> tuple:
        score = item.get("score")
        if isinstance(score, (int, float)):
            primary_score = float(score)
        else:
            primary_score = 0.0

        confidence = item.get("confidence")
        if isinstance(confidence, (int, float)):
            secondary_score = float(confidence)
        else:
            secondary_score = 0.0

        return (primary_score, secondary_score, len(item.get("title", "")))

    for item in items:
        source = item.get("source")
        if source in grouped:
            grouped[source].append(item)
        else:
            extras.append(item)

    for source in source_order:
        grouped[source].sort(key=sort_key, reverse=True)
    extras.sort(key=sort_key, reverse=True)

    merged: List[Dict[str, Any]] = []
    while True:
        added = False
        for source in source_order:
            if grouped[source]:
                merged.append(grouped[source].pop(0))
                added = True
        if not added:
            break

    merged.extend(extras)
    return merged


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, round(value, 1)))


def _hn_signal(item: Dict[str, Any]) -> float:
    raw_score = float(item.get("score") or 0.0)
    comments = float(item.get("descendants") or 0.0)
    return _clamp_score((raw_score / 18.0) + (comments / 6.0))


def _weibo_signal(item: Dict[str, Any]) -> float:
    quality_score = float(item.get("quality_score") or 0.0)
    metrics = item.get("public_metrics") or {}
    reposts = float(metrics.get("reposts_count") or 0.0)
    comments = float(metrics.get("comments_count") or 0.0)
    likes = float(metrics.get("attitudes_count") or 0.0)
    followers = float(metrics.get("followers_count") or 0.0)
    signal = quality_score * 0.55 + min(30.0, reposts * 2.5 + comments * 3.0 + likes * 0.25)
    if item.get("entity_type") == "account":
        signal += min(18.0, followers / 50000.0)
    return _clamp_score(signal)


def _generic_signal(item: Dict[str, Any]) -> float:
    has_summary = 1.0 if item.get("summary") or item.get("snippet") or item.get("description") else 0.0
    title_length = min(1.0, len(item.get("title", "")) / 120.0)
    return _clamp_score(45.0 + has_summary * 20.0 + title_length * 15.0)


def _compute_normalized_score(item: Dict[str, Any], rank: int | None = None) -> float:
    source = item.get("source")
    confidence = item.get("confidence")
    confidence_score = float(confidence) * 100.0 if isinstance(confidence, (int, float)) else None

    if source == "hackernews":
        source_signal = _hn_signal(item)
    elif source == "weibo":
        source_signal = _weibo_signal(item)
    else:
        source_signal = _generic_signal(item)

    if rank is not None:
        rank_score = max(45.0, 100.0 - rank * 3.0)
        return _clamp_score(rank_score)

    if confidence_score is None:
        return source_signal

    return _clamp_score(confidence_score * 0.75 + source_signal * 0.25)


def _prepare_item_for_storage(item: Dict[str, Any], rank: int | None = None) -> Dict[str, Any]:
    prepared = dict(item)
    prepared["raw_score"] = float(prepared.get("raw_score") or item.get("score") or 0.0)
    if not isinstance(prepared.get("normalized_score"), (int, float)):
        prepared["normalized_score"] = _compute_normalized_score(prepared, rank=rank)
    return prepared


async def _save_items(items: List[Dict[str, Any]], keyword: str = None) -> Dict[str, int]:
    """Save trending items to database, skipping duplicates by URL."""
    inserted = 0
    skipped_duplicate = 0
    skipped_missing_title = 0

    async with async_session_maker() as db:
        for item in items:
            item = _prepare_item_for_storage(item)
            url = item.get("url") or item.get("primary_url") or item.get("link")
            title = item.get("title") or item.get("name") or ""
            if not title:
                skipped_missing_title += 1
                continue
            item["title"] = title

            # Skip duplicates by URL
            if url:
                existing = await db.execute(
                    select(TrendingItem).where(TrendingItem.url == url)
                )
                if existing.scalar_one_or_none():
                    skipped_duplicate += 1
                    continue

            db_item = TrendingItem(
                title=title,
                url=url,
                source=item.get("source", "unknown"),
                score=item.get("score", 0.0),
                tags=item.get("tags"),
                keyword=keyword,
                raw_data=item,
                is_relevant=item.get("is_relevant", True),
                confidence=item.get("confidence"),
                summary=item.get("summary"),
            )
            db.add(db_item)
            inserted += 1

        await db.commit()

    return {
        "inserted": inserted,
        "skipped_duplicate": skipped_duplicate,
        "skipped_missing_title": skipped_missing_title,
        "attempted": len(items),
    }


async def run_keyword_monitor():
    """Fetch content for all active keywords and run AI relevance filtering."""
    print("Starting keyword monitor job...")
    async with async_session_maker() as db:
        result = await db.execute(select(Keyword).where(Keyword.is_active == True))
        keywords = result.scalars().all()

    for kw in keywords:
        sources = kw.sources or DEFAULT_KEYWORD_SOURCES
        normalized_sources = _normalize_sources(sources)
        all_items = []

        tasks = []
        if "hackernews" in normalized_sources:
            tasks.append(search_hn_by_keyword(kw.keyword))
        if "bing" in normalized_sources:
            tasks.append(search_bing(kw.keyword))
        if "google_news" in normalized_sources:
            tasks.append(search_google_news(kw.keyword))
        if "baidu_news" in normalized_sources:
            tasks.append(search_baidu_news(kw.keyword))
        if "sogou_weixin" in normalized_sources:
            tasks.append(search_sogou_weixin(kw.keyword))
        if "weibo" in normalized_sources:
            tasks.append(search_weibo(kw.keyword))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, list):
                all_items.extend(r)

        all_items, recency_stats = _filter_recent_items(all_items)
        if any(recency_stats.values()):
            print(f"Keyword '{kw.keyword}' recency stats: {recency_stats}")
        all_items = _dedupe_items(all_items)

        # AI relevance filtering — one batch call instead of one per item
        relevant_items = []
        if all_items:
            try:
                analyses = await analyze_relevance_batch(kw.keyword, all_items)
                for item, analysis in zip(all_items, analyses):
                    if analysis.get("relevant") and analysis.get("confidence", 0) >= 0.6:
                        item["is_relevant"] = True
                        item["confidence"] = analysis["confidence"]
                        relevant_items.append(item)
            except Exception as e:
                print(f"Batch AI analysis error for '{kw.keyword}': {e}")
                relevant_items = all_items  # fallback: keep all

        if relevant_items:
            save_stats = await _save_items(relevant_items, keyword=kw.keyword)
            print(
                f"Keyword '{kw.keyword}': attempted {save_stats['attempted']}, "
                f"inserted {save_stats['inserted']}, duplicates {save_stats['skipped_duplicate']}, "
                f"missing_title {save_stats['skipped_missing_title']}"
            )
            try:
                from app.services.notifier import notify_keyword_matches
                await notify_keyword_matches(kw.keyword, relevant_items)
            except Exception as e:
                print(f"Notification error for '{kw.keyword}': {e}")

    print("Keyword monitor job complete.")


async def run_trending_collector():
    """Collect trending content from all sources and save deduped raw items."""
    print("Starting trending collector job...")

    source_tasks = [
        ("hackernews", fetch_hn_trending(limit=30)),
        ("github", fetch_github_trending()),
        ("baidu_news", search_baidu_news(TRENDING_NEWS_QUERY, limit=20)),
        ("bing", search_bing(TRENDING_NEWS_QUERY, limit=20)),
        ("google_news", search_google_news(TRENDING_NEWS_QUERY, limit=20)),
    ]
    results = await asyncio.gather(*(task for _, task in source_tasks), return_exceptions=True)

    all_items = []
    fetched_counts: Dict[str, int] = {}
    for (source_name, _), result in zip(source_tasks, results):
        if isinstance(result, Exception):
            fetched_counts[source_name] = 0
            print(f"Trending source '{source_name}' failed: {repr(result)}")
            continue

        fetched_counts[source_name] = len(result)
        if not result:
            print(f"Trending source '{source_name}' returned 0 items.")
            continue

        all_items.extend(result)

    all_items, recency_stats = _filter_recent_items(all_items)
    print(f"Trending recency stats: {recency_stats}")
    all_items = _dedupe_items(all_items)
    deduped_counts = Counter(item.get("source", "unknown") for item in all_items)

    if not all_items:
        print("No items collected for trending.")
        return

    for item in all_items:
        item["is_relevant"] = True
        if not item.get("summary"):
            item["summary"] = item.get("snippet") or item.get("description") or ""

    ranked_items = _sort_trending_items(all_items)[:20]
    selected_counts = Counter(item.get("source", "unknown") for item in ranked_items)
    ranked_items = [_prepare_item_for_storage(item, rank=index) for index, item in enumerate(ranked_items)]
    save_stats = await _save_items(ranked_items)
    print(
        "Trending source counts: "
        f"fetched={dict(fetched_counts)}, "
        f"deduped={dict(deduped_counts)}, "
        f"selected={dict(selected_counts)}"
    )
    print(
        f"Trending save stats: attempted {save_stats['attempted']}, "
        f"inserted {save_stats['inserted']}, duplicates {save_stats['skipped_duplicate']}, "
        f"missing_title {save_stats['skipped_missing_title']}"
    )

    print("Trending collector job complete.")
