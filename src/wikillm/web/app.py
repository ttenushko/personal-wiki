from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import markdown
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from wikillm.config.settings import settings
from wikillm.core.wiki_manager import WikiManager

app = FastAPI(title="Personal Wiki")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.filters["markdown"] = markdown.Markdown(
    extensions=["fenced_code", "tables", "nl2br"],
    output_format="html5",
).convert
wiki = WikiManager()

SLUG_PATTERN = re.compile(r"^[a-z0-9_-]+$")


def verify_password(request: Request) -> bool:
    password = request.cookies.get("wiki_password")
    return password == settings.web_password


class IngestTextRequest(BaseModel):
    text: str
    tags: list[str] | None = None


class IngestUrlRequest(BaseModel):
    url: str
    text: str | None = None
    tags: list[str] | None = None


class TagsUpdateRequest(BaseModel):
    tags: list[str]


@app.get("/", response_class=HTMLResponse, response_model=None)
async def index(request: Request) -> HTMLResponse | RedirectResponse:
    if not verify_password(request):
        return RedirectResponse("/login")
    pages = [p for p in (wiki.get_page(s) for s in wiki.list_pages()) if p]
    tags = wiki.list_tags()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "pages": pages, "tags": list(tags.items())[:10]},
    )


@app.get("/login", response_class=HTMLResponse, response_model=None)
async def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_model=None)
async def login(request: Request) -> RedirectResponse:
    form = await request.form()
    password = form.get("password", "")
    if password == settings.web_password:
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(
            "wiki_password",
            password,
            httponly=True,
            samesite="lax",
            max_age=86400 * 30,
        )
        return response
    return RedirectResponse("/login?error=1", status_code=303)


@app.get("/page/{slug}", response_class=HTMLResponse, response_model=None)
async def view_page(request: Request, slug: str) -> HTMLResponse:
    if not verify_password(request):
        return RedirectResponse("/login")
    page = wiki.get_page(slug)
    if not page:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        "page.html",
        {"request": request, "page": page},
    )


@app.get("/tags", response_class=HTMLResponse, response_model=None)
async def view_tags(request: Request) -> HTMLResponse:
    if not verify_password(request):
        return RedirectResponse("/login")
    tags = wiki.list_tags()
    return templates.TemplateResponse(
        "tags.html",
        {"request": request, "tags": tags},
    )


@app.get("/search", response_class=HTMLResponse, response_model=None)
async def search(request: Request, q: str = "") -> HTMLResponse:
    if not verify_password(request):
        return RedirectResponse("/login")
    results = wiki.search_pages(q) if q else []
    return templates.TemplateResponse(
        "search.html",
        {"request": request, "query": q, "results": results},
    )


@app.post("/api/ingest/text")
async def api_ingest_text(request: Request, data: IngestTextRequest) -> dict:
    if not verify_password(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    page = await wiki.ingest_text(
        text=data.text,
        user_tags=data.tags,
    )
    return {"slug": page.slug, "title": page.title, "tags": page.tags}


@app.post("/api/ingest/url")
async def api_ingest_url(request: Request, data: IngestUrlRequest) -> dict:
    if not verify_password(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    page = await wiki.ingest_url(
        url=data.url,
        text=data.text,
        user_tags=data.tags,
    )
    return {"slug": page.slug, "title": page.title, "tags": page.tags}


@app.put("/api/page/{slug}/tags")
async def api_update_tags(slug: str, request: Request, data: TagsUpdateRequest) -> dict:
    if not verify_password(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    page = wiki.get_page(slug)
    if not page:
        raise HTTPException(status_code=404)
    page.tags = data.tags
    page.updated_at = datetime.now()
    wiki.storage.save_page(
        slug=slug,
        content=page.to_markdown(),
        message=f"Update tags for {page.title}",
    )
    return {"slug": slug, "tags": page.tags}


@app.delete("/api/page/{slug}")
async def api_delete_page(slug: str, request: Request) -> dict:
    if not verify_password(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    success = wiki.delete_page(slug)
    if not success:
        raise HTTPException(status_code=500)
    return {"deleted": slug}
