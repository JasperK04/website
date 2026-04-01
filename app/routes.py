"""
URL routes for the portfolio application.
Registered as the 'main' Blueprint.
"""

import os
from pathlib import Path

from flask import Blueprint, abort, current_app, jsonify, render_template, request

from .syntax import tokenize_plain, tokenize_source
from .utils import load_yaml, search_items

main = Blueprint("main", __name__)

MONTH_LOOKUP = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def _is_current(value: str | None) -> bool:
    if not value:
        return False
    return str(value).strip().lower() in {"current", "present"}


def _parse_month_year(value: str | None) -> int:
    if not value:
        return 0
    text = str(value).strip().lower()
    if _is_current(text):
        return 0
    parts = text.split()
    if len(parts) < 2:
        return 0
    month = MONTH_LOOKUP.get(parts[0][:3])
    try:
        year = int(parts[1])
    except ValueError:
        return 0
    if not month:
        return 0
    return year * 12 + month


def _is_tech_relevant(item: dict) -> bool:
    value = item.get("tech_relevant")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return False


def _job_sort_key(item: dict) -> tuple[int, int, int]:
    end_value = item.get("end")
    if _is_current(end_value):
        return (0, 0, item.get("priority", 99))
    end_score = _parse_month_year(end_value)
    return (1, -end_score, item.get("priority", 99))


def _parse_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip().replace(",", "."))
    except ValueError:
        return None


def _normalize_course_list(value) -> list[dict]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        nested = value.get("courses")
        return nested if isinstance(nested, list) else []
    return []


def _normalize_course_structure(programs: list[dict]) -> None:
    for program in programs:
        if "courses" in program:
            program["courses"] = _normalize_course_list(program.get("courses"))
        if "extra" in program and not isinstance(program.get("extra"), list):
            program["extra"] = []

        for year in program.get("years", []) or []:
            if "courses" in year:
                year["courses"] = _normalize_course_list(year.get("courses"))
            for semester in year.get("semesters", []) or []:
                if "courses" in semester:
                    semester["courses"] = _normalize_course_list(
                        semester.get("courses")
                    )
                for block in semester.get("blocks", []) or []:
                    if "courses" in block:
                        block["courses"] = _normalize_course_list(block.get("courses"))


def _iter_courses(program: dict) -> list[dict]:
    collected: list[dict] = []

    def add_courses(courses: list[dict] | None) -> None:
        if courses:
            collected.extend(courses)

    add_courses(_normalize_course_list(program.get("courses")))
    add_courses(program.get("extra"))

    for year in program.get("years", []) or []:
        add_courses(_normalize_course_list(year.get("courses")))
        for semester in year.get("semesters", []) or []:
            add_courses(_normalize_course_list(semester.get("courses")))
            for block in semester.get("blocks", []) or []:
                add_courses(_normalize_course_list(block.get("courses")))

    return collected


def _apply_course_stats(programs: list[dict]) -> None:
    for program in programs:
        courses = _iter_courses(program)
        grades: list[float] = []
        ects_total = 0.0
        for course in courses:
            grade = _parse_float(course.get("grade"))
            if grade is not None:
                grades.append(grade)
                ects = _parse_float(course.get("ects"))
                if ects is not None:
                    ects_total += ects

        program["average_grade"] = (
            round(sum(grades) / len(grades), 1) if grades else None
        )
        program["ects_total"] = (
            int(ects_total) if ects_total.is_integer() else round(ects_total, 2)
        )


def _build_course_average_lookup() -> dict[str, float]:
    programs = load_yaml("courses.yaml")
    _normalize_course_structure(programs)
    _apply_course_stats(programs)
    averages: dict[str, float] = {}
    for program in programs:
        program_id = program.get("id")
        average = program.get("average_grade")
        if program_id and isinstance(average, (int, float)):
            averages[program_id] = average
    return averages


def _build_course_search_lookup() -> dict[str, list[str]]:
    programs = load_yaml("courses.yaml")
    _normalize_course_structure(programs)
    lookup: dict[str, list[str]] = {}
    for program in programs:
        program_id = program.get("id")
        if not program_id:
            continue
        courses = _iter_courses(program)
        tokens: list[str] = []
        for course in courses:
            name = course.get("name")
            if name:
                tokens.append(str(name))
            description = course.get("description")
            if description:
                tokens.append(str(description))
            topics = course.get("topics")
            if isinstance(topics, list):
                tokens.extend(str(topic) for topic in topics)
            elif topics:
                tokens.append(str(topics))
        lookup[program_id] = tokens
    return lookup


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
    averages = _build_course_average_lookup()
    course_search = _build_course_search_lookup()
    for item in items:
        courses_id = item.get("courses_id")
        if courses_id and courses_id in averages:
            item["average_grade"] = f"{averages[courses_id]:.1f}"
        if courses_id and courses_id in course_search:
            keywords = item.get("keywords") or []
            if not isinstance(keywords, list):
                keywords = [str(keywords)]
            item["keywords"] = keywords + course_search[courses_id]
    items = (
        search_items(items, query)
        if query
        else sorted(items, key=lambda x: x.get("priority", 99))
    )
    return render_template("education.html", items=items, query=query)


@main.route("/courses")
@main.route("/courses/<program_id>")
def courses(program_id: str | None = None):
    programs = load_yaml("courses.yaml")
    _normalize_course_structure(programs)
    _apply_course_stats(programs)
    page_title = "Courses & Grades"
    if program_id:
        match = next((p for p in programs if p.get("id") == program_id), None)
        if not match:
            abort(404)
        programs = [match]
        page_title = f"Courses & Grades - {match.get('program') or match.get('degree') or match.get('institution') or ''}".strip(
            " -"
        )
    return render_template("courses.html", programs=programs, page_title=page_title)


@main.route("/jobs")
def jobs():
    query = request.args.get("q", "")
    tech = request.args.get("tech", "all")
    tech = "tech" if tech == "tech" else "all"
    items = load_yaml("jobs.yaml")
    if query:
        items = search_items(items, query)
    else:
        if tech == "tech":
            items = [item for item in items if _is_tech_relevant(item)]
        items = sorted(items, key=_job_sort_key)
    return render_template("jobs.html", items=items, query=query, tech=tech)


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
    if file_path.name.endswith(".py"):
        tokens = tokenize_source(source, "python", current_app.config["DATA_DIR"])
    elif file_path.name.endswith(".js"):
        tokens = tokenize_source(source, "javascript", current_app.config["DATA_DIR"])
    else:
        tokens = tokenize_plain(source)
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
        "img",
        "projects",
        "css",
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
