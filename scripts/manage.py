#!/usr/bin/env python3
"""Unified wiki management script.

Usage:
    python manage.py add <file_or_url> --wiki <name> [--section sources] [--dry-run]
    python manage.py delete <page_path> --wiki <name>
    python manage.py tags [--wiki <name>]
    python manage.py status [--wiki <name>]
    python manage.py commit [-m "message"]
    python manage.py push
    python manage.py sync [-m "message"]  # commit + push + rebuild
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent

OMNIRoute_URL = "http://localhost:20128/v1/chat/completions"
OMNIRoute_KEY = "sk_omniroute"
MODEL = "auto/best-fast"

ANALYZE_PROMPT = """Analyze the text below. Return ONLY valid JSON, no prose.
{"title":"Short Russian title (max 10 words)",
 "tags":["tag1","tag2","tag3"],
 "summary":"2-4 Russian sentences",
 "content":"Full note text with [[wikilinks]]"}
Rules:
- all output in Russian (except tech terms: android, kotlin, api, ios, python)
- tags: 3-7, ALWAYS lowercase, hyphens instead of spaces, NO spaces, e.g. #android-studio, #мой-тег
- content: use [[wikilinks]], headers (##), preserve key info
- title: short, descriptive, in Russian"""

WIKIS = {
    "Личное": "personal",
    "Разработка": "dev",
    "Автомобили": "auto",
}

SECTIONS = {
    "sources": "Источники",
    "entities": "Люди",
    "concepts": "Идеи",
    "synthesis": "Анализ",
}


def normalize_tag(tag: str) -> str:
    """Normalize tag to lowercase-hyphenated format."""
    tag = tag.lower().strip().lstrip("#")
    tag = re.sub(r"[\s_]+", "-", tag)
    tag = re.sub(r"[^a-zа-я0-9\-]", "", tag)
    tag = re.sub(r"-+", "-", tag).strip("-")
    return tag


def slug_from_title(title: str) -> str:
    """Create a kebab-case slug from a title."""
    translit = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e",
        "ё": "yo", "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k",
        "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
        "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
        "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "",
        "э": "e", "ю": "yu", "я": "ya",
    }
    slug = title.lower()
    result = []
    for ch in slug:
        if ch in translit:
            result.append(translit[ch])
        elif ch.isalnum() or ch == "-":
            result.append(ch)
        elif ch in (" ", "_"):
            result.append("-")
    slug = "".join(result)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:60] or "page"


# ── Text extraction ──────────────────────────────────────────────────────


def extract_from_url(url: str) -> str:
    import trafilatura

    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        print(f"Failed to download: {url}", file=sys.stderr)
        sys.exit(1)
    text = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
    if not text:
        print(f"Failed to extract text from: {url}", file=sys.stderr)
        sys.exit(1)
    return text


def extract_from_pdf(path: str) -> str:
    from pypdf import PdfReader

    reader = PdfReader(path)
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(pages).strip()
    if not text:
        print(f"Failed to extract text from: {path}", file=sys.stderr)
        sys.exit(1)
    return text


def extract_from_docx(path: str) -> str:
    from docx import Document

    doc = Document(path)
    text = "\n\n".join(para.text for para in doc.paragraphs if para.text.strip())
    if not text:
        print(f"Failed to extract text from: {path}", file=sys.stderr)
        sys.exit(1)
    return text


def extract_text(source: str) -> str:
    if source.startswith("http://") or source.startswith("https://"):
        return extract_from_url(source)
    path = Path(source)
    if not path.exists():
        print(f"File not found: {source}", file=sys.stderr)
        sys.exit(1)
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_from_pdf(str(path))
    elif ext in (".docx", ".doc"):
        return extract_from_docx(str(path))
    return path.read_text(encoding="utf-8", errors="replace")


def analyze_with_llm(text: str, source: str) -> dict:
    if len(text) > 15000:
        text = text[:15000] + "\n\n[... truncated ...]"

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": ANALYZE_PROMPT},
            {"role": "user", "content": f"Source: {source}\n\nText:\n{text}"},
        ],
        "temperature": 0.3,
        "max_tokens": 4000,
    }

    headers = {
        "Authorization": f"Bearer {OMNIRoute_KEY}",
        "Content-Type": "application/json",
    }

    print("Analyzing with LLM...", file=sys.stderr)
    resp = requests.post(OMNIRoute_URL, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()

    content = resp.json()["choices"][0]["message"]["content"].strip()
    json_match = re.search(r"\{[\s\S]*\}", content)
    if not json_match:
        print(f"LLM did not return JSON:\n{content}", file=sys.stderr)
        sys.exit(1)

    result = json.loads(json_match.group())
    for key in ("title", "tags", "content"):
        if key not in result:
            print(f"Missing required field: {key}", file=sys.stderr)
            sys.exit(1)

    result["tags"] = [normalize_tag(t) for t in result["tags"]]
    return result


# ── Commands ─────────────────────────────────────────────────────────────


def cmd_add(args):
    """Add a source to wiki via LLM."""
    print(f"Extracting text from: {args.source}", file=sys.stderr)
    text = extract_text(args.source)
    print(f"Extracted {len(text)} characters", file=sys.stderr)

    result = analyze_with_llm(text, args.source)

    slug = args.slug or slug_from_title(result["title"])
    page_path = f"wiki/{args.section}/{slug}.md"

    wiki_json = {
        "title": result["title"],
        "tags": result["tags"],
        "content": result["content"],
    }
    if args.source.startswith("http"):
        wiki_json["source"] = args.source

    print(f"\nTitle: {result['title']}", file=sys.stderr)
    print(f"Tags:  #{'  #'.join(result['tags'])}", file=sys.stderr)
    print(f"Path:  {page_path}", file=sys.stderr)

    if args.dry_run:
        print(json.dumps(wiki_json, ensure_ascii=False, indent=2))
        return

    proc = subprocess.run(
        ["wiki", "--wiki", args.wiki, "write", page_path],
        input=json.dumps(wiki_json, ensure_ascii=False),
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(f"Error: {proc.stderr}", file=sys.stderr)
        sys.exit(1)

    print(f"Written to: {page_path}", file=sys.stderr)
    print("Done!", file=sys.stderr)


def cmd_delete(args):
    """Delete a page from wiki."""
    proc = subprocess.run(
        ["wiki", "--wiki", args.wiki, "delete", args.path],
        capture_output=True, text=True,
    )
    print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")
    if proc.returncode != 0:
        sys.exit(1)


def cmd_wikis(args):
    """List wikis and page counts."""
    for wiki_name, folder in WIKIS.items():
        wiki_dir = ROOT / "wikis" / folder / "wiki"
        if not wiki_dir.exists():
            print(f"  {wiki_name}  (пустая)")
            continue
        count = sum(1 for p in wiki_dir.rglob("*.md") if p.name != "index.md")
        print(f"  {wiki_name}  ({count} стр.)")


def cmd_tags(args):
    """List all tags across wikis."""
    import yaml

    wikis = [args.wiki] if args.wiki else list(WIKIS.keys())
    all_tags: dict[str, list[str]] = {}

    for wiki_name in wikis:
        wiki_dir = ROOT / "wikis" / WIKIS[wiki_name] / "wiki"
        if not wiki_dir.exists():
            continue
        for md in wiki_dir.rglob("*.md"):
            if md.name == "index.md":
                continue
            content = md.read_text(encoding="utf-8")
            if not content.startswith("---"):
                continue
            parts = content.split("---", 2)
            if len(parts) < 3:
                continue
            try:
                fm = yaml.safe_load(parts[1])
            except Exception:
                continue
            if not fm or "tags" not in fm:
                continue
            for tag in fm["tags"]:
                tag = normalize_tag(tag)
                all_tags.setdefault(tag, []).append(f"{wiki_name}/{md.stem}")

    if not all_tags:
        print("No tags found.")
        return

    for tag in sorted(all_tags.keys()):
        pages = ", ".join(all_tags[tag])
        print(f"  #{tag}  ({pages})")


def cmd_tagdel(args):
    """Remove a tag from all pages (rewrites frontmatter)."""
    import yaml

    target = normalize_tag(args.tag)
    wikis = [args.wiki] if args.wiki else list(WIKIS.keys())
    changed = 0

    for wiki_name in wikis:
        wiki_dir = ROOT / "wikis" / WIKIS[wiki_name] / "wiki"
        if not wiki_dir.exists():
            continue
        for md in wiki_dir.rglob("*.md"):
            if md.name == "index.md":
                continue
            content = md.read_text(encoding="utf-8")
            if not content.startswith("---"):
                continue
            parts = content.split("---", 2)
            if len(parts) < 3:
                continue
            try:
                fm = yaml.safe_load(parts[1])
            except Exception:
                continue
            if not fm or "tags" not in fm or not isinstance(fm["tags"], list):
                continue
            kept = [t for t in fm["tags"] if normalize_tag(t) != target]
            if len(kept) == len(fm["tags"]):
                continue
            fm["tags"] = kept
            new_fm = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
            md.write_text(f"---\n{new_fm}\n---{parts[2]}", encoding="utf-8")
            changed += 1
            print(f"  #{target}: {wiki_name}/{md.stem}", file=sys.stderr)

    if changed:
        print(f"Removed #{target} from {changed} page(s).")
    else:
        print(f"Tag #{target} not found.")


def cmd_status(args):
    """Show wiki status."""
    wikis = [args.wiki] if args.wiki else list(WIKIS.keys())
    for wiki_name in wikis:
        proc = subprocess.run(
            ["wiki", "--wiki", wiki_name, "status"],
            capture_output=True, text=True,
        )
        print(proc.stdout, end="")


def cmd_commit(args):
    """Git commit all changes."""
    msg = args.message or "wiki: обновление"
    proc = subprocess.run(
        ["git", "add", "-A"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    proc = subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")


def cmd_push(args):
    """Git push."""
    proc = subprocess.run(
        ["git", "push"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")


def cmd_sync(args):
    """Commit + push + rebuild site."""
    msg = args.message or "wiki: обновление"
    subprocess.run(["git", "add", "-A"], cwd=str(ROOT))
    subprocess.run(["git", "commit", "-m", msg], cwd=str(ROOT))
    subprocess.run(["git", "push"], cwd=str(ROOT))
    subprocess.run([sys.executable, str(SCRIPTS / "build_site.py")])
    subprocess.run([sys.executable, "-m", "mkdocs", "build", "--site-dir", "dist"], cwd=str(ROOT))
    print("Synced: committed, pushed, site rebuilt.", file=sys.stderr)


# ── CLI ──────────────────────────────────────────────────────────────────


class WideHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Linux-style help: option + args on one line, wrapped help text."""

    def _format_action_invocation(self, action):
        if not action.option_strings:
            return action.dest.upper()
        return " ".join(action.option_strings)


def add_wiki_arg(parser):
    parser.add_argument(
        "--wiki",
        required=True,
        choices=list(WIKIS.keys()),
        metavar="WIKI",
        help="имя вики: " + ", ".join(WIKIS.keys()),
    )


def main():
    parser = argparse.ArgumentParser(
        prog="manage",
        description="Инструмент управления базой знаний",
        epilog="Примеры:\n"
        "  manage add https://example.com --wiki Разработка\n"
        "  manage --tags --wiki Личное\n"
        "  manage tags --wiki Личное\n"
        "  manage sync -m \"добавил статью\"",
        formatter_class=WideHelpFormatter,
    )
    parser.add_argument(
        "--tags", action="store_true",
        help="вывести теги (можно вместо подкоманды tags)",
    )
    parser.add_argument(
        "--wikis", action="store_true",
        help="вывести список вики (можно вместо подкоманды wikis)",
    )
    parser.add_argument(
        "--wiki", choices=list(WIKIS.keys()), metavar="WIKI",
        help="имя вики: " + ", ".join(WIKIS.keys()),
    )
    sub = parser.add_subparsers(dest="command", metavar="КОМАНДА")

    # add
    p_add = sub.add_parser("add", help="добавить контент в вики через LLM", formatter_class=WideHelpFormatter)
    p_add.add_argument("source", metavar="ИСТОЧНИК", help="файл или URL для обработки")
    add_wiki_arg(p_add)
    p_add.add_argument(
        "--section",
        default="sources",
        choices=list(SECTIONS.keys()),
        metavar="СЕКЦИЯ",
        help="секция вики: " + ", ".join(SECTIONS.keys()) + " (по умолчанию: sources)",
    )
    p_add.add_argument("--slug", metavar="ИМЯ", help="имя файла страницы (по умолчанию из заголовка)")
    p_add.add_argument("--dry-run", action="store_true", help="показать результат без записи")

    # delete
    p_del = sub.add_parser("delete", help="удалить страницу из вики", formatter_class=WideHelpFormatter)
    p_del.add_argument("path", metavar="ПУТЬ", help="путь страницы относительно корня вики")
    add_wiki_arg(p_del)

    # tags
    p_tags = sub.add_parser("tags", help="вывести все теги", formatter_class=WideHelpFormatter)
    p_tags.add_argument("--wiki", choices=list(WIKIS.keys()), metavar="WIKI", help="только для указанной вики")

    # wikis
    sub.add_parser("wikis", help="вывести список вики", formatter_class=WideHelpFormatter)

    # tagdel
    p_tagdel = sub.add_parser("tagdel", help="удалить тег из всех страниц", formatter_class=WideHelpFormatter)
    p_tagdel.add_argument("tag", metavar="ТЕГ", help="тег для удаления (без #)")
    p_tagdel.add_argument("--wiki", choices=list(WIKIS.keys()), metavar="WIKI", help="только для указанной вики")

    # status
    p_status = sub.add_parser("status", help="показать состояние вики", formatter_class=WideHelpFormatter)
    p_status.add_argument("--wiki", choices=list(WIKIS.keys()), metavar="WIKI", help="только для указанной вики")

    # commit
    p_commit = sub.add_parser("commit", help="закоммитить изменения (git)", formatter_class=WideHelpFormatter)
    p_commit.add_argument("-m", "--message", metavar="СООБЩЕНИЕ", help="сообщение коммита")

    # push
    sub.add_parser("push", help="запушить изменения (git)", formatter_class=WideHelpFormatter)

    # sync
    p_sync = sub.add_parser("sync", help="коммит + пуш + пересборка сайта", formatter_class=WideHelpFormatter)
    p_sync.add_argument("-m", "--message", metavar="СООБЩЕНИЕ", help="сообщение коммита")

    args = parser.parse_args()

    commands = {
        "add": cmd_add,
        "delete": cmd_delete,
        "tags": cmd_tags,
        "tagdel": cmd_tagdel,
        "wikis": cmd_wikis,
        "status": cmd_status,
        "commit": cmd_commit,
        "push": cmd_push,
        "sync": cmd_sync,
    }
    if args.command:
        commands[args.command](args)
    elif args.tags:
        cmd_tags(args)
    elif args.wikis:
        cmd_wikis(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
