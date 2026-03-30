"""
Personal Portfolio Website - Flask Backend
"""
import ast
import io
import os
import tokenize
from pathlib import Path

import yaml
from flask import Flask, abort, jsonify, render_template, request

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CODE_DIR = BASE_DIR / "static" / "code"


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

def load_yaml(filename: str) -> "list | dict":
    path = DATA_DIR / filename
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Context processor — inject profile + socials into every template
# ---------------------------------------------------------------------------

@app.context_processor
def inject_globals():
    return {
        "profile": load_yaml("profile.yaml"),
        "socials": load_yaml("socials.yaml"),
    }


# ---------------------------------------------------------------------------
# Fuzzy weighted search
# ---------------------------------------------------------------------------

def levenshtein(a: str, b: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * lb
        for j, cb in enumerate(b, 1):
            curr[j] = min(
                prev[j] + 1,
                curr[j - 1] + 1,
                prev[j - 1] + (0 if ca == cb else 1),
            )
        prev = curr
    return prev[lb]


def score_token_against_words(token: str, words: list[str], weight: int) -> int:
    """Score a single query token against a list of words from one field."""
    best = 0
    for word in words:
        word = word.lower()
        if token == word:
            best = max(best, 10 * weight)
        elif token in word or word in token:
            best = max(best, 6 * weight)
        elif levenshtein(token, word) <= 2:
            best = max(best, 3 * weight)
    return best


def extract_words(value) -> list[str]:
    """Flatten a string or list of strings into a list of lowercase words."""
    if not value:
        return []
    if isinstance(value, list):
        text = " ".join(str(v) for v in value)
    else:
        text = str(value)
    return text.lower().split()


def search_items(items: list[dict], query: str) -> list[dict]:
    """
    Perform token-based fuzzy weighted search on a list of items.
    Each item must have at minimum: name/title/company, tags, keywords, description, priority.
    Returns items sorted by score desc, then priority asc.
    """
    if not query or not query.strip():
        return sorted(items, key=lambda x: x.get("priority", 99))

    tokens = query.lower().split()
    threshold = len(tokens) * 5
    scored = []

    for item in items:
        total = 0
        for token in tokens:
            # Name / title field (weight 10)
            name_val = item.get("name") or item.get("display_name") or item.get("title") or \
                       item.get("role") or item.get("institution") or item.get("company") or ""
            total += score_token_against_words(token, extract_words(name_val), 10)

            # Tags (weight 6)
            total += score_token_against_words(token, extract_words(item.get("tags", [])), 6)

            # Keywords (weight 10)
            total += score_token_against_words(token, extract_words(item.get("keywords", [])), 10)

            # Description (weight 3)
            total += score_token_against_words(token, extract_words(item.get("description", "")), 3)

        if total >= threshold:
            scored.append((total, item.get("priority", 99), item))

    scored.sort(key=lambda x: (-x[0], x[1]))
    return [item for _, _, item in scored]


# ---------------------------------------------------------------------------
# Python syntax tokenizer
# ---------------------------------------------------------------------------

TOKEN_TYPE_MAP = {
    tokenize.COMMENT: "comment",
    tokenize.STRING: "string",
    tokenize.NUMBER: "number",
    tokenize.NEWLINE: "newline",
    tokenize.NL: "nl",
    tokenize.INDENT: "indent",
    tokenize.DEDENT: "dedent",
    tokenize.ENDMARKER: "endmarker",
    tokenize.ERRORTOKEN: "error",
}

PYTHON_KEYWORDS = frozenset([
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
    "try", "while", "with", "yield",
])

BUILTIN_NAMES = frozenset([
    "abs", "all", "any", "ascii", "bin", "bool", "breakpoint", "bytearray",
    "bytes", "callable", "chr", "classmethod", "compile", "complex",
    "delattr", "dict", "dir", "divmod", "enumerate", "eval", "exec",
    "filter", "float", "format", "frozenset", "getattr", "globals",
    "hasattr", "hash", "help", "hex", "id", "input", "int", "isinstance",
    "issubclass", "iter", "len", "list", "locals", "map", "max", "memoryview",
    "min", "next", "object", "oct", "open", "ord", "pow", "print", "property",
    "range", "repr", "reversed", "round", "set", "setattr", "slice",
    "sorted", "staticmethod", "str", "sum", "super", "tuple", "type",
    "vars", "zip", "__import__",
])

DECORATOR_NAMES = frozenset([
    "property", "staticmethod", "classmethod", "abstractmethod",
    "wraps", "app", "route", "login_required",
])


def tokenize_python(source: str) -> list[dict]:
    """
    Tokenize Python source code and return a list of token dicts.
    Each dict: {type, value, line, col}
    """
    tokens = []
    try:
        readline = io.StringIO(source).readline
        for tok in tokenize.generate_tokens(readline):
            tok_type = tok.type
            tok_val = tok.string
            line, col = tok.start

            if tok_type == tokenize.OP:
                t = "op"
            elif tok_type == tokenize.NAME:
                if tok_val in PYTHON_KEYWORDS:
                    t = "keyword"
                elif tok_val in BUILTIN_NAMES:
                    t = "builtin"
                else:
                    t = "name"
            else:
                t = TOKEN_TYPE_MAP.get(tok_type, "other")

            tokens.append({
                "type": t,
                "value": tok_val,
                "line": line,
                "col": col,
            })
    except tokenize.TokenError:
        # Return raw lines on tokenization failure
        for i, line_text in enumerate(source.splitlines(), 1):
            tokens.append({"type": "other", "value": line_text + "\n", "line": i, "col": 0})
    return tokens


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/education")
def education():
    query = request.args.get("q", "")
    items = load_yaml("education.yaml")
    if query:
        items = search_items(items, query)
    else:
        items = sorted(items, key=lambda x: x.get("priority", 99))
    return render_template("education.html", items=items, query=query)


@app.route("/jobs")
def jobs():
    query = request.args.get("q", "")
    items = load_yaml("jobs.yaml")
    if query:
        items = search_items(items, query)
    else:
        items = sorted(items, key=lambda x: x.get("priority", 99))
    return render_template("jobs.html", items=items, query=query)


@app.route("/projects")
def projects():
    query = request.args.get("q", "")
    items = load_yaml("projects.yaml")
    if query:
        items = search_items(items, query)
    else:
        items = sorted(items, key=lambda x: x.get("priority", 99))
    return render_template("projects.html", items=items, query=query)


@app.route("/projects/<project_name>")
def project_detail(project_name: str):
    projects_data = load_yaml("projects.yaml")
    project = next((p for p in projects_data if p["name"] == project_name), None)
    if not project:
        abort(404)
    return render_template("project_detail.html", project=project)


@app.route("/code/<project>/<path:filename>")
def serve_code(project: str, filename: str):
    """Serve raw source file content."""
    safe_project = Path(project).name
    safe_filename = Path(filename).name
    file_path = CODE_DIR / safe_project / safe_filename
    if not file_path.exists():
        abort(404)
    return file_path.read_text(encoding="utf-8"), 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/code/<project>/<path:filename>/tokens")
def serve_tokens(project: str, filename: str):
    """Serve tokenized Python code as JSON."""
    safe_project = Path(project).name
    safe_filename = Path(filename).name
    file_path = CODE_DIR / safe_project / safe_filename
    if not file_path.exists():
        abort(404)
    source = file_path.read_text(encoding="utf-8")
    if safe_filename.endswith(".py"):
        tokens = tokenize_python(source)
    else:
        # Non-Python: return as a single raw token per line
        tokens = [
            {"type": "other", "value": line + "\n", "line": i, "col": 0}
            for i, line in enumerate(source.splitlines(), 1)
        ]
    return jsonify({"tokens": tokens, "source": source})


if __name__ == "__main__":
    app.run(debug=True)
