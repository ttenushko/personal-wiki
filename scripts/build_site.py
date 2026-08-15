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
WIKI_ROOT = ROOT / "wikis"
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
    m = re.search(r"(?m)^tags:\s*\n((?:[ \t]*-[ \t]+[^\n]+\n?)+)", fm)
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
    return f"{parts[0]}---{parts[1]}---\n<div data-search-exclude>**Теги:** {tags_line}</div>\n\n{body.lstrip()}\n"


SUBDIR_TITLES = {"sources": "Источники", "entities": "Люди", "concepts": "Идеи", "synthesis": "Анализ"}
SECTION_HEADINGS = {
    "sources": "Источники",
    "entities": "Люди",
    "concepts": "Идеи",
    "synthesis": "Анализ",
}


SEARCH_BOX_HTML = (
    '<div class="isearch">\n'
    '  <input type="search" class="isearch__input" '
    'data-isearch placeholder="Поиск по базе знаний…" '
    'aria-label="Поиск по базе знаний">\n'
    '  <div class="isearch__results" data-isearch-results></div>\n'
    '</div>\n'
)


def inject_search_box(content: str, wiki: str | None = None) -> str:
    """Insert the inline search box right after the first H1 (or after frontmatter)."""
    box = SEARCH_BOX_HTML
    if wiki:
        box = box.replace('<div class="isearch">', f'<div class="isearch" data-wiki="{wiki}">')
    m = re.search(r"(?m)^#\s[^\n]*\n", content)
    if m:
        return content[: m.end()] + "\n" + box + content[m.end():]
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[0] + "---" + parts[1] + "---" + "\n" + box + parts[2]
    return content + "\n" + box


def ensure_frontmatter(content: str, extra_lines: list[str]) -> str:
    """Ensure content has YAML frontmatter; merge extra_lines into it, preserving existing keys."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1].rstrip("\n").lstrip("\n")
            extra = [ln for ln in extra_lines if ln not in fm]
            merged = fm + ("\n" if fm else "") + "\n".join(extra)
            return f"---\n{merged}\n---{parts[2]}"
    head = "\n".join(extra_lines) + "\n"
    return f"---\n{head}---\n{content}"


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
            content = f"---\ntitle: {section_title}\n---\n# {section_title}\n"
            content = inject_search_box(content, wiki=section)
            target.write_text(content, encoding="utf-8")
            continue
        else:
            content = ensure_frontmatter(content, ["not_in_nav: true"])
        fm = parse_frontmatter(content)
        content = inject_tags(content, fm.get("tags", []))
        content = convert_wikilinks(content, target, link_map)
        content = inject_search_box(content, wiki=section)
        target.write_text(content, encoding="utf-8")


def normalize_tag(tag: str) -> str:
    """Normalize tag to lowercase-hyphenated format."""
    tag = tag.lower().strip().lstrip("#")
    tag = re.sub(r"[\s_]+", "-", tag)
    tag = re.sub(r"[^a-zа-я0-9\-]", "", tag)
    tag = re.sub(r"-+", "-", tag).strip("-")
    return tag


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
            tags.setdefault(normalize_tag(tag), []).append((rel, title))
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
    lines = ["---", "title: Главная", "---", "# Главная", ""]
    return inject_search_box("\n".join(lines))


def build_tags_data() -> str:
    """Generate window.WIKI_TAGS = {all: [...], personal: [...], dev: [...], auto: [...]}."""
    per_section: dict[str, set[str]] = {}
    for section, _title in WIKIS.items():
        per_section[section] = set(collect_section_tags(section).keys())
    all_tags = sorted({t for tags in per_section.values() for t in tags})
    data = {"all": all_tags, "names": dict(WIKIS)}
    for section, tags in per_section.items():
        data[section] = sorted(tags)
    import json

    return "window.WIKI_TAGS = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"


def build_nav() -> list:
    nav: list = [{"Главная": "index.md"}]
    for section, title in WIKIS.items():
        nav.append({title: f"{section}/index.md"})
    return nav


def write_nav_to_mkdocs(nav: list) -> None:
    import yaml

    cfg_path = ROOT / "mkdocs.yml"
    cfg = cfg_path.read_text(encoding="utf-8")
    nav_yaml = yaml.safe_dump(nav, allow_unicode=True, sort_keys=False, default_flow_style=False)
    block = "nav:\n" + nav_yaml
    idx = cfg.find("\nnav:\n")
    if idx >= 0:
        cfg = cfg[: idx + 1].rstrip() + "\n\n" + block
    else:
        cfg = cfg.rstrip() + "\n\n" + block
    cfg_path.write_text(cfg, encoding="utf-8")


def build_extra_css() -> str:
    return (
        "/* ---- Obsidian-style layout ---- */\n\n"
        "/* Hide the top header entirely */\n"
        ".md-header { display: none !important; }\n\n"
        "/* Hide empty footer (no copyright) */\n"
        ".md-footer { display: none !important; }\n\n"
        "/* ---- Left/right sidebars: equal width in % ---- */\n"
        ".md-sidebar--primary { top: 0 !important; width: 14% !important; }\n"
        ".md-sidebar--secondary { top: 0 !important; width: 14% !important; }\n"
        "/* Screen edge margins and gaps between panels */\n"
        ".md-grid { max-width: none !important; padding-left: 2rem !important; padding-right: 2rem !important; }\n"
        ".md-content__inner { margin-left: 2rem !important; margin-right: 2rem !important; }\n"
        ".md-sidebar__inner { padding: 1rem .2rem 2rem; }\n"
        "/* Sidebar brand: show title, hide the logo image */\n"
        ".md-nav__title { font-size: 1.05rem !important; font-weight: 700 !important; }\n"
        ".md-nav--primary > .md-nav__title { color: var(--md-default-fg-color) !important; }\n"
        ".md-nav__button.md-logo { display: none !important; }\n"
        "/* Theme switch (sun/moon icon) under the title */\n"
        ".theme-switch {\n"
        "  display: inline-flex;\n"
        "  align-items: center;\n"
        "  justify-content: center;\n"
        "  width: 2rem;\n"
        "  height: 2rem;\n"
        "  margin: .4rem 0 .9rem .2rem;\n"
        "  padding: 0;\n"
        "  border: none;\n"
        "  border-radius: 6px;\n"
        "  background: transparent;\n"
        "  color: var(--md-default-fg-color--light);\n"
        "  cursor: pointer;\n"
        "}\n"
        ".theme-switch:hover {\n"
        "  background: var(--md-default-fg-color--lightest);\n"
        "  color: var(--md-default-fg-color);\n"
        "}\n"
        ".theme-switch__icon { display: inline-flex; }\n"
        "/* Separate the first nav item (Главная) from the wikis */\n"
        ".md-nav--primary > .md-nav__list > .md-nav__item:first-child {\n"
        "  margin-bottom: .8rem;\n"
        "  padding-bottom: .8rem;\n"
        "  border-bottom: 1px solid var(--md-default-fg-color--lightest);\n"
        "}\n"
        ".md-nav__link { padding: .35rem .6rem; }\n\n"
        "/* ---- Right sidebar: tags panel ---- */\n"
        ".md-sidebar--secondary .md-nav--secondary { display: none !important; }\n"
        ".tags-panel { display: flex; flex-wrap: wrap; gap: .3rem; }\n"
        ".tag-chip {\n"
        "  display: inline-block;\n"
        "  padding: .15rem .5rem;\n"
        "  font-size: .75rem;\n"
        "  border-radius: 999px;\n"
        "  border: 1px solid var(--md-primary-fg-color);\n"
        "  color: var(--md-primary-fg-color);\n"
        "  background: none;\n"
        "  cursor: pointer;\n"
        "  font: inherit;\n"
        "}\n"
        ".tag-chip:hover {\n"
        "  background: var(--md-primary-fg-color);\n"
        "  color: var(--md-default-bg-color);\n"
        "}\n\n"
        "/* ---- Inline search block ---- */\n"
        ".isearch { margin: 0 0 1.5rem; }\n"
        ".isearch__input {\n"
        "  width: 100%;\n"
        "  padding: .65rem 1rem;\n"
        "  font-size: .95rem;\n"
        "  border: 1px solid var(--md-default-fg-color--lightest);\n"
        "  border-radius: 4px;\n"
        "  background: var(--md-default-bg-color);\n"
        "  color: var(--md-typeset-color);\n"
        "}\n"
        ".isearch__input:focus { outline: none; border-color: var(--md-primary-fg-color); }\n"
        ".isearch__results { margin-top: .5rem; }\n"
        ".isearch-item {\n"
        "  display: block;\n"
        "  padding: .55rem .75rem;\n"
        "  border-left: 2px solid var(--md-primary-fg-color);\n"
        "  border-radius: 0 4px 4px 0;\n"
        "  text-decoration: none;\n"
        "}\n"
        ".isearch-item:hover { background: var(--md-default-fg-color--lightest); }\n"
        ".isearch-item__title { font-weight: 600; }\n"
        ".isearch-item__snippet { font-size: .85rem; opacity: .75; }\n"
        ".isearch-empty { opacity: .7; font-style: italic; }\n"
    )


def update_mkdocs_assets(css_name: str, js_names: list[str]) -> None:
    """Rewrite extra_css / extra_javascript blocks in mkdocs.yml."""
    cfg_path = ROOT / "mkdocs.yml"
    cfg = cfg_path.read_text(encoding="utf-8")
    # Replace or append extra_css
    if re.search(r"(?m)^extra_css:\n", cfg):
        cfg = re.sub(
            r"(?m)^extra_css:\n(?:[ \t]+-[^\n]*\n?)*",
            "extra_css:\n  - " + css_name + "\n",
            cfg,
            count=1,
        )
    else:
        cfg = cfg.rstrip() + "\n\nextra_css:\n  - " + css_name + "\n"
    # Replace or insert extra_javascript (before nav)
    js_block = "extra_javascript:\n" + "".join(f"  - {n}\n" for n in js_names)
    if re.search(r"(?m)^extra_javascript:\n", cfg):
        cfg = re.sub(
            r"(?m)^extra_javascript:\n(?:[ \t]+-[^\n]*\n?)*",
            js_block,
            cfg,
            count=1,
        )
    else:
        # Insert before nav: block
        nav_idx = cfg.find("\nnav:\n")
        if nav_idx >= 0:
            cfg = cfg[: nav_idx] + "\n\n" + js_block + "\n" + cfg[nav_idx:]
        else:
            cfg = cfg.rstrip() + "\n" + js_block + "\n"
    cfg_path.write_text(cfg, encoding="utf-8")


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    for section, title in WIKIS.items():
        wiki_src = WIKI_ROOT / section / "wiki"
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

    import hashlib

    css = build_extra_css()
    css_hash = hashlib.md5(css.encode("utf-8")).hexdigest()[:8]
    css_name = f"extra.{css_hash}.css"
    (OUT / css_name).write_text(css, encoding="utf-8")

    js_content = (ROOT / "scripts" / "inline-search.js").read_text(encoding="utf-8")
    js_hash = hashlib.md5(js_content.encode("utf-8")).hexdigest()[:8]
    js_name = f"inline-search.{js_hash}.js"
    (OUT / js_name).write_text(js_content, encoding="utf-8")

    tags_data = build_tags_data()
    tags_hash = hashlib.md5(tags_data.encode("utf-8")).hexdigest()[:8]
    tags_name = f"tags-data.{tags_hash}.js"
    (OUT / tags_name).write_text(tags_data, encoding="utf-8")

    update_mkdocs_assets(css_name, [js_name, tags_name])
    write_nav_to_mkdocs(build_nav())
    print(f"Site source built in {OUT}")


if __name__ == "__main__":
    main()
