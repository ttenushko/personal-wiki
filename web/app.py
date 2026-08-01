from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config.settings import settings
from core.wiki_manager import WikiManager

app = FastAPI(title="Personal Wiki")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
wiki = WikiManager()


# Simple auth
def verify_password(request: Request) -> bool:
    password = request.cookies.get("wiki_password")
    return password == settings.web_password


class TagUpdate(BaseModel):
    slug: str
    tags: list[str]


class PageUpdate(BaseModel):
    slug: str
    title: str
    content: str
    tags: list[str]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse | RedirectResponse:
    if not verify_password(request):
        return RedirectResponse("/login")
    pages = wiki.list_pages()
    tags = wiki.list_tags()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "pages": pages, "tags": tags},
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(request: Request) -> RedirectResponse:
    form = await request.form()
    password = form.get("password", "")
    if password == settings.web_password:
        response = RedirectResponse("/", status_code=303)
        response.set_cookie("wiki_password", password)
        return response
    return RedirectResponse("/login?error=1", status_code=303)


@app.get("/page/{slug}", response_class=HTMLResponse)
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


@app.get("/tags", response_class=HTMLResponse)
async def view_tags(request: Request) -> HTMLResponse:
    if not verify_password(request):
        return RedirectResponse("/login")
    tags = wiki.list_tags()
    return templates.TemplateResponse(
        "tags.html",
        {"request": request, "tags": tags},
    )


@app.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: str = "") -> HTMLResponse:
    if not verify_password(request):
        return RedirectResponse("/login")
    results = wiki.search_pages(q) if q else []
    return templates.TemplateResponse(
        "search.html",
        {"request": request, "query": q, "results": results},
    )


# API endpoints for bot/web interaction
@app.post("/api/ingest/text")
async def api_ingest_text(request: Request) -> dict:
    data = await request.json()
    page = await wiki.ingest_text(
        text=data["text"],
        user_tags=data.get("tags"),
    )
    return {"slug": page.slug, "title": page.title, "tags": page.tags}


@app.post("/api/ingest/url")
async def api_ingest_url(request: Request) -> dict:
    data = await request.json()
    page = await wiki.ingest_url(
        url=data["url"],
        text=data.get("text"),
        user_tags=data.get("tags"),
    )
    return {"slug": page.slug, "title": page.title, "tags": page.tags}


@app.put("/api/page/{slug}/tags")
async def api_update_tags(slug: str, request: Request) -> dict:
    data = await request.json()
    page = wiki.get_page(slug)
    if not page:
        raise HTTPException(status_code=404)
    page.tags = data["tags"]
    from datetime import datetime
    page.updated_at = datetime.now()
    wiki.github.create_or_update_file(
        path=f"wiki/{slug}.md",
        content=page.to_markdown(),
        message=f"Update tags for {page.title}",
    )
    return {"slug": slug, "tags": page.tags}


@app.delete("/api/page/{slug}")
async def api_delete_page(slug: str) -> dict:
    success = wiki.delete_page(slug)
    if not success:
        raise HTTPException(status_code=500)
    return {"deleted": slug}
