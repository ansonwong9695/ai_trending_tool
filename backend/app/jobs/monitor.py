import asyncio
import re
from collections import Counter
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
    signal = quality_score * 0.55 + min(30.0, reposts * 2.5 + comments * 3.0 + likes * 0.25)
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
