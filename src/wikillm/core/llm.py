from __future__ import annotations

import asyncio
import base64
from pathlib import Path

import httpx

from wikillm.config.settings import LLMProvider, settings
from wikillm.core.logger import logger
from wikillm.core.spinner import spinner
from wikillm.core.validation import clean_slug, extract_tags_from_text, transliterate_slug_fallback

MAX_RETRIES = 3
RETRY_DELAY = 5.0

TRANSIENT_CODES = (429, 500, 502, 503, 504)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _load_prompt(name: str, **kwargs: str) -> str:
    """Load a markdown prompt template and substitute {{var}} placeholders."""
    path = PROMPTS_DIR / name
    text = path.read_text(encoding="utf-8")
    for key, value in kwargs.items():
        text = text.replace("{{" + key + "}}", value)
    return text.strip()


async def _openrouter_completion(
    client: httpx.AsyncClient,
    provider: LLMProvider,
    payload: dict,
    timeout: float,
) -> dict | None:
    """POST to an OpenAI-compatible API with retries on transient errors."""
    base_url = (provider.base_url or "https://openrouter.ai/api/v1").rstrip("/")
    body = {"model": provider.model, **payload}
    if provider.provider == "ollama":
        body["think"] = False
    for attempt in range(MAX_RETRIES):
        response = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {provider.api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=timeout,
        )
        if response.status_code in TRANSIENT_CODES:
            if attempt == MAX_RETRIES - 1:
                return None
            wait = RETRY_DELAY * (2**attempt)
            logger.info(f"  {provider.model}: {response.status_code}, повтор через {wait:.0f}с...")
            await asyncio.sleep(wait)
            continue
        if response.status_code >= 400:
            logger.info(
                f"  {provider.model}: {response.status_code} {response.text[:200]}"
            )
            return None
        data = response.json()
        if provider.provider == "ollama":
            msg = data["choices"][0]["message"]
            if not msg.get("content") and msg.get("reasoning"):
                msg["content"] = msg["reasoning"]
        return data
    return None


async def _opencode_completion(
    client: httpx.AsyncClient,
    provider: LLMProvider,
    payload: dict,
    timeout: float,
) -> dict | None:
    """Send a prompt to a local opencode server via its HTTP API."""
    base_url = provider.base_url.rstrip("/")
    headers = {}
    if provider.password:
        token = base64.b64encode(
            f"{provider.username}:{provider.password}".encode()
        ).decode()
        headers["Authorization"] = f"Basic {token}"

    # Соберём все текстовые части: system-prompt + сообщения пользователя
    texts = []
    for msg in payload["messages"]:
        parts = msg.get("parts") if isinstance(msg.get("parts"), list) else None
        if isinstance(msg.get("content"), str):
            texts.append(msg["content"])
        elif parts:
            texts.extend(
                part.get("text", "")
                for part in parts
                if isinstance(part, dict) and part.get("type") == "text"
            )

    prompt = "\n\n".join(texts)

    try:
        session = await client.post(
            f"{base_url}/session",
            headers=headers,
            json={"title": "wiki"},
            timeout=timeout,
        )
        if session.status_code in TRANSIENT_CODES:
            return None
        session.raise_for_status()
        session_id = session.json()["id"]

        message = await client.post(
            f"{base_url}/session/{session_id}/message",
            headers=headers,
            json={
                "model": provider.model,
                "parts": [{"type": "text", "text": prompt}],
            },
            timeout=timeout,
        )
        if message.status_code in TRANSIENT_CODES:
            return None
        message.raise_for_status()
        parts = message.json().get("parts", [])
        content = "".join(
            part.get("text", "") for part in parts if part.get("type") == "text"
        )
        if not content:
            return None
        return {"choices": [{"message": {"content": content}}]}
    except httpx.HTTPStatusError as exc:
        logger.info(f"  opencode {provider.model}: {exc.response.status_code}")
        return None


async def _complete_with(
    client: httpx.AsyncClient,
    provider: LLMProvider,
    payload: dict,
    timeout: float,
) -> dict | None:
    if provider.provider == "opencode":
        return await _opencode_completion(client, provider, payload, timeout)
    # "openrouter" and "ollama" are both OpenAI-compatible chat/completions APIs
    return await _openrouter_completion(client, provider, payload, timeout)


async def _complete(payload: dict, timeout: float) -> dict:
    """Try each configured provider in order."""
    providers = list(settings.llm_providers)
    if not providers:
        providers = [
            LLMProvider(
                provider="openrouter",
                model=settings.openrouter_model,
                api_key=settings.openrouter_api_key,
            )
        ]
    async with httpx.AsyncClient() as client:
        for provider in providers:
            try:
                data = await _complete_with(client, provider, payload, timeout)
            except Exception as exc:
                logger.info(
                    f"  {provider.provider}/{provider.model}: {type(exc).__name__}: {exc}"
                )
                data = None
            if data:
                return data
            logger.info(
                f"  {provider.provider}/{provider.model}:"
                " не сработал, пробуем следующий..."
            )
    raise httpx.HTTPError("все провайдеры вернули ошибку")


async def process_with_llm(
    content: str,
    context: str = "",
    instruction: str = "",
) -> str:
    """Send content to LLM and get a response."""
    system_prompt = _load_prompt("process_system.md")
    instruction_block = ""
    if instruction:
        instruction_block = f"# Инструкция\n\n{instruction}"
    context_block = ""
    if context:
        context_block = f"# Контекст вики (смежные темы)\n\n{context}"
    prompt = _load_prompt(
        "process_user.md",
        instruction=instruction_block,
        context=context_block,
        content=content,
    )

    async with spinner("Модель создаёт страницу..."):
        data = await _complete(
            {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 4096,
            },
            timeout=300.0,
        )
    return data["choices"][0]["message"]["content"]


async def extract_tags(content: str, user_tags: list[str] | None = None) -> list[str]:
    """Use LLM to extract relevant tags from content."""
    system_prompt = _load_prompt("tags_system.md")
    user_tags_block = ""
    if user_tags:
        user_tags_block = ", ".join(f"#{t}" for t in user_tags)
    prompt = _load_prompt(
        "tags_user.md",
        content=content[:2000],
        user_tags=user_tags_block,
    )

    try:
        async with spinner("Модель подбирает теги..."):
            data = await _complete(
                {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 200,
                },
                timeout=120.0,
            )
        tags_text = data["choices"][0]["message"]["content"]
        tags = extract_tags_from_text(tags_text)
    except Exception as exc:
        logger.info(f"  extract_tags: {type(exc).__name__}: {exc}")
        tags = []

    # Пользовательские теги — всегда в приоритете и гарантированно валидны
    for user_tag in user_tags or []:
        clean = user_tag.strip().strip("#").strip()
        if clean and clean not in tags:
            tags.append(clean)
    return tags


async def generate_slug(title: str) -> str:
    """Generate a URL-friendly slug from a title."""
    system_prompt = _load_prompt("slug_system.md")
    prompt = _load_prompt("slug_user.md", title=title)

    try:
        async with spinner("Модель генерирует slug..."):
            data = await _complete(
                {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 50,
                },
                timeout=15.0,
            )
        raw = data["choices"][0]["message"]["content"]
        slug = clean_slug(raw)
        if slug:
            return slug
        logger.info(f"  generate_slug: модель вернула мусор: {raw!r}")
    except Exception as exc:
        logger.info(f"  generate_slug: {type(exc).__name__}: {exc}")

    # Фолбэк без LLM — транслитерация заголовка
    return transliterate_slug_fallback(title)
