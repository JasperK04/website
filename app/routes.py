"""
URL routes for the portfolio application.
Registered as the 'main' Blueprint.
"""

import os
from pathlib import Path

from flask import Blueprint, abort, current_app, jsonify, render_template, request

from .syntax import tokenize_plain, tokenize_python
from .utils import load_yaml, search_items

main = Blueprint("main", __name__)


# ---------------------------------------------------------------------------
# Context processor — inject profile + socials into every template
# ---------------------------------------------------------------------------


@main.context_processor
def inject_globals():
    return {
        "profile": load_yaml("profile.yaml"),
        "socials": load_yaml("socials.yaml"),
    }


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/about")
def about():
    return render_template("about.html")


@main.route("/education")
def education():
    query = request.args.get("q", "")
    items = load_yaml("education.yaml")
    items = (
        search_items(items, query)
        if query
        else sorted(items, key=lambda x: x.get("priority", 99))
    )
    return render_template("education.html", items=items, query=query)


@main.route("/jobs")
def jobs():
    query = request.args.get("q", "")
    items = load_yaml("jobs.yaml")
    items = (
        search_items(items, query)
        if query
        else sorted(items, key=lambda x: x.get("priority", 99))
    )
    return render_template("jobs.html", items=items, query=query)


@main.route("/projects")
def projects():
    query = request.args.get("q", "")
    items = load_yaml("projects.yaml")
    items = (
        search_items(items, query)
        if query
        else sorted(items, key=lambda x: x.get("priority", 99))
    )
    return render_template("projects.html", items=items, query=query)


@main.route("/projects/<project_name>")
def project_detail(project_name: str):
    projects_data = load_yaml("projects.yaml")
    project = next((p for p in projects_data if p["name"] == project_name), None)
    if not project:
        abort(404)
    project_data = dict(project)
    project_data["files"] = _build_project_files(project_name, project_data)
    return render_template("project_detail.html", project=project_data)


# ---------------------------------------------------------------------------
# Code file serving
# ---------------------------------------------------------------------------


@main.route("/code/<project>/<path:filename>")
def serve_code(project: str, filename: str):
    """Return raw source file content as plain text."""
    file_path = _resolve_code_path(project, filename)
    print(f"Serving code file: {file_path}")
    return (
        file_path.read_text(encoding="utf-8"),
        200,
        {"Content-Type": "text/plain; charset=utf-8"},
    )


@main.route("/code/<project>/<path:filename>/tokens")
def serve_tokens(project: str, filename: str):
    """Return tokenized source as JSON for the frontend syntax highlighter."""
    file_path = _resolve_code_path(project, filename)
    source = file_path.read_text(encoding="utf-8")
    tokens = (
        tokenize_python(source)
        if file_path.name.endswith(".py")
        else tokenize_plain(source)
    )
    return jsonify({"tokens": tokens, "source": source})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _resolve_code_path(project: str, filename: str) -> Path:
    """Sanitise and resolve a code file path; abort 404 if not found."""
    base_dir = Path(current_app.config["BASE_DIR"]).resolve()
    project_data = _get_project_by_name(project)
    code_root = _resolve_project_root(project, project_data)
    requested_path = Path(filename)
    if requested_path.is_absolute():
        abort(404)

    file_path = (code_root / requested_path).resolve()
    try:
        file_path.relative_to(base_dir)
    except ValueError:
        abort(404)

    if not file_path.exists():
        abort(404)

    return file_path


def _get_project_by_name(project_name: str) -> dict | None:
    projects_data = load_yaml("projects.yaml")
    return next((p for p in projects_data if p.get("name") == project_name), None)


def _resolve_project_root(project_name: str, project_data: dict | None) -> Path:
    base_dir = Path(current_app.config["BASE_DIR"]).resolve()
    if project_data and project_data.get("code_path"):
        code_dir: Path = current_app.config["CODE_DIR"]
        code_root = (code_dir / project_data["code_path"]).resolve()
        try:
            code_root.relative_to(base_dir)
        except ValueError:
            abort(404)
        return code_root

    code_dir: Path = current_app.config["CODE_DIR"]
    safe_project = Path(project_name).name
    return (code_dir / safe_project).resolve()


def _build_project_files(project_name: str, project_data: dict) -> list[str]:
    code_root = _resolve_project_root(project_name, project_data)
    explicit_files = project_data.get("files", []) or []
    main_file = project_data.get("main_file")
    if main_file and main_file not in explicit_files:
        explicit_files = [main_file, *explicit_files]

    whitelist_exts = {".py", ".js", ".md"}
    blacklist_dirs = {
        ".git",
        ".venv",
        "__pycache__",
        "build",
        "data",
        "dist",
        "node_modules",
        "static",
        "venv",
    }

    auto_files: list[str] = []
    for path in code_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in blacklist_dirs for part in path.parts):
            continue
        if path.suffix.lower() not in whitelist_exts:
            continue
        rel = path.relative_to(code_root).as_posix()
        auto_files.append(rel)

    explicit_normalized: list[str] = []
    base_dir = Path(current_app.config["BASE_DIR"]).resolve()
    for explicit in explicit_files:
        if not explicit:
            continue
        explicit_path = Path(str(explicit))
        if explicit_path.is_absolute():
            continue
        resolved = (code_root / explicit_path).resolve()
        try:
            resolved.relative_to(base_dir)
        except ValueError:
            continue
        if not resolved.exists():
            continue
        rel = Path(os.path.relpath(resolved, code_root)).as_posix()
        explicit_normalized.append(rel)

    combined = list(dict.fromkeys(explicit_normalized + auto_files))
    combined.sort()
    return combined
