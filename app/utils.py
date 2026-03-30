"""
Utility helpers: YAML loading and fuzzy weighted search.
"""
import yaml
from flask import current_app


def load_yaml(filename: str) -> "list | dict":
    """Load and return parsed YAML from the configured data directory."""
    path = current_app.config["DATA_DIR"] / filename
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


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


def score_token_against_words(token: str, words: "list[str]", weight: int) -> int:
    """Score a single query token against words from one field."""
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


def extract_words(value) -> "list[str]":
    """Flatten a string or list of strings into a list of lowercase words."""
    if not value:
        return []
    if isinstance(value, list):
        text = " ".join(str(v) for v in value)
    else:
        text = str(value)
    return text.lower().split()


def search_items(items: "list[dict]", query: str) -> "list[dict]":
    """
    Token-based fuzzy weighted search across name, tags, keywords, description.

    Field weights: name/title ×10, keywords ×10, tags ×6, description ×3.
    Match scores:  exact ×10, substring ×6, fuzzy (distance≤2) ×3.
    Threshold:     total_score ≥ len(tokens) × 5.
    Sort:          score desc, then priority asc.
    """
    if not query or not query.strip():
        return sorted(items, key=lambda x: x.get("priority", 99))

    tokens = query.lower().split()
    threshold = len(tokens) * 5
    scored = []

    for item in items:
        total = 0
        for token in tokens:
            name_val = (
                item.get("name")
                or item.get("display_name")
                or item.get("title")
                or item.get("role")
                or item.get("institution")
                or item.get("company")
                or ""
            )
            total += score_token_against_words(token, extract_words(name_val), 10)
            total += score_token_against_words(token, extract_words(item.get("tags", [])), 6)
            total += score_token_against_words(token, extract_words(item.get("keywords", [])), 10)
            total += score_token_against_words(token, extract_words(item.get("description", "")), 3)

        if total >= threshold:
            scored.append((total, item.get("priority", 99), item))

    scored.sort(key=lambda x: (-x[0], x[1]))
    return [item for _, _, item in scored]
