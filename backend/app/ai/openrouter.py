import httpx
import json
from typing import Optional, Dict, Any
from app.config import settings


async def call_openrouter(
    prompt: str,
    content: str,
    model: str = "gpt-5.4",
    temperature: float = 0.7,
    max_tokens: int = 2000
) -> str:
    """Call linkapi.ai with given prompt and content"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            'https://linkapi.ai/v1/chat/completions',
            json={
                'model': model,
                'messages': [
                    {'role': 'system', 'content': prompt},
                    {'role': 'user', 'content': content}
                ],
                'temperature': temperature,
                'max_tokens': max_tokens
            },
            headers={
                'Authorization': f"Bearer {settings.openrouter_api_key}",
                'HTTP-Referer': settings.app_url,
                'X-Title': 'AI Trending Monitor'
            }
        )
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']


async def analyze_relevance_batch(keyword: str, items: list) -> list:
    """Batch relevance analysis — one AI call for all items."""
    prompt = f"""你是内容相关性分析专家。判断以下每条内容是否与关键词"{keyword}"相关。

要求：
1. 排除标题党、假冒、无关内容
2. 内容必须实质性提到该关键词或其直接相关概念
3. 返回 JSON 数组，长度必须与输入条目数相同，顺序一一对应
4. 格式: [{{"relevant": boolean, "confidence": float}}]"""

    items_str = json.dumps(
        [{"index": i, "title": it.get("title", ""), "url": it.get("url", "")} for i, it in enumerate(items)],
        ensure_ascii=False
    )

    try:
        result = await call_openrouter(prompt, items_str, temperature=0.2, max_tokens=2000)
        result_clean = result.strip()
        if result_clean.startswith('```json'):
            result_clean = result_clean[7:]
        if result_clean.startswith('```'):
            result_clean = result_clean[3:]
        if result_clean.endswith('```'):
            result_clean = result_clean[:-3]
        parsed = json.loads(result_clean.strip())
        if isinstance(parsed, list) and len(parsed) == len(items):
            return parsed
    except Exception as e:
        print(f"Batch AI analysis error: {e}")

    # fallback: mark all relevant
    return [{"relevant": True, "confidence": 0.5}] * len(items)


async def analyze_relevance(keyword: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """Use AI to determine if content is relevant to keyword"""
    prompt = f"""你是一个内容相关性分析专家。判断以下内容是否真正与关键词"{keyword}"相关。

要求：
1. 排除标题党、假冒、无关内容
2. 内容必须实质性提到该关键词或其直接相关概念
3. 返回JSON格式: {{"relevant": boolean, "reason": string, "confidence": float}}

其中 confidence 为 0-1 之间的浮点数，表示相关性置信度。"""

    content_str = json.dumps(item, ensure_ascii=False, indent=2)

    try:
        result = await call_openrouter(prompt, content_str, temperature=0.3, max_tokens=500)
        # Try to parse JSON from result
        result_clean = result.strip()
        if result_clean.startswith('```json'):
            result_clean = result_clean[7:]
        if result_clean.startswith('```'):
            result_clean = result_clean[3:]
        if result_clean.endswith('```'):
            result_clean = result_clean[:-3]

        parsed = json.loads(result_clean.strip())
        return {
            'relevant': parsed.get('relevant', False),
            'reason': parsed.get('reason', ''),
            'confidence': parsed.get('confidence', 0.0)
        }
    except Exception as e:
        return {
            'relevant': False,
            'reason': f'AI分析失败: {str(e)}',
            'confidence': 0.0
        }


async def extract_trending_topics(domain: str, items: list, top_n: int = 10) -> list:
    """Extract and rank trending topics from multiple sources"""
    prompt = f"""你是一个热点内容分析专家。从以下内容中提取"{domain}"领域的前{top_n}个热点话题。

要求：
1. 排除重复、过时、无关内容
2. 按热度和重要性排序
3. 为每个热点生成简洁摘要
4. 返回JSON数组格式: [{{"title": string, "summary": string, "source": string, "score": float, "tags": [string]}}]

score 为 0-100 的热度分数。"""

    items_str = json.dumps(items, ensure_ascii=False, indent=2)

    try:
        result = await call_openrouter(prompt, items_str, temperature=0.5, max_tokens=3000)
        result_clean = result.strip()
        if result_clean.startswith('```json'):
            result_clean = result_clean[7:]
        if result_clean.startswith('```'):
            result_clean = result_clean[3:]
        if result_clean.endswith('```'):
            result_clean = result_clean[:-3]

        parsed = json.loads(result_clean.strip())
        return parsed if isinstance(parsed, list) else []
    except Exception as e:
        print(f"Error extracting trending topics: {e}")
        return []


async def generate_summary(items: list) -> str:
    """Generate daily summary from trending items"""
    prompt = """你是一个内容摘要专家。为以下热点内容生成一份简洁的每日摘要。

要求：
1. 突出最重要的3-5个热点
2. 使用简洁、专业的语言
3. 按重要性排序
4. 总长度控制在300字以内"""

    items_str = json.dumps(items, ensure_ascii=False, indent=2)

    try:
        result = await call_openrouter(prompt, items_str, temperature=0.7, max_tokens=1000)
        return result.strip()
    except Exception as e:
        return f"摘要生成失败: {str(e)}"
