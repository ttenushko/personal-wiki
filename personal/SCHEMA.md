# Личное — личные заметки, фильмы, хобби, идеи Knowledge Base

## Wiki Structure

```
raw/                  # Immutable source documents (paste originals here)
  assets/             # Downloaded images and files
wiki/                 # LLM-generated pages (all knowledge lives here)
  index.md            # Master index of all pages (updated by wiki write)
  entities/           # People, orgs, products
  concepts/           # Ideas, frameworks, theories
  sources/            # One summary per ingested source
  synthesis/          # Cross-cutting analysis
```

## Page Format

Every wiki page should use YAML frontmatter:

```markdown
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [tag1, tag2]
source: URL or description
---

Page content here. Use [[wikilinks]] to connect pages.
```

## Wikilink Syntax

- `[[page-name]]` — links to a page (resolved by filename across all wiki directories)
- `[[page-name|Display Text]]` — link with custom display text

## CLI Commands

### Wiki Management
```bash
wiki init [dir] --name <name> --domain <domain>      # Create new wiki (local files only)
wiki registry                                       # List all wikis
wiki use [wiki-id]                                  # Set active wiki
```

### Reading & Writing
```bash
wiki read <path>                                    # Print page markdown to stdout
wiki write <path> <<'JSON'                          # JSON on stdin → YAML frontmatter + body; upserts wiki/index.md
{"title":"…","content":"…"}
JSON
wiki delete <path>                                  # Delete page and remove from index
wiki list [dir] [--tree] [--json]                   # List pages
wiki search <query> [--limit N] [--all] [--json]    # Search pages
```

### Version control and visualization (optional)
Use normal Git in your wiki directory if you want history and remotes. For an interactive link graph on GitHub Pages, copy the workflow and `scripts/` files from the llmwiki-cli repository (see project README: optional viz drop-in).

### Health & Links
```bash
wiki lint [--json]                                  # Health check
wiki links <path>                                   # Outbound + inbound links
wiki backlinks <path>                               # Inbound links only
wiki orphans                                        # Pages with no inbound links
wiki status [--json]                                # Wiki overview stats
```

## Ingest Workflow

When ingesting a new source:

1. Save the raw source to `raw/` (paste full text, keep immutable)
2. Create a source summary page in `wiki/sources/`
3. Extract entities → create/update pages in `wiki/entities/`
4. Extract concepts → create/update pages in `wiki/concepts/`
5. If cross-cutting insights emerge → create `wiki/synthesis/` pages
6. For each new or updated page under `wiki/`, use `wiki write <path>` with JSON on stdin — the CLI writes YAML frontmatter plus body and **upserts** `wiki/index.md` automatically.
7. Version changes with Git or another tool outside the CLI if you need history

## Query Workflow

When answering a question using the wiki:

1. `wiki search "<query terms>"` to find relevant pages
2. `wiki read <path>` to read promising results
3. Follow [[wikilinks]] to gather connected knowledge
4. Synthesize answer from wiki content
5. Optional: track queries in your own notes outside the CLI (there is no activity log command).

## Lint Workflow

Periodically check wiki health:

1. `wiki lint` to find issues (broken links, orphans, missing frontmatter)
2. Fix broken links by creating missing pages or updating references
3. Connect orphan pages by adding wikilinks from related pages
4. Add frontmatter to pages missing it
5. Re-run `wiki lint` until clean

## Conventions

1. File names use kebab-case: `my-topic-name.md`
2. One topic per file. Split large topics into sub-topics.
3. Adding or updating pages under `wiki/` via `wiki write` keeps `wiki/index.md` in sync; use `wiki delete` when removing pages.
4. Use [[wikilinks]] to connect related pages.
5. Prefer concrete examples over abstract descriptions.
6. Include the source of knowledge when possible.
7. Use callouts for important notes:
   - `> [!NOTE]` for general notes
   - `> [!WARNING]` for contradictions or caveats
   - `> [!TIP]` for best practices
