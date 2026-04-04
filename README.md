# Portfolio Website

Static portfolio site built with Flask and YAML data files, plus a code previewer that renders project source code and Markdown in the browser.

## Features

- Data-driven content from YAML (profile, socials, jobs, education, courses, projects).
- Project code previewer with file tree, syntax highlighting, and Markdown rendering.
- Project search with fuzzy matching for name/tags/keywords/description.

## Data (YAML)

All site content lives under the `data/` directory.

- `profile.yaml`, `socials.yaml`
- `jobs.yaml`
- `education.yaml`
- `courses.yaml`
- `projects.yaml`

`projects.yaml` supports fields like:

```yaml
- name: "project_slug"
  display_name: "Project Display Name"
  description: "Short description"
  Course: "Course name" # optional
  github: "https://github.com/..." # optional
  demo: "https://..." # optional
  main_file: "README.md"
  code_path: "project_folder/" # under static/projects
  files: [] # optional explicit list; otherwise auto-discovered
  priority: 1 # low number means a high priority
  tags: ["tag1", "tag2"]
  keywords: ["keyword1", "keyword2"]
```

## Backend (Flask)

Flask app factory lives in `app/__init__.py`. Routes are defined in `app/routes.py`.

Key endpoints:

- `GET /` and other content pages rendered from YAML.
- `GET /projects` list view.
- `GET /projects/<name>` code previewer page.
- `GET /code/<project>/<path:filename>` raw file content.
- `GET /code/<project>/<path:filename>/tokens` tokenized source for syntax highlighting.
- `POST /code/<project>/snippet/tokens` tokenized Markdown code fences.

Project file roots are resolved from `CODE_DIR` in `app/config.py` (default `static/projects`).

## Syntax Highlighting

Highlighting is done server-side with a lightweight tokenizer in `app/syntax.py`.
Language definitions live in `data/syntax_languages.json` (keywords, builtins, operators).
The frontend renders tokens with the same styles for full files and Markdown fences.

Supported languages include Python, JavaScript, and Bash.

## Frontend (Previewer)

The previewer is powered by:

- `static/js/previewer.js`: file tree, code pane, token rendering, state persistence.
- `static/js/markdown_renderer.js`: Markdown rendering including math, admonitions, images and code fence integration.
- `static/css/previewer.css`: previewer layout, tokens, Markdown styles.

Markdown code fences render using the same token renderer as full files.
A language badge is shown alongside the code block when a language is specified.

## Git Submodules (Projects)

Project repositories are stored under `static/projects/`. You can add them as Git submodules.

Add a new project submodule:

```bash
git submodule add <repo-url> static/projects/<folder-name>
```

Clone with submodules:

```bash
git submodule update --init --recursive
```

Update submodules:

```bash
git submodule update --remote --merge
```

## Setup

### Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

or

```bash
uv sync
source .venv/bin/activate
```

### Run (development)

```bash
flask run --debug
```

### Run (production)

```bash
gunicorn "run:app"
```

## Project CLI Commands


### Recipes

```bash
docker exec -it recipes bash
```

```bash
exit
```

#### commands
```bash
flask create-user <username> <email>
flask create-admin <username> <email>
flask seed-data
flask seed-data --users 10 --recipes 50
flask clear-data
flask db-stats
flask add-machine "Oven"
flask list-machines
flask seed-machines
```

### Marketplace

```bash
docker exec -it recipes bash
```

```bash
exit
```

#### commands
```bash
flask cli recreate-db
flask cli recreate-db --users 50 --listings 200
flask cli create-admin
```
