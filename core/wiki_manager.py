from __future__ import annotations

import re
from datetime import datetime

from core.github_wiki import GitHubWiki
from core.llm import extract_tags, generate_slug, process_with_llm
from core.models import WikiPage


class WikiManager:
    """High-level wiki operations."""

    def __init__(self) -> None:
        self.github = GitHubWiki()

    async def ingest_text(
        self,
        text: str,
        user_tags: list[str] | None = None,
    ) -> WikiPage:
        """Process raw text and create/update wiki pages."""
        # Get LLM to process the content
        processed = await process_with_llm(
            content=text,
            instruction="Создай структурированную страницу вики из этого текста.",
        )

        # Extract title (first line or first heading)
        title = self._extract_title(processed)

        # Generate slug
        slug = await generate_slug(title)

        # Get tags from LLM and merge with user tags
        auto_tags = await extract_tags(processed)
        tags = list(set(auto_tags + (user_tags or [])))

        # Create page
        page = WikiPage(
            slug=slug,
            title=title,
            content=processed,
            tags=tags,
            source_type="text",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Save to GitHub
        filepath = f"wiki/{page.slug}.md"
        self.github.create_or_update_file(
            path=filepath,
            content=page.to_markdown(),
            message=f"Add/update wiki page: {page.title}",
        )

        # Update index
        await self._update_index(page)

        return page

    async def ingest_url(
        self,
        url: str,
        text: str | None = None,
        user_tags: list[str] | None = None,
    ) -> WikiPage:
        """Process a URL and create a wiki page."""
        content = text or f"Ссылка: {url}"

        processed = await process_with_llm(
            content=content,
            context=f"Исходная ссылка: {url}",
            instruction="Создай страницу вики на основе этой ссылки. Если доступен контент страницы, опиши его.",
        )

        title = self._extract_title(processed)
        slug = await generate_slug(title)
        auto_tags = await extract_tags(processed)
        tags = list(set(auto_tags + (user_tags or [])))

        page = WikiPage(
            slug=slug,
            title=title,
            content=processed,
            tags=tags,
            source_url=url,
            source_type="link",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        filepath = f"wiki/{page.slug}.md"
        self.github.create_or_update_file(
            path=filepath,
            content=page.to_markdown(),
            message=f"Add wiki page from link: {page.title}",
        )

        await self._update_index(page)
        return page

    async def ingest_file(
        self,
        filename: str,
        content: str,
        user_tags: list[str] | None = None,
    ) -> WikiPage:
        """Process an uploaded file and create a wiki page."""
        processed = await process_with_llm(
            content=content,
            context=f"Файл: {filename}",
            instruction="Проанализируй содержимое файла и создай страницу вики.",
        )

        title = self._extract_title(processed)
        slug = await generate_slug(title)
        auto_tags = await extract_tags(processed)
        tags = list(set(auto_tags + (user_tags or [])))

        page = WikiPage(
            slug=slug,
            title=title,
            content=processed,
            tags=tags,
            source_type="file",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        filepath = f"wiki/{page.slug}.md"
        self.github.create_or_update_file(
            path=filepath,
            content=page.to_markdown(),
            message=f"Add wiki page from file: {filename}",
        )

        await self._update_index(page)
        return page

    def get_page(self, slug: str) -> WikiPage | None:
        """Get a wiki page by slug."""
        content = self.github.get_file(f"wiki/{slug}.md")
        if content:
            return WikiPage.from_markdown(slug, content)
        return None

    def list_pages(self) -> list[str]:
        """List all wiki page slugs."""
        files = self.github.list_files("wiki")
        return [
            f.replace("wiki/", "").replace(".md", "")
            for f in files
            if f.endswith(".md") and f != "wiki/index.md"
        ]

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
        filepath = f"wiki/{slug}.md"
        return self.github.delete_file(filepath, f"Delete wiki page: {slug}")

    def search_pages(self, query: str) -> list[WikiPage]:
        """Search pages by query."""
        results = []
        for slug in self.list_pages():
            page = self.get_page(slug)
            if page and (
                query.lower() in page.title.lower()
                or query.lower() in page.content.lower()
                or query in page.tags
            ):
                results.append(page)
        return results

    async def _update_index(self, new_page: WikiPage) -> None:
        """Update the wiki index page."""
        index_content = self.github.get_file("wiki/index.md") or "# Wiki Index\n\n"

        # Add entry for new page
        tags_str = ", ".join(f"`#{t}`" for t in new_page.tags)
        entry = f"- [{new_page.title}](/{new_page.slug}.md) — {tags_str}\n"

        # Append if not already there
        if f"/{new_page.slug}.md" not in index_content:
            index_content += entry
            self.github.create_or_update_file(
                path="wiki/index.md",
                content=index_content,
                message=f"Update index: add {new_page.title}",
            )

    @staticmethod
    def _extract_title(text: str) -> str:
        """Extract title from markdown text."""
        lines = text.strip().split("\n")
        for line in lines:
            if line.startswith("# "):
                return line[2:].strip()
            if line.strip() and not line.startswith("---"):
                return line.strip()[:100]
        return "Untitled"
