from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from wikillm.core.logger import logger

TEXT_CONTENT_TYPES = (
    "text/html",
    "application/xhtml",
    "text/plain",
    "text/markdown",
    "application/json",
    "application/xml",
)


async def fetch_url_content(url: str) -> str:
    """Download a URL and extract readable text."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=30.0,
        headers=headers,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    content_type = response.headers.get("content-type", "").lower()

    # Не-текстовые ресурсы (PDF, изображения, архивы) не разбираем
    if not any(ct in content_type for ct in TEXT_CONTENT_TYPES):
        logger.info(f"  пропускаю не-HTML контент: {content_type or 'unknown'}")
        return ""

    if "text/html" in content_type or "application/xhtml" in content_type:
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        main = soup.find("article") or soup.find("main")
        body = main or soup.body or soup

        for tag in body(["script", "style", "noscript"]):
            tag.decompose()

        text = body.get_text(separator="\n", strip=True)
        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())

        if len(text) > 20000:
            text = text[:20000] + "\n... (обрезка)"

        return f"# {title}\n\n{text}" if title else text

    # Простой текстовый контент — вернём как есть
    text = response.text[:20000]
    return f"# Файл\n\n{text}"
