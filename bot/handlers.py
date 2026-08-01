from __future__ import annotations

import re

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
)

from config.settings import settings
from core.wiki_manager import WikiManager

router = Router()
wiki = WikiManager()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 Привет! Я WikiLLM бот.\n\n"
        "Отправь мне:\n"
        "— текст или заметку\n"
        "— ссылку\n"
        "— файл (PDF, изображение)\n\n"
        "Команды:\n"
        "/tags — список всех тегов\n"
        "/search <запрос> — поиск по вики\n"
        "/pages — список страниц\n"
        "/help — помощь"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📖 Как пользоваться:\n\n"
        "1. Отправь любой контент (текст, ссылку, файл)\n"
        "2. Добавь теги: просто напиши их в сообщении (#тег1 #тег2)\n"
        "3. Я обработаю и сохраню в вики\n\n"
        "Примеры:\n"
        '• "Интересная статья о RecyclerView #android #разработка"\n'
        '• "Заметка: нужно изучить Coroutines #kotlin"\n'
        '• https://example.com/article'
    )


@router.message(Command("tags"))
async def cmd_tags(message: Message) -> None:
    tags = wiki.list_tags()
    if not tags:
        await message.answer("Пока нет тегов.")
        return

    lines = ["📊 Теги:\n"]
    for tag, count in list(tags.items())[:20]:
        lines.append(f"  #{tag} — {count} стр.")
    await message.answer("\n".join(lines))


@router.message(Command("pages"))
async def cmd_pages(message: Message) -> None:
    pages = wiki.list_pages()
    if not pages:
        await message.answer("Пока нет страниц.")
        return

    lines = ["📚 Страницы:\n"]
    for slug in pages[:20]:
        page = wiki.get_page(slug)
        if page:
            lines.append(f"  • {page.title}")
    await message.answer("\n".join(lines))


@router.message(Command("search"))
async def cmd_search(message: Message) -> None:
    query = message.text.replace("/search", "").strip()
    if not query:
        await message.answer("Укажи запрос: /search <запрос>")
        return

    results = wiki.search_pages(query)
    if not results:
        await message.answer(f"Ничего не найдено по запросу: {query}")
        return

    lines = [f"🔍 Результаты по «{query}»:\n"]
    for page in results[:5]:
        tags_str = ", ".join(f"#{t}" for t in page.tags[:3])
        lines.append(f"  • {page.title} ({tags_str})")
    await message.answer("\n".join(lines))


@router.message(F.text)
async def handle_text(message: Message) -> None:
    text = message.text or ""
    user_tags = re.findall(r"#(\w+)", text)
    clean_text = re.sub(r"#\w+", "", text).strip()

    if not clean_text:
        await message.answer("Отправь текст, ссылку или файл для добавления в вики.")
        return

    # Check if it's a URL
    url_match = re.search(r"https?://\S+", clean_text)
    if url_match:
        await message.answer("🔄 Обрабатываю ссылку...")
        page = await wiki.ingest_url(url=url_match.group(0), user_tags=user_tags)
    else:
        await message.answer("🔄 Обрабатываю текст...")
        page = await wiki.ingest_text(text=clean_text, user_tags=user_tags)

    tags_str = ", ".join(f"#{t}" for t in page.tags)
    await message.answer(
        f"✅ Сохранено: {page.title}\n"
        f"Теги: {tags_str}\n"
        f"Страница: wiki/{page.slug}.md"
    )


@router.message(F.document)
async def handle_document(message: Message) -> None:
    doc = message.document
    if not doc:
        return

    await message.answer("🔄 Загружаю файл...")

    # Download file
    file = await message.bot.get_file(doc.file_id)
    file_bytes = await message.bot.download_file(file.file_path)

    # Extract text (simple approach - just use filename and metadata)
    content = f"Файл: {doc.file_name}\nРазмер: {doc.file_size} байт"
    user_tags = re.findall(r"#(\w+)", message.caption or "")

    page = await wiki.ingest_file(
        filename=doc.file_name or "unknown",
        content=content,
        user_tags=user_tags,
    )

    tags_str = ", ".join(f"#{t}" for t in page.tags)
    await message.answer(
        f"✅ Файл сохранён: {page.title}\n"
        f"Теги: {tags_str}\n"
        f"Страница: wiki/{page.slug}.md\n\n"
        "ℹ️ Для полной обработки PDF/изображений нужна дополнительная настройка."
    )


async def main() -> None:
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.include_router(router)

    print("🤖 Bot started")
    await dp.start_polling(bot)
