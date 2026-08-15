#!/usr/bin/env python3
"""Build MkDocs source from the three llmwiki-cli wikis.

1. Copies each wiki's pages into site-src/ as personal/, dev/, auto/
2. Converts [[wikilink]] and [[page|text]] to markdown links
3. Injects "Теги: ..." line into pages that have tags
4. Generates per-section tags pages, common tags page, root index, extra CSS
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


def parse_frontmatter(content: str) -> dict:
    """Crude YAML frontmatter parser for title + tags."""
    result: dict = {}
    if not content.startswith("---"):
        return result
    parts = content.split("---", 2)
    if len(parts) < 3:
        return result
    fm = parts[1]
    m = re.search(r"(?m)^title:\s*(.+)$", fm)
    if m:
        result["title"] = m.group(1).strip().strip("'\"")
    m = re.search(r"(?m)^tags:\s*\n((?:\s+-\s+[^\n]+\n?)+)", fm)
    if m:
        tags = [t.strip().lstrip("-").strip() for t in m.group(1).splitlines()]
        result["tags"] = [t for t in tags if t]
    return result


def inject_tags(content: str, tags: list[str]) -> str:
    if not tags:
        return content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content
    body = parts[2]
    tags_line = ", ".join(f"`{t}`" for t in tags)
    return f"{parts[0]}---{parts[1]}---\n> **Теги:** {tags_line}\n\n{body.lstrip()}\n"


def copy_wiki(src: Path, section: str, section_title: str) -> None:
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
            if not content.startswith("---"):
                content = f"---\ntitle: {section_title}\n---\n{content}"
            else:
                parts = content.split("---", 2)
                content = f"{parts[0]}---\ntitle: {section_title}\n---{parts[2]}"
        fm = parse_frontmatter(content)
        content = inject_tags(content, fm.get("tags", []))
        content = convert_wikilinks(content, target, link_map)
        target.write_text(content, encoding="utf-8")


def collect_section_tags(section: str) -> dict[str, list[tuple[str, str]]]:
    tags: dict[str, list[tuple[str, str]]] = {}
    for md in (OUT / section).rglob("*.md"):
        if md.name == "tags.md":
            continue
        fm = parse_frontmatter(md.read_text(encoding="utf-8"))
        if not fm.get("tags"):
            continue
        title = fm.get("title") or md.stem
        rel = md.relative_to(OUT).as_posix().replace(".md", "/")
        for tag in fm["tags"]:
            tags.setdefault(tag, []).append((rel, title))
    return tags


def build_tags_page(tags: dict[str, list[tuple[str, str]]], title: str) -> str:
    lines = [f"# {title}", ""]
    if not tags:
        lines.append("Тегов пока нет.")
        return "\n".join(lines)
    for tag in sorted(tags):
        lines.append(f"## `{tag}`")
        for rel, page_title in sorted(tags[tag], key=lambda x: x[1]):
            lines.append(f"- [{page_title}]({rel})")
        lines.append("")
    return "\n".join(lines)


def build_root_index() -> str:
    lines = ["---", "title: Главная", "---", "# База знаний", ""]
    for section, title in WIKIS.items():
        lines.append(f"- [{title}]({section}/index.md)")
    lines.append("")
    return "\n".join(lines)


SUBDIR_TITLES = {"sources": "Источники", "entities": "Люди", "concepts": "Идеи", "synthesis": "Анализ"}


def build_nav() -> list:
    nav: list = [{"Главная": "index.md"}]
    for section, title in WIKIS.items():
        pages = sorted(
            md.relative_to(OUT).as_posix()
            for md in (OUT / section).rglob("*.md")
            if md.name not in ("tags.md",)
        )
        children: list = [{"Индекс": f"{section}/index.md"}]
        for path in pages:
            if path.endswith("/index.md"):
                continue
            rel = Path(path)
            sub = rel.parent.name
            label = SUBDIR_TITLES.get(sub, sub.capitalize())
            children.append({label: path})
        children.append({"Теги": f"{section}/tags.md"})
        nav.append({title: children})
    return nav


def write_nav_to_mkdocs(nav: list) -> None:
    import yaml

    cfg_path = ROOT / "mkdocs.yml"
    cfg = cfg_path.read_text(encoding="utf-8")
    nav_yaml = yaml.safe_dump(nav, allow_unicode=True, sort_keys=False, default_flow_style=False)
    block = "nav:\n" + nav_yaml
    if re.search(r"(?m)^nav:\n", cfg):
        cfg = re.sub(r"(?m)^nav:\n(?:[ \t].*\n?)*", block + "\n", cfg, count=1)
    else:
        cfg = cfg.rstrip() + "\n\n" + block
    cfg_path.write_text(cfg, encoding="utf-8")


def build_extra_css() -> str:
    return (
        "/* Section headers in the sidebar: distinct, smaller, uppercase */\n"
        ".md-nav__item--section > .md-nav__link .md-ellipsis {\n"
        "  font-size: .68rem !important;\n"
        "  text-transform: uppercase;\n"
        "  letter-spacing: .06em;\n"
        "  opacity: .6;\n"
        "}\n"
    )


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    for section, title in WIKIS.items():
        wiki_src = ROOT / section / "wiki"
        if wiki_src.exists():
            copy_wiki(wiki_src, section, title)
        else:
            (OUT / section).mkdir(parents=True, exist_ok=True)

    common_tags: dict[str, list[tuple[str, str]]] = {}
    for section, title in WIKIS.items():
        section_tags = collect_section_tags(section)
        (OUT / section / "tags.md").write_text(
            build_tags_page(section_tags, f"Теги: {title}"), encoding="utf-8"
        )
        for tag, pages in section_tags.items():
            common_tags.setdefault(tag, []).extend(pages)

    (OUT / "tags.md").write_text(
        build_tags_page(common_tags, "Все теги"), encoding="utf-8"
    )
    (OUT / "index.md").write_text(build_root_index(), encoding="utf-8")
    (OUT / "extra.css").write_text(build_extra_css(), encoding="utf-8")
    write_nav_to_mkdocs(build_nav())
    print(f"Site source built in {OUT}")


if __name__ == "__main__":
    main()
