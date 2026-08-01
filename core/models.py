from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


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

    @property
    def filepath(self) -> Path:
        return Path(f"{self.slug}.md")

    def to_markdown(self) -> str:
        tags_str = ", ".join(self.tags)
        frontmatter = f"""---
title: "{self.title}"
tags: [{tags_str}]
source_url: "{self.source_url or ''}"
source_type: "{self.source_type}"
created_at: "{self.created_at.isoformat()}"
updated_at: "{self.updated_at.isoformat()}"
---

"""
        return frontmatter + self.content

    @classmethod
    def from_markdown(cls, slug: str, markdown: str) -> WikiPage:
        """Parse a markdown file with frontmatter into a WikiPage."""
        if markdown.startswith("---"):
            end = markdown.find("---", 3)
            if end != -1:
                frontmatter = markdown[3:end].strip()
                content = markdown[end + 3 :].strip()
                metadata = cls._parse_frontmatter(frontmatter)
                return cls(
                    slug=slug,
                    title=metadata.get("title", slug),
                    content=content,
                    tags=metadata.get("tags", []),
                    source_url=metadata.get("source_url"),
                    source_type=metadata.get("source_type", "text"),
                    created_at=datetime.fromisoformat(metadata["created_at"])
                    if "created_at" in metadata
                    else datetime.now(),
                    updated_at=datetime.fromisoformat(metadata["updated_at"])
                    if "updated_at" in metadata
                    else datetime.now(),
                )
        return cls(slug=slug, title=slug, content=markdown)

    @staticmethod
    def _parse_frontmatter(frontmatter: str) -> dict:
        result: dict = {}
        for line in frontmatter.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if value.startswith("[") and value.endswith("]"):
                    value = [v.strip().strip('"') for v in value[1:-1].split(",")]
                elif value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                result[key] = value
        return result
