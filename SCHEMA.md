# Personal Wiki — база знаний

## Обзор

Три вики-хранилища (в общей папке `wikis/`):
- `wikis/personal/` — личное (фильмы, хобби, идеи, заметки)
- `wikis/dev/` — разработка (Android, Kotlin, технологии)
- `wikis/auto/` — автомобили (техобслуживание, ремонт)

## Как работает AI-оброботка

Когда пользователь скидывает ссылку или документ:

1. **Извлечение текста**: trafilatura (URL), pypdf (PDF), python-docx (DOCX), pytesseract (картинки)
2. **AI-анализ через omniroute**: LLM получает текст → возвращает JSON:
   ```json
   {
     "title": "Заголовок",
     "tags": ["тег1", "тег2"],
     "summary": "Краткое резюме",
     "content": "Полный текст заметки"
   }
   ```
3. **Запись в вики**: `wiki write wiki/sources/<slug>.md` с YAML-фронтматтером
4. **Git commit**: автоматический коммит в репозиторий
5. **GitHub Pages**: сайт обновляется

## Язык

Все страницы, теги и резюме — **на русском** (кроме устоявшихся технических терминов: Android, Kotlin, API).

## LLM Prompt (omniroute)

```
Analyze the text. Return ONLY valid JSON, no prose:
{"title":"Short Russian title (max 10 words)",
 "tags":["tag1","tag2","tag3"],
 "summary":"2-4 Russian sentences",
 "content":"Full note text with [[wikilinks]]"}
Rules: all output in Russian (except tech terms: android, kotlin, api).
Tags: 3-7, lowercase, hyphens, descriptive.
Content: use [[wikilinks]], headers (##), preserve key info.
```

## Структура файлов

```
wikis/personal/
  .llmwiki.yaml
  SCHEMA.md
  raw/              # Исходные документы (неизменяемые)
  wiki/
    index.md        # Главный индекс
    entities/       # Люди, организации, продукты
    concepts/       # Идеи, концепции, теории
    sources/        # Сводки по источникам
    synthesis/      # Кросс-тематический анализ

wikis/dev/
  ...

wikis/auto/
  ...
```

## CLI-команды

> `--wiki` принимает **имя** из реестра (не папку): `Личное`, `Разработка`, `Автомобили`.

```bash
# Переключение между вики
wiki --wiki "Личное" status
wiki --wiki "Разработка" status
wiki --wiki "Автомобили" status

# Запись страницы (JSON на stdin)
echo '{"title":"...", "tags":["..."], "content":"..."}' | wiki --wiki "Разработка" write wiki/sources/page.md

# Поиск
wiki --wiki "Разработка" search "android"
wiki --wiki "Личное" search "фильм"

# Проверка здоровья
wiki --wiki "Разработка" lint
```

## Git workflow

```bash
git add -A
git commit -m "wiki: обновление <название>"
git push
```

GitHub Pages автоматически обновляется при пуше в main.
