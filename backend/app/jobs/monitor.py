import asyncio
import re
from typing import List, Dict, Any
from sqlalchemy import select

from app.db.database import async_session_maker
from app.db.models import Keyword, TrendingItem
from app.ai.openrouter import analyze_relevance_batch
from app.services.scrapers.hackernews import fetch_hn_trending, search_hn_by_keyword
from app.services.scrapers.github import fetch_github_trending
from app.services.scrapers.bing import search_bing
from app.services.scrapers.google_news import search_google_news
from app.services.scrapers.weibo import search_weibo


DEFAULT_KEYWORD_SOURCES = ["hackernews", "bing", "google_news", "weibo"]
TRENDING_NEWS_QUERY = '"AI" OR "LLM" OR "agent" OR "OpenAI" OR "Anthropic" OR "Gemini"'


def _normalize_sources(sources: List[str]) -> set:
    normalized = set(sources)
    if "nitter" in normalized:
        normalized.discard("nitter")
        normalized.add("weibo")
    if "google" in normalized:
        normalized.discard("google")
        normalized.add("google_news")
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
    source_order = ["hackernews", "github", "bing", "google_news", "weibo"]
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


async def _save_items(items: List[Dict[str, Any]], keyword: str = None):
    """Save trending items to database, skipping duplicates by URL."""
    async with async_session_maker() as db:
        for item in items:
            url = item.get("url") or item.get("primary_url") or item.get("link")
            title = item.get("title", "")
            if not title:
                continue

            # Skip duplicates by URL
            if url:
                existing = await db.execute(
                    select(TrendingItem).where(TrendingItem.url == url)
                )
                if existing.scalar_one_or_none():
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

        await db.commit()


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
            await _save_items(relevant_items, keyword=kw.keyword)
            print(f"Saved {len(relevant_items)} items for keyword '{kw.keyword}'")
            try:
                from app.services.notifier import notify_keyword_matches
                await notify_keyword_matches(kw.keyword, relevant_items)
            except Exception as e:
                print(f"Notification error for '{kw.keyword}': {e}")

    print("Keyword monitor job complete.")


async def run_trending_collector():
    """Collect trending content from all sources and save deduped raw items."""
    print("Starting trending collector job...")

    hn_task = fetch_hn_trending(limit=30)
    github_task = fetch_github_trending()
    bing_task = search_bing(TRENDING_NEWS_QUERY, limit=20)
    google_news_task = search_google_news(TRENDING_NEWS_QUERY, limit=20)
    results = await asyncio.gather(hn_task, github_task, bing_task, google_news_task, return_exceptions=True)

    all_items = []
    for r in results:
        if isinstance(r, list):
            all_items.extend(r)

    all_items = _dedupe_items(all_items)

    if not all_items:
        print("No items collected for trending.")
        return

    for item in all_items:
        item["is_relevant"] = True
        if not item.get("summary"):
            item["summary"] = item.get("snippet") or item.get("description") or ""

    ranked_items = _sort_trending_items(all_items)[:20]
    await _save_items(ranked_items)
    print(f"Saved {len(ranked_items)} raw trending items.")

    print("Trending collector job complete.")
