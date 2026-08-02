from __future__ import annotations

import argparse
import asyncio
import re
import sys

from wikillm.core.logger import logger
from wikillm.core.site_builder import SiteBuilder
from wikillm.core.wiki_manager import WikiManager

URL_RE = re.compile(r"https?://\S+")


def parse_tags(args: list[str]) -> list[str]:
    """Parse tag arguments: #tag1, #'tag 2', #"tag #3". Raises ValueError on bad input."""
    tags = []
    for arg in args:
        if not arg.startswith("#"):
            raise ValueError(f'Не понятно: "{arg}" (ожидался тег вида #tag, #\'tag 2\', #"tag #3")')
        tag = arg[1:]
        if not tag:
            raise ValueError("Пустой тег: #")
        if tag[0] in "'\"":
            if len(tag) < 2 or tag[-1] != tag[0]:
                raise ValueError(f"Несогласованные кавычки в теге: {arg}")
            tag = tag[1:-1]
            if not tag.strip():
                raise ValueError(f"Пустой тег: {arg}")
        tags.append(tag)
    return tags


def main() -> None:
    parser = argparse.ArgumentParser(prog="wiki", description="Personal Wiki CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List pages
    subparsers.add_parser("pages", help="List all pages")

    # List tags
    subparsers.add_parser("tags", help="List all tags")

    # Search
    search_parser = subparsers.add_parser("search", help="Search pages")
    search_parser.add_argument("query", help="Search query")

    # Get page
    get_parser = subparsers.add_parser("get", help="Get page content")
    get_parser.add_argument("slug", help="Page slug")

    # Delete page
    del_parser = subparsers.add_parser("delete", help="Delete page")
    del_parser.add_argument("slug", help="Page slug")

    # Add content
    add_parser = subparsers.add_parser("add", help="Add text/link/file to wiki")
    add_parser.add_argument(
        "text",
        help="Text or link to add",
    )
    add_parser.add_argument(
        "tags",
        nargs="*",
        metavar="TAG",
        help='Tags: #tag1 or #\'tag 2\' or #"tag #3"',
    )

    # Build static site
    subparsers.add_parser("build", help="Build static HTML site")

    # Open site in browser
    subparsers.add_parser("open", help="Build and open the site in browser")

    args = parser.parse_args()
    wiki = WikiManager()

    if args.command == "pages":
        pages = wiki.list_pages()
        if not pages:
            print("Страниц пока нет.")
        for slug in pages:
            page = wiki.get_page(slug)
            if page:
                tags = ", ".join(f"#{t}" for t in page.tags)
                print(f"  {page.title} ({tags})")

    elif args.command == "tags":
        tags = wiki.list_tags()
        if not tags:
            print("Тегов пока нет.")
        for tag, count in tags.items():
            print(f"  #{tag} — {count} стр.")

    elif args.command == "search":
        results = wiki.search_pages(args.query)
        if not results:
            print(f"Ничего не найдено по запросу: {args.query}")
        for page in results:
            tags = ", ".join(f"#{t}" for t in page.tags)
            print(f"  {page.title} ({tags})")

    elif args.command == "get":
        page = wiki.get_page(args.slug)
        if not page:
            print(f"Страница не найдена: {args.slug}")
        else:
            print(page.to_markdown())

    elif args.command == "delete":
        success = wiki.delete_page(args.slug)
        print("Удалено." if success else "Не удалось удалить (страница не найдена?).")

    elif args.command == "add":
        try:
            tags = parse_tags(args.tags)
        except ValueError as e:
            print(f"Ошибка: {e}")
            print("Ничего не добавлено.")
            return
        try:
            text = args.text
            url_match = URL_RE.search(text)
            if url_match:
                url = url_match.group(0)
                note = text.replace(url, "").strip()
                page = asyncio.run(
                    wiki.ingest_url(url=url, text=note or None, user_tags=tags)
                )
            else:
                page = asyncio.run(wiki.ingest_text(text=text, user_tags=tags))
        except Exception:
            logger.exception("add: не удалось обработать запрос")
            print("Ошибка: не удалось обработать запрос (подробности в wiki.log)")
            return
        print(f"Created: {page.title} ({', '.join(page.tags)})")

    elif args.command == "build":
        out_dir = SiteBuilder(wiki).build()
        print(f"Site built: {out_dir}")

    elif args.command == "open":
        import webbrowser

        out_dir = SiteBuilder(wiki).build()
        index = (out_dir / "index.html").resolve()
        webbrowser.open(index.as_uri())
        print(f"Opened: {index}")

    else:
        parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Необработанная ошибка")
        print("Ошибка: что-то пошло не так (подробности в wiki.log)")
        sys.exit(1)
