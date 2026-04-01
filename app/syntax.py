"""
Config-driven syntax parser for multiple languages.

Loads per-language keywords and builtins from a server-side JSON file.
"""

from __future__ import annotations

import json
from pathlib import Path

_LANGUAGE_CACHE: dict[Path, dict] = {}


def load_language_config(data_dir: Path) -> dict:
    path = data_dir / "syntax_languages.json"
    if path in _LANGUAGE_CACHE:
        return _LANGUAGE_CACHE[path]
    config = json.loads(path.read_text(encoding="utf-8"))
    _LANGUAGE_CACHE[path] = config
    return config


def tokenize_source(source: str, language: str, data_dir: Path) -> "list[dict]":
    config = load_language_config(data_dir)
    alias_map = {
        "bash": "shell",
        "sh": "shell",
        "zsh": "shell",
        "python3": "python",
    }
    language = alias_map.get(language, language)
    lang = config.get(language)
    if not lang:
        return tokenize_plain(source)
    return _tokenize_generic(source, lang)


def _tokenize_generic(source: str, lang: dict) -> "list[dict]":
    tokens: list[dict] = []
    i = 0
    line = 1
    col = 0
    length = len(source)

    keywords = set(lang.get("keywords", []))
    builtins = set(lang.get("builtins", []))
    operators = sorted(lang.get("operators", []), key=len, reverse=True)
    line_comments = lang.get("line_comments", [])
    block_comments = lang.get("block_comments", [])
    delimiters = sorted(lang.get("string_delimiters", []), key=len, reverse=True)
    ident_conf = lang.get("identifier", {})
    extra_start = set(ident_conf.get("extra_start", ""))
    extra_part = set(ident_conf.get("extra_part", ""))

    def add_token(tok_type: str, value: str, start_line: int, start_col: int) -> None:
        if "\n" in value:
            parts = value.split("\n")
            for idx, part in enumerate(parts):
                part_line = start_line + idx
                part_col = start_col if idx == 0 else 0
                tokens.append(
                    {
                        "type": tok_type,
                        "value": part,
                        "line": part_line,
                        "col": part_col,
                    }
                )
        else:
            tokens.append(
                {"type": tok_type, "value": value, "line": start_line, "col": start_col}
            )

    def advance(value: str) -> None:
        nonlocal line, col
        if "\n" in value:
            parts = value.split("\n")
            line += len(parts) - 1
            col = len(parts[-1])
        else:
            col += len(value)

    def is_ident_start(ch: str) -> bool:
        return ch.isalpha() or ch in extra_start

    def is_ident_part(ch: str) -> bool:
        return ch.isalnum() or ch in extra_part

    while i < length:
        ch = source[i]

        if ch == "\n":
            line += 1
            col = 0
            i += 1
            continue

        if ch.isspace():
            col += 1
            i += 1
            continue

        comment_matched = False
        for marker in line_comments:
            if source.startswith(marker, i):
                start_line, start_col = line, col
                end = source.find("\n", i)
                if end == -1:
                    end = length
                value = source[i:end]
                add_token("comment", value, start_line, start_col)
                advance(value)
                i = end
                comment_matched = True
                break
        if comment_matched:
            continue

        block_matched = False
        for block in block_comments:
            start = block.get("start", "")
            end = block.get("end", "")
            if start and source.startswith(start, i):
                start_line, start_col = line, col
                j = source.find(end, i + len(start))
                if j == -1:
                    j = length
                else:
                    j += len(end)
                value = source[i:j]
                add_token("comment", value, start_line, start_col)
                advance(value)
                i = j
                block_matched = True
                break
        if block_matched:
            continue

        string_matched = False
        for delim in delimiters:
            if source.startswith(delim, i):
                start_line, start_col = line, col
                j = i + len(delim)
                escaped = False
                while j < length:
                    if source.startswith(delim, j):
                        j += len(delim)
                        break
                    c = source[j]
                    if escaped:
                        escaped = False
                    elif c == "\\" and len(delim) == 1:
                        escaped = True
                    j += 1
                value = source[i:j]
                add_token("string", value, start_line, start_col)
                advance(value)
                i = j
                string_matched = True
                break
        if string_matched:
            continue

        if ch.isdigit():
            start_line, start_col = line, col
            j = i + 1
            while j < length and (source[j].isdigit() or source[j] in {".", "_"}):
                j += 1
            value = source[i:j]
            add_token("number", value, start_line, start_col)
            advance(value)
            i = j
            continue

        if is_ident_start(ch):
            start_line, start_col = line, col
            j = i + 1
            while j < length and is_ident_part(source[j]):
                j += 1
            value = source[i:j]
            if value in keywords:
                tok_type = "keyword"
            elif value in builtins:
                tok_type = "builtin"
            else:
                tok_type = "name"
            add_token(tok_type, value, start_line, start_col)
            advance(value)
            i = j
            continue

        start_line, start_col = line, col
        matched_op = None
        for op in operators:
            if source.startswith(op, i):
                matched_op = op
                break
        if matched_op:
            add_token("op", matched_op, start_line, start_col)
            advance(matched_op)
            i += len(matched_op)
            continue

        add_token("op", ch, start_line, start_col)
        advance(ch)
        i += 1

    return tokens


def tokenize_plain(source: str) -> "list[dict]":
    """Return one 'other' token per line for unconfigured files."""
    return [
        {"type": "other", "value": line + "\n", "line": i, "col": 0}
        for i, line in enumerate(source.splitlines(), 1)
    ]
