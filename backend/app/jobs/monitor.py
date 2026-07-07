import asyncio
from typing import List, Dict, Any
from sqlalchemy import select

from app.db.database import async_session_maker
from app.db.models import Keyword, TrendingItem
from app.ai.openrouter import analyze_relevance_batch, extract_trending_topics
from app.services.scrapers.hackernews import fetch_hn_trending, search_hn_by_keyword
from app.services.scrapers.github import fetch_github_trending
from app.services.scrapers.bing import search_bing
from app.services.scrapers.weibo import search_weibo


def _collect_item_urls(item: Dict[str, Any]) -> List[str]:
    urls: List[str] = []
    for key in ("primary_url", "url", "link"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            urls.append(value.strip())

    raw_urls = item.get("raw_urls")
    if isinstance(raw_urls, list):
        for value in raw_urls:
            if isinstance(value, str) and value.strip():
                urls.append(value.strip())

    deduped: List[str] = []
    seen = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        deduped.append(url)
    return deduped


def _attach_topic_links(topics: List[Dict[str, Any]], source_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    enriched_topics: List[Dict[str, Any]] = []

    for topic in topics:
        indices = topic.get("source_indices")
        if not isinstance(indices, list):
            indices = []

        topic_urls: List[str] = []
        for index in indices:
            if not isinstance(index, int):
                continue
            if index < 0 or index >= len(source_items):
                continue
            topic_urls.extend(_collect_item_urls(source_items[index]))

        deduped_urls: List[str] = []
        seen = set()
        for url in topic_urls:
            if url in seen:
                continue
            seen.add(url)
            deduped_urls.append(url)

        existing_urls = _collect_item_urls(topic)
        for url in existing_urls:
            if url in seen:
                continue
            seen.add(url)
            deduped_urls.append(url)

        topic["raw_urls"] = deduped_urls
        topic["primary_url"] = deduped_urls[0] if deduped_urls else None
        topic["url"] = topic.get("url") or topic["primary_url"]
        enriched_topics.append(topic)

    return enriched_topics


def _normalize_sources(sources: List[str]) -> set:
    normalized = set(sources)
    if "nitter" in normalized:
        normalized.discard("nitter")
        normalized.add("weibo")
    return normalized


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
        sources = kw.sources or ["hackernews", "bing", "weibo"]
        normalized_sources = _normalize_sources(sources)
        all_items = []

        tasks = []
        if "hackernews" in normalized_sources:
            tasks.append(search_hn_by_keyword(kw.keyword))
        if "bing" in normalized_sources:
            tasks.append(search_bing(kw.keyword))
        if "weibo" in normalized_sources:
            tasks.append(search_weibo(kw.keyword))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, list):
                all_items.extend(r)

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
    """Collect trending content from all sources and extract top topics via AI."""
    print("Starting trending collector job...")

    hn_task = fetch_hn_trending(limit=30)
    github_task = fetch_github_trending()
    results = await asyncio.gather(hn_task, github_task, return_exceptions=True)

    all_items = []
    for r in results:
        if isinstance(r, list):
            all_items.extend(r)

    if not all_items:
        print("No items collected for trending.")
        return

    # AI extracts and ranks top topics
    try:
        topics = await extract_trending_topics("AI & Technology", all_items, top_n=20)
        topics = _attach_topic_links(topics, all_items)
        for topic in topics:
            topic["source"] = topic.get("source", "aggregated")
            topic["is_relevant"] = True
        await _save_items(topics)
        print(f"Saved {len(topics)} trending topics.")
    except Exception as e:
        print(f"AI trending extraction error: {e}")
        # Fallback: save raw items without AI processing
        await _save_items(all_items[:20])
        print(f"Saved {min(20, len(all_items))} raw trending items (fallback).")

    print("Trending collector job complete.")
