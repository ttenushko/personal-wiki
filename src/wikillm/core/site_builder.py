from __future__ import annotations

import html
import shutil
from pathlib import Path

import markdown

from wikillm.config.settings import settings
from wikillm.core.models import WikiPage
from wikillm.core.storage import safe_filename
from wikillm.core.wiki_manager import WikiManager

CSS = """
:root {
  --bg: #faf9f6;
  --fg: #24292f;
  --muted: #57606a;
  --accent: #0969da;
  --border: #d0d7de;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--fg);
  line-height: 1.6;
}
.wrap { max-width: 860px; margin: 0 auto; padding: 32px 20px 64px; }
header {
  border-bottom: 1px solid var(--border);
  padding: 14px 0;
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
header a { text-decoration: none; color: var(--accent); font-weight: 600; }
h1 { font-size: 2em; margin: 0.3em 0 0.5em; }
h2 { border-bottom: 1px solid var(--border); padding-bottom: 0.25em; }
a { color: var(--accent); }
pre, code { background: #f6f8fa; border-radius: 6px; }
pre { padding: 14px; overflow-x: auto; }
code { padding: 0.2em 0.4em; font-size: 0.9em; }
pre code { padding: 0; background: none; }
.tag {
  display: inline-block;
  background: #ddf4ff;
  color: #0969da;
  border-radius: 12px;
  padding: 2px 10px;
  margin: 0 6px 6px 0;
  font-size: 0.85em;
}
.page-list { list-style: none; padding: 0; }
.page-list li { padding: 10px 0; border-bottom: 1px solid var(--border); }
.page-list a { font-size: 1.1em; font-weight: 600; }
.page-list .tags { display: block; margin-top: 4px; }
.meta { color: var(--muted); font-size: 0.85em; }
"""


class SiteBuilder:
    """Generate a static HTML site from the wiki pages."""

    def __init__(self, wiki: WikiManager) -> None:
        self.wiki = wiki
        self.out_dir = settings.site_dir
        self.md = markdown.Markdown(
            extensions=["fenced_code", "tables", "nl2br"],
            output_format="html5",
        )

    def build(self) -> Path:
        # Защита от случайного удаления важных директорий
        out = self.out_dir.resolve()
        root = settings.project_root.resolve()
        if (
            out == root
            or out == settings.pages_dir.resolve()
            or out.parent == out
            or str(out).lower().startswith(str(root).lower()) is False
            or out == root.parent
        ):
            raise ValueError(f"Опасный путь для site: {self.out_dir}")

        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True, exist_ok=True)

        pages = self.wiki.list_pages()
        index_page = self.wiki.get_page("index")
        index_content = index_page.content if index_page else ""

        # Прочитаем страницы один раз
        page_map: dict[str, WikiPage] = {}
        for slug in pages:
            page = self.wiki.get_page(slug)
            if page:
                page_map[slug] = page

        page_list_html = self._render_page_list(page_map)
        index_html = self._render_index(index_content, page_list_html)
        (out / "index.html").write_text(index_html, encoding="utf-8")

        for slug, page in page_map.items():
            (out / f"{safe_filename(slug)}.html").write_text(
                self._render_page(page),
                encoding="utf-8",
            )

        self._write_style()
        return out

    def _render_index(self, content: str, page_list: str) -> str:
        body = self.md.convert(content or "")
        return self._page("Wiki", f"<h1>Wiki</h1>\n{body}\n{page_list}")

    def _render_page_list(self, pages: dict[str, WikiPage]) -> str:
        if not pages:
            return '<p class="meta">Пока пусто.</p>'
        items = []
        for slug, page in pages.items():
            tags = " ".join(
                f'<span class="tag">#{html.escape(t)}</span>' for t in page.tags
            )
            items.append(
                f'<li><a href="{html.escape(safe_filename(slug))}.html">'
                f"{html.escape(page.title)}</a>"
                f'<span class="tags">{tags}</span></li>'
            )
        return f'<ul class="page-list">{"".join(items)}</ul>'

    def _render_page(self, page: WikiPage) -> str:
        body = self.md.convert(page.content)
        tags = " ".join(f'<span class="tag">#{html.escape(t)}</span>' for t in page.tags)
        meta = f"<p class=\"meta\">Обновлено: {page.updated_at.strftime('%d.%m.%Y %H:%M')}</p>"
        return self._page(
            page.title,
            f"<h1>{html.escape(page.title)}</h1>{tags}{meta}\n{body}",
        )

    def _page(self, title: str, body_html: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<div class="wrap">
<header>
  <a href="index.html">На главную</a>
</header>
{body_html}
</div>
</body>
</html>
"""

    def _write_style(self) -> None:
        (self.out_dir / "style.css").write_text(CSS, encoding="utf-8")
