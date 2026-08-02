from __future__ import annotations

import re
from pathlib import Path

from wikillm.config.settings import settings
from wikillm.core.github_wiki import GitHubWiki

# Валидный slug: строчные буквы, цифры, дефис, подчёркивание (кириллица допускается)
_SLUG_PATTERN = re.compile(r"^[a-z0-9а-яё_-]+$", re.IGNORECASE)
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_filename(slug: str) -> str:
    """Make a slug safe for use as a Windows file name."""
    return _INVALID_FILENAME_CHARS.sub("_", slug).strip().rstrip(" .")


def is_valid_slug(slug: str) -> bool:
    """True if the slug is already filesystem- and URL-safe."""
    return bool(_SLUG_PATTERN.match(slug))


class WikiStorage:
    """Local pages directory with optional GitHub sync.

    Pages live as markdown files under ``pages/``. Writes are saved
    locally and mirrored to GitHub when a repository is configured;
    reads prefer the local copy and fall back to GitHub.
    """

    def __init__(self) -> None:
        self.local_dir = settings.pages_dir
        self.local_dir.mkdir(parents=True, exist_ok=True)
        self._github: GitHubWiki | None = None

    @property
    def github(self) -> GitHubWiki | None:
        if self._github is None and settings.github_repo:
            self._github = GitHubWiki()
        return self._github

    def _path(self, slug: str) -> Path:
        return self.local_dir / f"{safe_filename(slug)}.md"

    def _github_path(self, slug: str) -> str:
        """GitHub path for a slug (mirrors the local safe filename)."""
        return f"wiki/{safe_filename(slug)}.md"

    def get_page(self, slug: str) -> str | None:
        local = self._path(slug)
        if local.exists():
            return local.read_text(encoding="utf-8")
        gh = self.github
        if gh:
            content = gh.get_file(self._github_path(slug))
            if content is not None:
                local.write_text(content, encoding="utf-8")
                return content
        return None

    def save_page(self, slug: str, content: str, message: str) -> bool:
        local = self._path(slug)
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(content, encoding="utf-8")
        gh = self.github
        if gh:
            return gh.create_or_update_file(
                path=self._github_path(slug),
                content=content,
                message=message,
            )
        return True

    def delete_page(self, slug: str, message: str) -> bool:
        local = self._path(slug)
        local_exists = local.exists()
        if local_exists:
            local.unlink()
        gh = self.github
        if gh:
            return gh.delete_file(self._github_path(slug), message)
        return True

    def page_exists(self, slug: str) -> bool:
        return self._path(slug).exists() or (
            self.github is not None
            and self.github.get_file(self._github_path(slug)) is not None
        )

    def list_pages(self) -> list[str]:
        """List page slugs from local storage and GitHub (union)."""
        local_slugs = {p.stem for p in self.local_dir.glob("*.md")}
        gh = self.github
        if gh:
            gh_slugs = {
                Path(path).stem
                for path in gh.list_files("wiki")
                if path.endswith(".md")
            }
            return sorted(local_slugs | gh_slugs)
        return sorted(local_slugs)

    def get_index(self) -> str:
        return self.get_page("index") or "# Wiki Index\n\n"

    def save_index(self, content: str, message: str) -> bool:
        return self.save_page("index", content, message)
