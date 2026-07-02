import httpx
from typing import List, Dict, Any
from app.config import settings


async def search_twitter(keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search Twitter via twitterapi.io"""
    if not settings.twitter_api_key:
        print("Twitter API key not configured")
        return []

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                'https://api.twitterapi.io/v1/tweets/search',
                params={
                    'query': keyword,
                    'max_results': limit
                },
                headers={
                    'X-API-Key': settings.twitter_api_key
                }
            )
            response.raise_for_status()
            data = response.json()

            tweets = []
            for tweet in data.get('data', []):
                tweets.append({
                    'id': tweet.get('id'),
                    'text': tweet.get('text', ''),
                    'author_id': tweet.get('author_id', ''),
                    'created_at': tweet.get('created_at', ''),
                    'url': f"https://twitter.com/i/web/status/{tweet.get('id')}",
                    'public_metrics': tweet.get('public_metrics', {}),
                    'source': 'twitter'
                })

            return tweets
        except httpx.HTTPStatusError as e:
            print(f"Twitter API error: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            print(f"Error searching Twitter for '{keyword}': {e}")
            return []
