# Personal Wiki — база знаний

Личная база знаний на трёх вики-хранилищах с сайтом на GitHub Pages, обновлением через ИИ (omniroute) и ботом в Telegram.

**Сайт:** https://ttenushko.github.io/personal-wiki/

## Зачем

Хранить знания в трёх раздельных базах, пополняемых на русском языке, с единым веб-интерфейсом в стиле Obsidian: inline-поиск, теги, переключение тёмной/светлой темы. Контент попадает в базу автоматически — через Telegram-бот, который скидывает ссылку/документ, ИИ разбирает его и записывает заметку в нужную вики.

## Вики-базы

| Вики | Папка | Содержимое |
|---|---|---|
| Личное | `wikis/personal/` | фильмы, хобби, идеи, заметки |
| Разработка | `wikis/dev/` | Android, Kotlin, технологии |
| Автомобили | `wikis/auto/` | техобслуживание, ремонт |

## Как работает

1. **Пополнение**: Telegram-бот получает ссылку/документ (или `manage.py add`), извлекает текст и отдаёт его LLM (omniroute, `http://localhost:20128`, модель `auto/best-fast`).
2. **AI-анализ**: LLM возвращает JSON `{title, tags, summary, content}` — всё на русском, теги в формате `#нижний-регистр-через-дефис`, в контенте `[[викиссылки]]`.
3. **Запись**: страница пишется в `wikis/<база>/wiki/<section>/<slug>.md` с YAML-фронтматтером (title, created, updated, tags, source).
4. **Сборка**: `scripts/build_site.py` копирует вики в `site-src/`, конвертирует викиссылки, генерирует страницы тегов и файл `tags-data.js`.
5. **Публикация**: `mkdocs build` → GitHub Actions деплоит на GitHub Pages (ветка `llmwiki-cli`).

## Быстрый старт

```bash
# Установить llmwiki-cli (ядро вики)
npm install -g llmwiki-cli

# Установить зависимости скриптов
pip install requests

# Собрать сайт локально
python scripts/build_site.py
mkdocs build
python scripts/clean_search.py site   # очистить HTML из поискового индекса

# Локальный просмотр
mkdocs serve -a 127.0.0.1:8000        # http://127.0.0.1:8000/personal-wiki/
```

## Управление (scripts/manage.py)

Единый CLI для работы с базами. `--wiki` принимает **имя** (`Личное`, `Разработка`, `Автомобили`), пути страниц — относительно корня вики (`wiki/sources/page.md`).

```bash
python scripts/manage.py wikis                 # список вики и количество страниц
python scripts/manage.py add <файл|URL> --wiki Разработка [--section sources] [--dry-run]
python scripts/manage.py delete <путь> --wiki Личное
python scripts/manage.py tags [--wiki Разработка]      # или: --tags --wiki Разработка
python scripts/manage.py tagdel <тег> [--wiki Разработка]  # удалить тег из всех страниц
python scripts/manage.py status [--wiki Разработка]
python scripts/manage.py commit -m "сообщение"
python scripts/manage.py push
python scripts/manage.py sync -m "сообщение"   # commit + push + пересборка
```

Помощь: `python scripts/manage.py --help`, `python scripts/manage.py add --help`.

### Секции вики

| Секция | Папка | Содержимое |
|---|---|---|
| sources | `wiki/sources/` | сводки по источникам |
| entities | `wiki/entities/` | люди, организации, продукты |
| concepts | `wiki/concepts/` | идеи, концепции, теории |
| synthesis | `wiki/synthesis/` | кросс-тематический анализ |

## Сайт (статические файлы)

- `scripts/build_site.py` — сборка исходников сайта из вики: конвертация `[[викиссылок]]`, вставка строки «Теги: …» (исключена из поиска через `data-search-exclude`), генерация страниц тегов, CSS Obsidian-раскладки, версии ассетов с хешами для обхода кеша.
- `scripts/inline-search.js` — inline-поиск по `search/search_index.json` (дебаунс 150 мс, подсветка, дедупликация результатов по странице), переключатель темы (солнце/луна), панель тегов-чипов в правой колонке. Перехватывает `/` вместо модалки Material.
- `scripts/clean_search.py` — убирает HTML-теги из `search_index.json`, чтобы сниппеты в результатах были чистыми.
- `scripts/manage.py` — CLI (см. выше).
- `mkdocs.yml` — конфиг MkDocs Material; `nav` и ссылки на версионированные ассеты перезаписываются `build_site.py` при сборке. `extra_javascript` должен стоять ДО `nav:`.
- `.github/workflows/pages.yml` — деплой: build_site.py → mkdocs build → clean_search.py → GitHub Pages.

## Известные проблемы

1. **Модалка поиска Material**: открывалась по `/` и показывала сырые HTML-сниппеты. Убрана перехватом `/` в capture-фазе + очисткой индекса. Если после обновления открылась модалка — сделай **Ctrl+F5** (браузер кеширует старый JS).
2. **Кеширование**: старый `mkdocs serve` продолжал отдавать устаревшие версии ассетов, пока его не убили по порту 8000. При подозрении на «старый сайт» — перезапусти сервер и Ctrl+F5.
3. **Фронтматтер и отступы тегов**: `tagdel` переписывает фронтматтер через `yaml.safe_dump`, который пишет `- тег` без отступа. Парсер тегов в `build_site.py` принимает оба формата (с отступом и без).
4. **Кириллица в консоли Windows**: PowerShell не отображает кириллицу (кракозябры) — для проверки содержимого используй чтение файла, а не вывод команды.
5. **omniroute на localhost:20128** — должен быть запущен для `manage.py add` (автозапуск через `OmniRoute.vbs` в Startup). Без него `add` не работает; остальные команды не зависят от LLM.
6. **GitHub Pages отстаёт на один коммит**: сайт деплоится из ветки `llmwiki-cli` — пуши в другие ветки сайт не обновляют.

## Что осталось сделать

- [ ] **Telegram-бот**: приём ссылок/документов → извлечение текста → LLM → `manage.py add`. Пользователь пишет бота сам, бот дергает CLI.
- [ ] **Автозапуск на Orange Pi**: `setup/install.sh` — установка и запуск на дешевом сервере вместо локальной машины.
- [ ] Наполнение вики контентом (`personal/` и `auto/` пустые).
- [ ] Полировка: мобильная раскладка, пагинация поиска, интеграция с резюме в ответах LLM.
