# Personal Wiki

Персональная база знаний на основе LLM по паттерну Karpathy's LLM Wiki.

## Идея

Вместо RAG, где LLM каждый раз заново ищет ответы в документах, здесь LLM **построит и поддерживает вики** — структурированную коллекцию markdown-страниц. При добавлении нового материала LLM не просто индексирует его, а интегрирует в существующую вики: обновляет страницы, добавляет перекрёстные ссылки, отмечает противоречия.

**Ключевое:** вики — это накапливаемый артефакт. Каждый новый источник делает её богаче.

## Что реализовано

### CLI (главный интерфейс)
- `add` — добавление текста/ссылки/заметки
- `pages` — список страниц
- `tags` — список тегов с количеством страниц
- `search <запрос>` — поиск по вики
- `get <slug>` — просмотр страницы
- `delete <slug>` — удаление страницы
- `build` — собрать статический HTML-сайт в `site/`
- `open` — собрать сайт и открыть главную страницу в браузере
- Теги через `#tag`, `#'tag с пробелом'`, `#"tag #3"` с валидацией ошибок

### Хранилище
- Страницы хранятся локально в `pages/` как markdown-файлы
- Опционально синхронизируются с GitHub-репозиторием (бэкап)
- `wiki open` генерирует статический HTML (без сервера) и открывает в браузере

### Ядро (LLM + GitHub)
- Обработка контента через цепочку LLM-провайдеров (OpenRouter, OpenCode Zen, локальная Ollama)
- **Скачивание и извлечение текста со ссылок** (httpx + BeautifulSoup)
- Синхронизация с GitHub-репозиторием (опционально)
- Структура wiki с frontmatter (теги, дата, источник)
- Поиск по страницам и тегам

### Веб-интерфейс
- Просмотр всех страниц
- Управление тегами (добавление, удаление)
- Поиск по вики
- Удаление страниц
- Авторизация по паролю

### Telegram-бот (в работе)
- Приём текста, ссылок, файлов с телефона
- Команды: `/tags`, `/pages`, `/search`, `/help`

## Структура проекта

```
personal-wiki/
├── wikis/               # Вики-базы (llmwiki-cli)
│   ├── personal/        #   «Личное»
│   ├── dev/             #   «Разработка»
│   └── auto/            #   «Автомобили»
├── scripts/
│   └── build_site.py    # Сборка MkDocs из вики (викилинки, теги, навигация)
├── setup/
│   └── install.sh       # Быстрая настройка на Orange Pi
├── .github/workflows/
│   └── pages.yml        # GitHub Actions: сборка + деплой MkDocs
├── SCHEMA.md            # Общая схема страниц для LLM
├── mkdocs.yml           # Конфиг MkDocs (nav вписывается при сборке)
└── .env.example         # Шаблон конфигурации (ключи для бота/LLM)
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

### 3. CLI

```bash
# Windows
wiki.cmd add "Моя заметка" #android #kotlin
wiki.cmd pages

# Unix/macOS
chmod +x wiki
./wiki add "Моя заметка" #android #kotlin
```

### 4. Просмотр вики (статический HTML)

```bash
# Windows: собрать и открыть в браузере
wiki.cmd open

# Unix/macOS
./wiki open
```

`open` генерирует сайт в `site/` и открывает `index.html` в браузере — без сервера и пароля.

### 5. Веб-интерфейс (опционально, для бота и API)

```bash
python -m wikillm.main web
# → http://localhost:8000 (пароль: admin)
```

### 6. Telegram-бот (когда настроен токен)

```bash
python -m wikillm.main bot
```

## Ключи

### OpenRouter API Key
1. Зарегистрируйся на [openrouter.ai](https://openrouter.ai)
2. Создай API-ключ в Settings → Keys
3. Вставь в `OPENROUTER_API_KEY`
4. Модель по умолчанию: `nvidia/nemotron-3-ultra-550b-a55b:free` (бесплатная)

### GitHub Token
1. Создай [Personal Access Token](https://github.com/settings/tokens) с правами `repo`
2. Создай пустой репозиторий (например `personal-wiki-vault`)
3. Вставь токен в `GITHUB_TOKEN` и имя репо в `GITHUB_REPO` (формат: `username/repo`)

### Telegram Bot Token
1. Напиши `/newbot` в [@BotFather](https://t.me/BotFather)
2. Задай имя и username
3. Скопируй токен в `TELEGRAM_BOT_TOKEN`

### Google Drive (опционально)
1. Создай проект в [Google Cloud Console](https://console.cloud.google.com)
2. Включи Google Drive API
3. Создай Service Account и скачай `credentials.json`
4. Положи в корень проекта
5. Вставь ID папки в `GOOGLE_DRIVE_FOLDER_ID`

## Использование

### CLI — добавление заметок

```bash
# Текст с тегами
wiki.cmd add "Заметка про RecyclerView" #android #kotlin

# Тег с пробелом (одинарные или двойные кавычки)
wiki.cmd add "Заметка" #'android разработка' #android
wiki.cmd add "Заметка" #"android разработка" #android

# Ссылка — контент скачается и обработается автоматически
wiki.cmd add "https://developer.android.com" #android #'компоновка UI'
```

При ошибке в тегах (несогласованные кавычки, не-тег) выводится сообщение и **ничего не добавляется**.

### CLI — управление

```bash
wiki.cmd pages                    # Список страниц
wiki.cmd tags                     # Список тегов
wiki.cmd search android           # Поиск
wiki.cmd get my-note              # Просмотр страницы
wiki.cmd delete my-note           # Удаление
wiki.cmd build                    # Собрать статический сайт в site/
wiki.cmd open                     # Собрать и открыть в браузере
```

### GitHub-синк

Страницы по умолчанию сохраняются локально в `pages/`. Если заполнить
`GITHUB_TOKEN` и `GITHUB_REPO` в `.env`, каждая запись дублируется в
GitHub-репозиторий (папка `wiki/`), а список страниц читается оттуда.

### Веб
- Открой `http://localhost:8000`
- Введи пароль (по умолчанию: `admin`)
- Просматривай, ищи, добавляй теги, удаляй страницы

## Планируется

### Фаза 1: Базовый функционал ✅
- [x] CLI-утилита (`wiki.cmd` / `wiki`)
- [x] GitHub-интеграция
- [x] LLM-обработка (OpenRouter)
- [x] Парсинг контента со ссылок
- [x] Веб-интерфейс с авторизацией
- [x] Система тегов с валидацией

### Фаза 2: Боты и файлы
- [ ] Telegram-бот: синхронизация формата тегов с CLI
- [ ] Google Drive для тяжёлых файлов (PDF, изображения)
- [ ] Обработка PDF и изображений (LLM vision)
- [ ] Локальные тесты через Termux на телефоне

### Фаза 3: Расширение
- [ ] Экспорт вики (zip, Obsidian-формат)
- [ ] Статистика (количество страниц, тегов, активность)
- [ ] Мульти-пользовательская авторизация
- [ ] Одобрение изменений (workflow)

### Фаза 4: Продвинутые возможности
- [ ] Автоматический lint (проверка на противоречия, битые ссылки, сироты)
- [ ] Генерация сводок/резюме
- [ ] Интеграция с Notion/Obsidian
- [ ] Мобильное приложение (PWA)
- [ ] Голосовой ввод через Telegram

### Фаза 5: Деплой
- [ ] Docker-контейнер
- [ ] Хостинг: Timeweb/Selectel VPS или домашний сервер + Cloudflare Tunnel
- [ ] Настройка CI/CD
- [ ] Мониторинг и логирование

## Технологии

- **Язык:** Python 3.11+
- **Просмотр:** статический HTML (markdown → html), без сервера
- **Веб (опционально):** FastAPI + Jinja2
- **LLM:** OpenRouter / OpenCode Zen / Ollama (цепочка провайдеров)
- **Парсинг ссылок:** httpx + BeautifulSoup
- **Хранилище:** локальная папка `pages/` + GitHub-синк
- **CLI:** argparse + обёртки wiki.cmd/wiki
- **Telegram:** aiogram 3.x

## Лицензия

MIT
