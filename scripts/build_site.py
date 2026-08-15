#!/usr/bin/env python3
"""Build MkDocs source from the three llmwiki-cli wikis.

1. Copies each wiki's pages into site-src/ as personal/, dev/, auto/
2. Converts [[wikilink]] and [[page|text]] to markdown links
3. Generates the root index.md
"""

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKIS = {"personal": "Личное", "dev": "Разработка", "auto": "Автомобили"}
OUT = ROOT / "site-src"

WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def build_link_map(src: Path, section: str) -> dict[str, Path]:
    """Aliases (stem, relative path, with/without .md) -> output file path."""
    mapping: dict[str, Path] = {}
    for md in src.rglob("*.md"):
        rel = md.relative_to(src).with_suffix("")
        target = OUT / section / rel.with_suffix(".md")
        mapping[md.stem] = target
        mapping[rel.as_posix()] = target
        mapping[md.name] = target
        mapping[f"{rel.as_posix()}.md"] = target
        mapping[f"wiki/{rel.as_posix()}"] = target
        mapping[f"wiki/{rel.as_posix()}.md"] = target
    return mapping


def convert_wikilinks(content: str, page_path: Path, link_map: dict) -> str:
    def repl(match: re.Match) -> str:
        target = match.group(1).strip()
        text = (match.group(2) or target).strip()
        link = link_map.get(target)
        if link is None:
            return f"`{target}`"
        rel = link.resolve().relative_to(page_path.parent.resolve())
        rel = rel.as_posix().replace(".md", "/")
        return f"[{text}]({rel})"

    return WIKILINK_RE.sub(repl, content)


def copy_wiki(src: Path, section: str) -> None:
    dst = OUT / section
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True, exist_ok=True)
    link_map = build_link_map(src, section)
    for md in src.rglob("*.md"):
        rel = md.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        content = md.read_text(encoding="utf-8")
        if md.name == "index.md":
            content = content.replace("# Index", "# Индекс", 1)
        content = convert_wikilinks(content, target, link_map)
        target.write_text(content, encoding="utf-8")


def build_root_index() -> str:
    lines = ["# База знаний", ""]
    for section, title in WIKIS.items():
        lines.append(f"## [{title}]({section}/index.md)")
        index = OUT / section / "index.md"
        if index.exists():
            for line in index.read_text(encoding="utf-8").splitlines():
                if line.startswith("- [") and "wiki/" not in line:
                    lines.append(f"  {line}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    for section, _title in WIKIS.items():
        wiki_src = ROOT / section / "wiki"
        if wiki_src.exists():
            copy_wiki(wiki_src, section)
        else:
            (OUT / section).mkdir(parents=True, exist_ok=True)
    (OUT / "index.md").write_text(build_root_index(), encoding="utf-8")
    print(f"Site source built in {OUT}")


if __name__ == "__main__":
    main()
