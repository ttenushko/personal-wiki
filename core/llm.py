from __future__ import annotations

import httpx

from config.settings import settings


async def process_with_llm(
    content: str,
    context: str = "",
    instruction: str = "",
) -> str:
    """Send content to LLM via OpenRouter and get a response."""
    prompt = f"""Ты — ассистент по обработке знаний. Проанализируй материал и создай структурированную страницу вики.

Инструкция: {instruction}

Контекст: {context}

Материал:
{content}

Создай markdown-страницу с:
1. Кратким заголовком
2. Основным содержимым (структурированным, с разделами если нужно)
3. Ключевыми моментами
4. Связями с другими темами (если угадываются)

Формат: чистый markdown без frontmatter."""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openrouter_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4096,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def extract_tags(content: str) -> list[str]:
    """Use LLM to extract relevant tags from content."""
    prompt = f"""Проанализируй текст и предложи 3-7 релевантных тегов на русском языке.
Теги должны быть короткими (1-2 слова), начинаться с #.

Текст:
{content[:2000]}

Верни только список тегов через запятую, например: #android, #разработка, #производительность"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openrouter_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        tags_text = data["choices"][0]["message"]["content"]
        return [
            tag.strip().lstrip("#")
            for tag in tags_text.split(",")
            if tag.strip()
        ]


async def generate_slug(title: str) -> str:
    """Generate a URL-friendly slug from a title."""
    prompt = f"""Преобразуй заголовок в URL-friendly slug на английском языке.
Только slug, без кавычек и пояснений.

Заголовок: {title}"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openrouter_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 50,
            },
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip().lower()
