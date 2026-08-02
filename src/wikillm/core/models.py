from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime

from wikillm.core.logger import logger


def _parse_datetime(value: str, fallback: datetime) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        logger.warning(f"  невалидная дата во frontmatter: {value!r}")
        return fallback


@dataclass
class WikiPage:
    """A single page in the wiki."""

    slug: str
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    source_url: str | None = None
    source_type: str = "text"  # text, link, file
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_markdown(self) -> str:
        tags_json = json.dumps(self.tags, ensure_ascii=False)
        frontmatter = f"""---
title: {json.dumps(self.title, ensure_ascii=False)}
tags: {tags_json}
source_url: {json.dumps(self.source_url or '', ensure_ascii=False)}
source_type: {json.dumps(self.source_type, ensure_ascii=False)}
created_at: "{self.created_at.isoformat()}"
updated_at: "{self.updated_at.isoformat()}"
---

"""
        return frontmatter + self.content

    @classmethod
    def from_markdown(cls, slug: str, markdown: str) -> WikiPage:
        """Parse a markdown file with frontmatter into a WikiPage."""
        if not markdown.startswith("---"):
            return cls(slug=slug, title=slug, content=markdown.strip())

        end = markdown.find("---", 3)
        if end == -1:
            return cls(slug=slug, title=slug, content=markdown.strip())

        frontmatter = markdown[3:end].strip()
        content = markdown[end + 3 :].strip()
        metadata = cls._parse_frontmatter(frontmatter)

        return cls(
            slug=slug,
            title=metadata.get("title") or slug,
            content=content,
            tags=metadata.get("tags") or [],
            source_url=metadata.get("source_url"),
            source_type=metadata.get("source_type") or "text",
            created_at=_parse_datetime(
                metadata.get("created_at", ""),
                datetime.now(),
            ),
            updated_at=_parse_datetime(
                metadata.get("updated_at", ""),
                datetime.now(),
            ),
        )

    @staticmethod
    def _parse_frontmatter(frontmatter: str) -> dict:
        """Parse YAML-ish frontmatter.

        Supports scalar values, quoted strings and JSON arrays.
        Falls back to a simple key: value split otherwise.
        """
        result: dict = {}
        for line in frontmatter.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if not key:
                continue

            if value.startswith("["):
                try:
                    result[key] = json.loads(value)
                except json.JSONDecodeError:
                    result[key] = [
                        v.strip().strip('"') for v in value[1:-1].split(",") if v.strip()
                    ]
            elif value.startswith('"'):
                try:
                    result[key] = json.loads(value)
                except json.JSONDecodeError:
                    result[key] = value[1:-1]
            else:
                result[key] = value
        return result
