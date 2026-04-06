"""
URL routes for the portfolio application.
Registered as the 'main' Blueprint.
"""

import fnmatch
import random
from pathlib import Path

from flask import Blueprint, abort, current_app, jsonify, render_template, request

from .syntax_code import tokenize_plain
from .syntax_code import tokenize_source as tokenize_code_source
from .syntax_data import tokenize_json, tokenize_markup, tokenize_yaml
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


def _load_list(filename: str) -> list[dict]:
    data = load_yaml(filename)
    return data if isinstance(data, list) else []


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
    programs = _load_list("courses.yaml")
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
    programs = _load_list("courses.yaml")
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


def _build_course_search_items() -> list[dict]:
    programs = _load_list("courses.yaml")
    _normalize_course_structure(programs)
    items: list[dict] = []
    for program in programs:
        program_name = program.get("program")
        institution = program.get("institution")
        degree = program.get("degree")
        for course in _iter_courses(program):
            entry = dict(course)
            entry["program"] = program_name
            entry["institution"] = institution
            entry["degree"] = degree
            keywords: list[str] = []
            for value in (program_name, institution, degree):
                if value:
                    keywords.append(str(value))
            description = course.get("description")
            if description:
                keywords.append(str(description))
            topics = course.get("topics")
            if isinstance(topics, list):
                keywords.extend(str(topic) for topic in topics)
            elif topics:
                keywords.append(str(topics))
            entry["keywords"] = keywords
            items.append(entry)
    return items


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
    profile = load_yaml("profile.yaml")
    tagline = None
    if isinstance(profile, dict):
        value = profile.get("tagline")
        if isinstance(value, list) and value:
            tagline = random.choice(value)
        elif isinstance(value, str):
            tagline = value
    return render_template("index.html", tagline=tagline)


@main.route("/about")
def about():
    return render_template("about.html")


@main.route("/education")
def education():
    query = request.args.get("q", "")
    items = _load_list("education.yaml")
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
    programs = _load_list("courses.yaml")
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
    items = _load_list("jobs.yaml")
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
    items = _load_list("projects.yaml")
    items = (
        search_items(items, query)
        if query
        else sorted(items, key=lambda x: x.get("priority", 99))
    )
    return render_template("projects.html", items=items, query=query)


@main.route("/search")
def global_search():
    query = request.args.get("q", "").strip()
    projects: list[dict] = []
    education_items: list[dict] = []
    jobs_items: list[dict] = []
    courses_items: list[dict] = []
    has_results = False

    if query:
        projects = search_items(_load_list("projects.yaml"), query)[:3]

        education_items = _load_list("education.yaml")
        averages = _build_course_average_lookup()
        course_search = _build_course_search_lookup()
        for item in education_items:
            courses_id = item.get("courses_id")
            if courses_id and courses_id in averages:
                item["average_grade"] = f"{averages[courses_id]:.1f}"
            if courses_id and courses_id in course_search:
                keywords = item.get("keywords") or []
                if not isinstance(keywords, list):
                    keywords = [str(keywords)]
                item["keywords"] = keywords + course_search[courses_id]
        education_items = search_items(education_items, query)[:3]

        jobs_items = search_items(_load_list("jobs.yaml"), query)[:3]

        courses_items = search_items(_build_course_search_items(), query)[:3]

        has_results = any([projects, education_items, jobs_items, courses_items])

    return render_template(
        "search.html",
        query=query,
        projects=projects,
        education=education_items,
        jobs=jobs_items,
        courses=courses_items,
        has_results=has_results,
    )


@main.route("/projects/<project_name>")
def project_detail(project_name: str):
    projects_data = load_yaml("projects.yaml")
    project = next((p for p in projects_data if p["name"] == project_name), None)
    if not project:
        abort(404)
    project_data = dict(project)
    code_root = _resolve_project_root(project_name, project_data)
    code_dir: Path = current_app.config["CODE_DIR"]
    try:
        project_data["asset_root"] = code_root.relative_to(code_dir).as_posix()
    except ValueError:
        project_data["asset_root"] = None
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
        tokens = tokenize_code_source(source, "python", current_app.config["DATA_DIR"])
    elif file_path.name.endswith(".js"):
        tokens = tokenize_code_source(
            source, "javascript", current_app.config["DATA_DIR"]
        )
    elif file_path.name.endswith(".asm"):
        tokens = tokenize_code_source(source, "asm", current_app.config["DATA_DIR"])
    elif file_path.name.endswith(".json"):
        tokens = tokenize_json(source)
    elif file_path.name.endswith((".yaml", ".yml")):
        tokens = tokenize_yaml(source)
    elif file_path.name.endswith(".xml"):
        tokens = tokenize_markup(source)
    elif file_path.name.endswith(".html"):
        tokens = tokenize_markup(source)
    else:
        tokens = tokenize_plain(source)
    return jsonify({"tokens": tokens, "source": source})


@main.route("/code/<project>/snippet/tokens", methods=["POST"])
def serve_snippet_tokens(project: str):
    """Return tokenized source for Markdown code fences."""
    payload = request.get_json(silent=True) or {}
    source = payload.get("source", "") or ""
    language = (payload.get("language", "") or "").strip().lower()

    lang_map = {
        "py": "python",
        "python": "python",
        "python3": "python",
        "js": "javascript",
        "javascript": "javascript",
        "asm": "asm",
        "sh": "shell",
        "bash": "shell",
        "zsh": "shell",
        "shell": "shell",
    }
    data_map = {
        "json": "json",
        "yaml": "yaml",
        "yml": "yaml",
        "xml": "xml",
        "html": "html",
    }
    lang_key = lang_map.get(language, "")
    data_key = data_map.get(language, "")

    if data_key == "json":
        tokens = tokenize_json(source)
    elif data_key == "yaml":
        tokens = tokenize_yaml(source)
    elif data_key in {"xml", "html"}:
        tokens = tokenize_markup(source)
    elif lang_key:
        tokens = tokenize_code_source(source, lang_key, current_app.config["DATA_DIR"])
    else:
        tokens = tokenize_plain(source)

    return jsonify({"tokens": tokens})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _resolve_code_path(project: str, filename: str) -> Path:
    """Sanitize and resolve a code file path; abort 404 if not found."""
    base_dir = Path(current_app.config["BASE_DIR"]).resolve()

    def _has_wildcards(value: str) -> bool:
        return any(ch in value for ch in "*?[")

    def _is_safe_pattern(value: str) -> bool:
        if value.startswith("/"):
            return False
        parts = [p for p in value.split("/") if p not in ("", ".")]
        return ".." not in parts

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
    projects_data = _load_list("projects.yaml")
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
    render_config = load_yaml("syntax_lists.yaml")
    render_config = render_config if isinstance(render_config, dict) else {}
    global_whitelist = render_config.get("global_whitelist", []) or []
    global_blacklist = render_config.get("global_blacklist", []) or []

    main_file = project_data.get("main_file")
    project_whitelist = project_data.get("file_whitelist", []) or []
    legacy_files = project_data.get("files", []) or []
    project_blacklist = project_data.get("file_blacklist", []) or []
    if main_file:
        project_whitelist = [main_file, *project_whitelist]
    if legacy_files:
        project_whitelist = [*legacy_files, *project_whitelist]

    base_dir = Path(current_app.config["BASE_DIR"]).resolve()

    def _has_wildcards(value: str) -> bool:
        return any(ch in value for ch in "*?[")

    def _is_safe_pattern(value: str) -> bool:
        if value.startswith("/"):
            return False
        parts = [p for p in value.split("/") if p not in ("", ".")]
        return ".." not in parts

    def _prepare_filters(
        entries: list[str],
        allow_exts: bool = True,
        allow_dirs: bool = True,
        allow_files: bool = True,
    ) -> list[tuple[str, str]]:
        prepared: list[tuple[str, str]] = []
        for entry in entries:
            if not entry:
                continue
            entry_text = str(entry).strip()
            if not entry_text:
                continue
            if not _is_safe_pattern(entry_text):
                continue
            if entry_text.startswith(".") and "/" not in entry_text:
                if not allow_exts:
                    continue
                prepared.append((entry_text.lower(), "ext"))
                continue
            is_dir = entry_text.endswith("/")
            entry_clean = entry_text.rstrip("/")
            if _has_wildcards(entry_clean):
                rel = entry_clean
            else:
                entry_path = Path(entry_clean)
                if entry_path.is_absolute():
                    continue
                resolved = (code_root / entry_clean).resolve()
                try:
                    resolved.relative_to(base_dir)
                    resolved.relative_to(code_root)
                except ValueError:
                    continue
                if not resolved.exists():
                    continue
                rel = resolved.relative_to(code_root).as_posix()
                if resolved.is_dir():
                    is_dir = True
            if is_dir:
                if not allow_dirs:
                    continue
                prepared.append((f"{rel.rstrip('/')}/", "dir"))
            else:
                if not allow_files:
                    continue
                prepared.append((rel, "file"))
        return prepared

    project_whitelist_filters = _prepare_filters(
        project_whitelist,
        allow_exts=True,
        allow_dirs=False,
        allow_files=True,
    )
    project_blacklist_filters = _prepare_filters(
        project_blacklist,
        allow_exts=False,
        allow_dirs=True,
        allow_files=True,
    )
    global_whitelist_filters = _prepare_filters(
        global_whitelist,
        allow_exts=True,
        allow_dirs=True,
        allow_files=True,
    )
    global_blacklist_filters = _prepare_filters(
        global_blacklist,
        allow_exts=False,
        allow_dirs=True,
        allow_files=True,
    )

    def _split_filters(
        filters: list[tuple[str, str]],
    ) -> tuple[set[str], list[str], set[str]]:
        exts: set[str] = set()
        dirs: list[str] = []
        files: set[str] = set()
        for filter_path, filter_type in filters:
            if filter_type == "ext":
                exts.add(filter_path)
            elif filter_type == "dir":
                dirs.append(filter_path)
            else:
                files.add(filter_path)
        return exts, dirs, files

    global_whitelist_exts, global_whitelist_dirs, global_whitelist_files = (
        _split_filters(global_whitelist_filters)
    )
    global_blacklist_exts, global_blacklist_dirs, global_blacklist_files = (
        _split_filters(global_blacklist_filters)
    )

    def _matches_dirs(rel_path: str, dirs: list[str]) -> bool:
        for dir_path in dirs:
            if _has_wildcards(dir_path):
                if fnmatch.fnmatch(rel_path, f"{dir_path}*"):
                    return True
            else:
                if rel_path == dir_path.rstrip("/") or rel_path.startswith(dir_path):
                    return True
        return False

    def _matches_filters(rel_path: str, filters: list[tuple[str, str]]) -> bool:
        rel_lower = rel_path.lower()
        for filter_path, filter_type in filters:
            if filter_type == "dir":
                if _matches_dirs(rel_path, [filter_path]):
                    return True
            elif filter_type == "file":
                if _has_wildcards(filter_path):
                    if fnmatch.fnmatch(rel_path, filter_path):
                        return True
                elif rel_path == filter_path:
                    return True
            elif _has_wildcards(filter_path):
                if fnmatch.fnmatch(path.suffix.lower(), filter_path):
                    return True
            elif rel_lower.endswith(filter_path):
                return True
        return False

    if not code_root.exists():
        return []

    visible_files: list[str] = []
    for path in code_root.rglob("*"):
        if not path.is_file():
            continue
        rel_path = path.relative_to(code_root).as_posix()
        project_whitelisted = _matches_filters(rel_path, project_whitelist_filters)
        project_blacklisted = _matches_filters(rel_path, project_blacklist_filters)

        if project_whitelisted:
            visible_files.append(rel_path)
            continue
        if project_blacklisted:
            continue

        if any(
            fnmatch.fnmatch(rel_path, pattern)
            if _has_wildcards(pattern)
            else rel_path == pattern
            for pattern in global_whitelist_files
        ):
            visible_files.append(rel_path)
            continue
        if any(
            fnmatch.fnmatch(rel_path, pattern)
            if _has_wildcards(pattern)
            else rel_path == pattern
            for pattern in global_blacklist_files
        ):
            continue

        if _matches_dirs(rel_path, global_whitelist_dirs):
            visible_files.append(rel_path)
            continue
        if _matches_dirs(rel_path, global_blacklist_dirs):
            continue

        if global_blacklist_exts and path.suffix.lower() in global_blacklist_exts:
            continue
        if global_whitelist_exts and path.suffix.lower() not in global_whitelist_exts:
            continue
        visible_files.append(rel_path)

    visible_files = list(dict.fromkeys(visible_files))
    visible_files.sort()
    return visible_files


@main.app_errorhandler(404)
@main.route("/404")
def error_404(error=None):
    return render_template("404.html"), 404
