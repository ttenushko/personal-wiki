from __future__ import annotations

import re
from datetime import datetime

from wikillm.core.fetcher import fetch_url_content
from wikillm.core.llm import extract_tags, generate_slug, process_with_llm
from wikillm.core.logger import logger
from wikillm.core.models import WikiPage
from wikillm.core.storage import WikiStorage, is_valid_slug, safe_filename
from wikillm.core.validation import transliterate_slug_fallback


class WikiManager:
    """High-level wiki operations."""

    def __init__(self) -> None:
        self.storage = WikiStorage()

    def _unique_slug(self, base: str) -> str:
        """Return a filesystem-safe slug, appending -2/-3... on collision."""
        slug = base if is_valid_slug(base) else safe_filename(transliterate_slug_fallback(base))
        candidate = slug
        counter = 2
        while self.storage.page_exists(candidate):
            candidate = f"{slug}-{counter}"
            counter += 1
        return candidate

    async def _ingest(
        self,
        content: str,
        source_url: str | None,
        source_type: str,
        instruction: str,
        context: str,
        user_tags: list[str] | None,
    ) -> WikiPage:
        processed = await process_with_llm(
            content=content,
            context=context,
            instruction=instruction,
        )
        title = self._extract_title(processed)
        slug = self._unique_slug(await generate_slug(title))
        auto_tags = await extract_tags(processed, user_tags)
        tags = list(dict.fromkeys(auto_tags + (user_tags or [])))

        page = WikiPage(
            slug=slug,
            title=title,
            content=processed,
            tags=tags,
            source_url=source_url,
            source_type=source_type,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self.storage.save_page(
            slug=page.slug,
            content=page.to_markdown(),
            message=f"Add/update wiki page: {page.title}",
        )
        await self._update_index(page)
        return page

    async def ingest_text(
        self,
        text: str,
        user_tags: list[str] | None = None,
    ) -> WikiPage:
        """Process raw text and create/update wiki pages."""
        return await self._ingest(
            content=text,
            source_url=None,
            source_type="text",
            instruction="Создай структурированную страницу вики из этого текста.",
            context="",
            user_tags=user_tags,
        )

    async def ingest_url(
        self,
        url: str,
        text: str | None = None,
        user_tags: list[str] | None = None,
    ) -> WikiPage:
        """Process a URL and create a wiki page."""
        content = text or ""

        try:
            fetched = await fetch_url_content(url)
            if fetched:
                content = fetched
        except Exception as exc:
            logger.info(f"  не удалось загрузить {url}: {exc}")

        if not content:
            content = f"Ссылка: {url}"

        return await self._ingest(
            content=content,
            source_url=url,
            source_type="link",
            instruction=(
                "Создай страницу вики на основе этой ссылки. "
                "Если доступен контент страницы, опиши его."
            ),
            context=f"Исходная ссылка: {url}",
            user_tags=user_tags,
        )

    async def ingest_file(
        self,
        filename: str,
        content: str,
        user_tags: list[str] | None = None,
    ) -> WikiPage:
        """Process an uploaded file and create a wiki page."""
        return await self._ingest(
            content=content,
            source_url=None,
            source_type="file",
            instruction="Проанализируй содержимое файла и создай страницу вики.",
            context=f"Файл: {filename}",
            user_tags=user_tags,
        )

    def get_page(self, slug: str) -> WikiPage | None:
        """Get a wiki page by slug."""
        content = self.storage.get_page(slug)
        if content:
            return WikiPage.from_markdown(slug, content)
        return None

    def list_pages(self) -> list[str]:
        """List all wiki page slugs."""
        return [s for s in self.storage.list_pages() if s != "index"]

    def list_tags(self) -> dict[str, int]:
        """Get all tags with page counts."""
        tag_counts: dict[str, int] = {}
        for slug in self.list_pages():
            page = self.get_page(slug)
            if page:
                for tag in page.tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True))

    def delete_page(self, slug: str) -> bool:
        """Delete a wiki page."""
        if not self.storage.page_exists(slug):
            return False
        return self.storage.delete_page(slug, f"Delete wiki page: {slug}")

    def search_pages(self, query: str) -> list[WikiPage]:
        """Search pages by query."""
        q = query.lower()
        results = []
        for slug in self.list_pages():
            page = self.get_page(slug)
            if not page:
                continue
            haystack = " ".join(page.tags).lower()
            if q in page.title.lower() or q in page.content.lower() or q in haystack:
                results.append(page)
        return results

    async def _update_index(self, new_page: WikiPage) -> None:
        """Update the wiki index page."""
        index_content = self.storage.get_index()

        tags_str = ", ".join(f"`#{t}`" for t in new_page.tags)
        link = f"{safe_filename(new_page.slug)}.html"
        entry = f"- [{new_page.title}]({link}) — {tags_str}\n"

        if f"({link})" not in index_content:
            index_content += entry
            self.storage.save_index(
                index_content,
                message=f"Update index: add {new_page.title}",
            )

    @staticmethod
    def _extract_title(text: str) -> str:
        """Extract title from markdown text.

        Prefers the first H1 heading; falls back to the first non-empty
        line that is not frontmatter.
        """
        lines = text.strip().splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
            if not stripped:
                continue
            if stripped == "---":
                # Пропускаем строки frontmatter (title: ... и т.п.)
                continue
            if re.match(r"^[a-z_]+:", stripped, re.IGNORECASE):
                continue
            return stripped[:100]
        return "Untitled"
