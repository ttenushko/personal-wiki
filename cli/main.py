from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.wiki_manager import WikiManager


def main() -> None:
    parser = argparse.ArgumentParser(description="Personal Wiki CLI")
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

    # Ingest text
    ingest_parser = subparsers.add_parser("ingest", help="Ingest text")
    ingest_parser.add_argument("text", help="Text to ingest")
    ingest_parser.add_argument("--tags", nargs="*", help="Tags")

    args = parser.parse_args()
    wiki = WikiManager()

    if args.command == "pages":
        pages = wiki.list_pages()
        if not pages:
            print("No pages yet.")
        for slug in pages:
            page = wiki.get_page(slug)
            if page:
                tags = ", ".join(f"#{t}" for t in page.tags)
                print(f"  {page.title} ({tags})")

    elif args.command == "tags":
        tags = wiki.list_tags()
        if not tags:
            print("No tags yet.")
        for tag, count in tags.items():
            print(f"  #{tag} — {count} pages")

    elif args.command == "search":
        results = wiki.search_pages(args.query)
        if not results:
            print(f"No results for: {args.query}")
        for page in results:
            tags = ", ".join(f"#{t}" for t in page.tags)
            print(f"  {page.title} ({tags})")

    elif args.command == "get":
        page = wiki.get_page(args.slug)
        if not page:
            print(f"Page not found: {args.slug}")
        else:
            print(page.to_markdown())

    elif args.command == "delete":
        success = wiki.delete_page(args.slug)
        print("Deleted." if success else "Failed to delete.")

    elif args.command == "ingest":
        page = asyncio.run(wiki.ingest_text(args.text, args.tags))
        print(f"Created: {page.title} ({', '.join(page.tags)})")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
