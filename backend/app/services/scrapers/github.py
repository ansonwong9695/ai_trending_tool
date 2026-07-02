import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any


async def fetch_github_trending(language: str = "", since: str = "daily") -> List[Dict[str, Any]]:
    """Fetch GitHub trending repositories"""
    async with httpx.AsyncClient(
        timeout=30.0,
        headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'},
        follow_redirects=True
    ) as client:
        try:
            url = "https://github.com/trending"
            if language:
                url += f"/{language}"
            url += f"?since={since}"

            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            repos = []

            for article in soup.select('article.Box-row'):
                try:
                    title_elem = article.select_one('h2 a')
                    desc_elem = article.select_one('p.col-9')
                    stars_elem = article.select_one('span.d-inline-block.float-sm-right')
                    lang_elem = article.select_one('[itemprop="programmingLanguage"]')

                    if title_elem:
                        repo_path = title_elem.get('href', '').strip('/')
                        repos.append({
                            'name': repo_path,
                            'url': f"https://github.com/{repo_path}",
                            'description': desc_elem.get_text(strip=True) if desc_elem else '',
                            'stars': stars_elem.get_text(strip=True) if stars_elem else '0',
                            'language': lang_elem.get_text(strip=True) if lang_elem else '',
                            'source': 'github'
                        })
                except Exception as e:
                    print(f"Error parsing GitHub trending item: {e}")
                    continue

            return repos
        except Exception as e:
            print(f"Error fetching GitHub trending: {e}")
            return []
