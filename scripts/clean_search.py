"""Strip raw HTML from search_index.json so search snippets are clean."""

import html
import json
import re
import sys
from pathlib import Path

TAG_RE = re.compile(r"<[^>]+>")


def clean_text(s: str) -> str:
    if not s:
        return s
    s = TAG_RE.sub(" ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def main() -> None:
    index_path = Path(sys.argv[1] if len(sys.argv) > 1 else "site") / "search" / "search_index.json"
    if not index_path.exists():
        print(f"Index not found: {index_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(index_path.read_text(encoding="utf-8"))
    for doc in data.get("docs", []):
        doc["title"] = clean_text(doc.get("title", ""))
        doc["text"] = clean_text(doc.get("text", ""))

    index_path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Cleaned {len(data.get('docs', []))} docs in {index_path}")


if __name__ == "__main__":
    main()
