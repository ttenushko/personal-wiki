# Personal Wiki

Персональная база знаний на основе LLM по паттерну Karpathy's LLM Wiki.

## Идея

Вместо RAG, где LLM каждый раз заново ищет ответы в документах, здесь LLM **построит и поддерживает вики** — структурированную коллекцию markdown-страниц. При добавлении нового материала LLM не просто индексирует его, а интегрирует в существующую вики: обновляет страницы, добавляет перекрёстные ссылки, отмечает противоречия.

**Ключевое:** вики — это накапливаемый артефакт. Каждый новый источник делает её богаче.

## Что реализовано

### Telegram-бот
- Приём текста, ссылок, файлов с телефона
- Автоматическая обработка LLM
- Извлечение и добавление тегов
- Команды: `/tags`, `/pages`, `/search`, `/help`

### Ядро (LLM + GitHub)
- Обработка контента через OpenRouter (Llama 3.1 8B free)
- Автоматические коммиты в GitHub-репозиторий
- Структура wiki с frontmatter (теги, дата, источник)
- Поиск по страницам и тегам

### Веб-интерфейс
- Просмотр всех страниц
- Управление тегами (добавление, удаление)
- Поиск по вики
- Удаление страниц
- Авторизация по паролю

### CLI
- `python cli/main.py pages` — список страниц
- `python cli/main.py tags` — список тегов
- `python cli/main.py search <запрос>` — поиск
- `python cli/main.py ingest <текст> --tags тег1 тег2` — добавление

## Структура проекта

```
personal-wiki/
├── bot/              # Telegram-бот (aiogram)
│   ├── handlers.py   # Обработчики сообщений
│   └── main.py       # Точка входа бота
├── core/             # Ядро системы
│   ├── llm.py        # Работа с OpenRouter API
│   ├── models.py     # Модель WikiPage
│   ├── github_wiki.py # Git-операции (PyGithub)
│   └── wiki_manager.py # Оркестрация операций
├── web/              # Веб-интерфейс
│   ├── app.py        # FastAPI сервер
│   └── templates/    # HTML-шаблоны (Jinja2)
├── cli/              # CLI-утилита
├── config/           # Настройки (pydantic-settings)
├── main.py           # Точка входа
├── pyproject.toml    # Зависимости
└── .env.example      # Шаблон конфигурации
```

## Быстрый старт

### 1. Установка

```bash
cd personal-wiki
python -m venv venv
venv\Scripts\activate  # Windows
pip install -e .
```

### 2. Настройка

```bash
cp .env.example .env
# Заполни .env ключами (см. раздел "Ключи" ниже)
```

### 3. Запуск

```bash
# Всё вместе (бот + веб)
python main.py all

# Только бот
python main.py bot

# Только веб-интерфейс
python main.py web
```

## Ключи

### Telegram Bot Token
1. Напиши `/newbot` в [@BotFather](https://t.me/BotFather)
2. Задай имя и username
3. Скопируй токен в `TELEGRAM_BOT_TOKEN`

### OpenRouter API Key
1. Зарегистрируйся на [openrouter.ai](https://openrouter.ai)
2. Создай API-ключ в Settings → Keys
3. Вставь в `OPENROUTER_API_KEY`
4. Модель по умолчанию: `meta-llama/llama-3.1-8b-instruct:free` (бесплатная)

### GitHub Token
1. Создай [Personal Access Token](https://github.com/settings/tokens) с правами `repo`
2. Создай пустой репозиторий (например `personal-wiki-vault`)
3. Вставь токен в `GITHUB_TOKEN` и имя репо в `GITHUB_REPO` (формат: `username/repo`)

### Google Drive (опционально)
1. Создай проект в [Google Cloud Console](https://console.cloud.google.com)
2. Включи Google Drive API
3. Создай Service Account и скачай `credentials.json`
4. Положи в корень проекта
5. Вставь ID папки в `GOOGLE_DRIVE_FOLDER_ID`

## Использование

### С телефона (Telegram)
```
Ты: Интересная статья о Coroutines в Kotlin #kotlin #coroutines
Бот: 🔄 Обрабатываю текст...
Бот: ✅ Сохранено: Coroutines в Kotlin
     Теги: #kotlin, #coroutines, #асинхронность
     Страница: wiki/coroutines-v-kotlin.md

Ты: /tags
Бот: 📊 Теги:
     #android — 12 стр.
     #kotlin — 8 стр.
     #coroutines — 3 стр.
```

### С компьютера (веб)
- Открой `http://localhost:8000`
- Введи пароль (по умолчанию: `admin`)
- Просматривай, ищи, добавляй теги, удаляй страницы

### CLI
```bash
python cli/main.py pages          # Список страниц
python cli/main.py tags           # Список тегов
python cli/main.py search android # Поиск
python cli/main.py delete slug    # Удаление
```

## Планируется

### Фаза 1: Базовый функционал ✅
- [x] Telegram-бот
- [x] GitHub-интеграция
- [x] LLM-обработка (OpenRouter)
- [x] Веб-интерфейс с авторизацией
- [x] CLI-утилита
- [x] Система тегов

### Фаза 2: Расширенный функционал
- [ ] Google Drive для тяжёлых файлов (PDF, изображения)
- [ ] Парсинг контента по ссылкам (BeautifulSoup)
- [ ] Обработка PDF и изображений (LLM vision)
- [ ] Экспорт вики (zip, Obsidian-формат)
- [ ] Статистика (количество страниц, тегов, активность)

### Фаза 3: Командная работа
- [ ] Мульти-пользовательская авторизация
- [ ] Роли (admin, viewer)
- [ ] Одобрение изменений (workflow)
- [ ] Уведомления о изменениях

### Фаза 4: Продвинутые возможности
- [ ] Автоматический lint (проверка на противоречия)
- [ ] Генерация сводок/резюме
- [ ] Интеграция с Notion/Obsidian
- [ ] Мобильное приложение (PWA)
- [ ] Голосовой ввод через Telegram

### Фаза 5: Деплой
- [ ] Docker-контейнер
- [ ] Деплой на Oracle Cloud Free Tier
- [ ] Настройка CI/CD
- [ ] Мониторинг и логирование

## Технологии

- **Язык:** Python 3.11+
- **Telegram:** aiogram 3.x
- **Веб:** FastAPI + Jinja2
- **LLM:** OpenRouter (Llama 3.1 8B free)
- **Хранилище:** GitHub (markdown + git)
- **Файлы:** Google Drive API (опционально)
- **CLI:** argparse

## Лицензия

MIT
