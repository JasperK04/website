"""
URL routes for the portfolio application.
Registered as the 'main' Blueprint.
"""
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
    items = search_items(items, query) if query else sorted(items, key=lambda x: x.get("priority", 99))
    return render_template("education.html", items=items, query=query)


@main.route("/jobs")
def jobs():
    query = request.args.get("q", "")
    items = load_yaml("jobs.yaml")
    items = search_items(items, query) if query else sorted(items, key=lambda x: x.get("priority", 99))
    return render_template("jobs.html", items=items, query=query)


@main.route("/projects")
def projects():
    query = request.args.get("q", "")
    items = load_yaml("projects.yaml")
    items = search_items(items, query) if query else sorted(items, key=lambda x: x.get("priority", 99))
    return render_template("projects.html", items=items, query=query)


@main.route("/projects/<project_name>")
def project_detail(project_name: str):
    projects_data = load_yaml("projects.yaml")
    project = next((p for p in projects_data if p["name"] == project_name), None)
    if not project:
        abort(404)
    return render_template("project_detail.html", project=project)


# ---------------------------------------------------------------------------
# Code file serving
# ---------------------------------------------------------------------------

@main.route("/code/<project>/<path:filename>")
def serve_code(project: str, filename: str):
    """Return raw source file content as plain text."""
    file_path = _resolve_code_path(project, filename)
    return file_path.read_text(encoding="utf-8"), 200, {"Content-Type": "text/plain; charset=utf-8"}


@main.route("/code/<project>/<path:filename>/tokens")
def serve_tokens(project: str, filename: str):
    """Return tokenized source as JSON for the frontend syntax highlighter."""
    file_path = _resolve_code_path(project, filename)
    source = file_path.read_text(encoding="utf-8")
    tokens = tokenize_python(source) if file_path.name.endswith(".py") else tokenize_plain(source)
    return jsonify({"tokens": tokens, "source": source})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _resolve_code_path(project: str, filename: str) -> Path:
    """Sanitise and resolve a code file path; abort 404 if not found."""
    code_dir: Path = current_app.config["CODE_DIR"]
    safe_project = Path(project).name
    safe_filename = Path(filename).name
    file_path = code_dir / safe_project / safe_filename
    if not file_path.exists():
        abort(404)
    return file_path
