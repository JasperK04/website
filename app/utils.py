"""
Utility helpers: YAML loading and fuzzy weighted search.
"""

import re

import yaml
from flask import current_app


def load_yaml(filename: str) -> list | dict:
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


def score_token_against_words(
    token: str,
    words: list[tuple[str, str]],
    weight: int,
    max_distance: int,
) -> tuple[int, str | None, str | None]:
    """Score a single query token against words from one field."""
    best = 0
    best_word: str | None = None
    best_kind: str | None = None
    for word_lower, word_original in words:
        if token == word_lower:
            score = 10 * weight
            kind = "exact"
        elif word_lower.startswith(token) or word_lower.endswith(token):
            score = 6 * weight
            kind = "partial"
        elif max_distance > 0 and levenshtein(token, word_lower) <= max_distance:
            score = 3 * weight
            kind = "fuzzy"
        else:
            continue

        if score > best:
            best = score
            best_word = word_original
            best_kind = kind

    return best, best_word, best_kind


def extract_word_pairs(value) -> list[tuple[str, str]]:
    """Return (lower, original) word pairs with punctuation stripped."""
    if not value:
        return []
    if isinstance(value, list):
        text = " ".join(str(v) for v in value)
    else:
        text = str(value)
    cleaned = re.sub(r"[^\w\s-]", " ", text)
    parts = [p for p in cleaned.split() if p]
    return [(part.lower(), part) for part in parts]


def extract_words(value) -> list[str]:
    """Flatten a string or list of strings into a list of lowercase words."""
    return [lower for lower, _ in extract_word_pairs(value)]


def search_items(items: list[dict], query: str) -> list[dict]:
    """
    Token-based fuzzy weighted search across name, tags, keywords, description.

    Field weights: name/title ×10, keywords ×10, tags ×6, description ×3.
    Match scores:  exact ×10, prefix/suffix ×6, fuzzy (distance≤max) ×3.
    Threshold:     total_score ≥ len(tokens) × 5.
    Sort:          score desc, then priority asc.
    """
    if not query or not query.strip():
        return sorted(items, key=lambda x: x.get("priority", 99))

    normalized = " ".join(query.lower().split())
    tokens = normalized.split()
    query_length = len(normalized.replace(" ", ""))
    if query_length <= 3:
        max_distance = 0
    elif query_length <= 6:
        max_distance = 1
    elif query_length <= 9:
        max_distance = 2
    else:
        max_distance = 3

    threshold = len(tokens) * 5
    scored = []

    for item in items:
        total = 0
        all_tokens_match = True
        fuzzy_matches: list[str] = []
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
            token_score = 0
            score, word, kind = score_token_against_words(
                token,
                extract_word_pairs(name_val),
                10,
                max_distance,
            )
            token_score += score
            if kind == "fuzzy" and word:
                fuzzy_matches.append(word)

            score, word, kind = score_token_against_words(
                token,
                extract_word_pairs(item.get("tags", [])),
                6,
                max_distance,
            )
            token_score += score
            if kind == "fuzzy" and word:
                fuzzy_matches.append(word)

            score, word, kind = score_token_against_words(
                token,
                extract_word_pairs(item.get("keywords", [])),
                10,
                max_distance,
            )
            token_score += score
            if kind == "fuzzy" and word:
                fuzzy_matches.append(word)

            score, word, kind = score_token_against_words(
                token,
                extract_word_pairs(item.get("description", "")),
                3,
                max_distance,
            )
            token_score += score
            if kind == "fuzzy" and word:
                fuzzy_matches.append(word)
            if token_score == 0:
                all_tokens_match = False
                break
            total += token_score

        if all_tokens_match and total >= threshold:
            result_item = dict(item)
            if fuzzy_matches:
                result_item["_fuzzy_matches"] = sorted(set(fuzzy_matches))
            scored.append((total, item.get("priority", 99), result_item))

    scored.sort(key=lambda x: (-x[0], x[1]))
    return [item for _, _, item in scored]
