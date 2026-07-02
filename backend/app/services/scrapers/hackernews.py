import httpx
from typing import List, Dict, Any


async def fetch_hn_trending(limit: int = 30) -> List[Dict[str, Any]]:
    """Fetch trending stories from Hacker News"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get('https://hacker-news.firebaseio.com/v0/topstories.json')
            response.raise_for_status()
            story_ids = response.json()[:limit]

            stories = []
            for story_id in story_ids:
                try:
                    story_response = await client.get(
                        f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json'
                    )
                    story_response.raise_for_status()
                    story = story_response.json()

                    if story and story.get('type') == 'story':
                        stories.append({
                            'id': story.get('id'),
                            'title': story.get('title', ''),
                            'url': story.get('url', f"https://news.ycombinator.com/item?id={story.get('id')}"),
                            'score': story.get('score', 0),
                            'by': story.get('by', ''),
                            'time': story.get('time', 0),
                            'descendants': story.get('descendants', 0),
                            'source': 'hackernews'
                        })
                except Exception as e:
                    print(f"Error fetching HN story {story_id}: {e}")
                    continue

            return stories
        except Exception as e:
            print(f"Error fetching HN trending: {e}")
            return []


async def search_hn_by_keyword(keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search Hacker News stories by keyword using Algolia API"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                'https://hn.algolia.com/api/v1/search',
                params={
                    'query': keyword,
                    'tags': 'story',
                    'hitsPerPage': limit
                }
            )
            response.raise_for_status()
            data = response.json()

            stories = []
            for hit in data.get('hits', []):
                stories.append({
                    'id': hit.get('objectID'),
                    'title': hit.get('title', ''),
                    'url': hit.get('url', f"https://news.ycombinator.com/item?id={hit.get('objectID')}"),
                    'score': hit.get('points', 0),
                    'by': hit.get('author', ''),
                    'time': hit.get('created_at_i', 0),
                    'descendants': hit.get('num_comments', 0),
                    'source': 'hackernews'
                })

            return stories
        except Exception as e:
            print(f"Error searching HN by keyword '{keyword}': {e}")
            return []
