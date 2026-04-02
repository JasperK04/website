"""
Tokenizer for structured data formats (JSON, YAML, XML/HTML).
"""

from __future__ import annotations


def tokenize_json(source: str) -> "list[dict]":
    tokens: list[dict] = []
    i = 0
    line = 1
    col = 0
    length = len(source)

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

    def peek_nonspace(idx: int) -> int:
        while idx < length and source[idx].isspace():
            idx += 1
        return idx

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

        if ch in "{}[]:,":
            add_token("op", ch, line, col)
            advance(ch)
            i += 1
            continue

        if ch == '"':
            start_line, start_col = line, col
            j = i + 1
            escaped = False
            while j < length:
                c = source[j]
                if escaped:
                    escaped = False
                elif c == "\\":
                    escaped = True
                elif c == '"':
                    j += 1
                    break
                j += 1
            value = source[i:j]
            next_idx = peek_nonspace(j)
            tok_type = (
                "name" if next_idx < length and source[next_idx] == ":" else "string"
            )
            add_token(tok_type, value, start_line, start_col)
            advance(value)
            i = j
            continue

        if ch.isdigit() or ch == "-":
            start_line, start_col = line, col
            j = i + 1
            while j < length and (
                source[j].isdigit() or source[j] in {".", "e", "E", "+", "-"}
            ):
                j += 1
            value = source[i:j]
            add_token("number", value, start_line, start_col)
            advance(value)
            i = j
            continue

        if ch.isalpha():
            start_line, start_col = line, col
            j = i + 1
            while j < length and source[j].isalpha():
                j += 1
            value = source[i:j]
            tok_type = "keyword" if value in {"true", "false", "null"} else "name"
            add_token(tok_type, value, start_line, start_col)
            advance(value)
            i = j
            continue

        add_token("op", ch, line, col)
        advance(ch)
        i += 1

    return tokens


def tokenize_yaml(source: str) -> "list[dict]":
    tokens: list[dict] = []
    i = 0
    line = 1
    col = 0
    length = len(source)

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

        if ch == "#":
            start_line, start_col = line, col
            j = source.find("\n", i)
            if j == -1:
                j = length
            value = source[i:j]
            add_token("comment", value, start_line, start_col)
            advance(value)
            i = j
            continue

        if ch in "-:":
            add_token("op", ch, line, col)
            advance(ch)
            i += 1
            continue

        if ch in {'"', "'"}:
            start_line, start_col = line, col
            delim = ch
            j = i + 1
            escaped = False
            while j < length:
                c = source[j]
                if escaped:
                    escaped = False
                elif c == "\\" and delim == '"':
                    escaped = True
                elif c == delim:
                    j += 1
                    break
                j += 1
            value = source[i:j]
            add_token("string", value, start_line, start_col)
            advance(value)
            i = j
            continue

        if ch.isdigit() or (ch == "-" and i + 1 < length and source[i + 1].isdigit()):
            start_line, start_col = line, col
            j = i + 1
            while j < length and (source[j].isdigit() or source[j] in {".", "_"}):
                j += 1
            value = source[i:j]
            add_token("number", value, start_line, start_col)
            advance(value)
            i = j
            continue

        if ch.isalpha() or ch in {"_"}:
            start_line, start_col = line, col
            j = i + 1
            while j < length and (source[j].isalnum() or source[j] in {"_", "-"}):
                j += 1
            value = source[i:j]
            next_idx = j
            while next_idx < length and source[next_idx].isspace():
                if source[next_idx] == "\n":
                    break
                next_idx += 1
            tok_type = (
                "name" if next_idx < length and source[next_idx] == ":" else "keyword"
            )
            if value.lower() in {"true", "false", "null", "yes", "no", "on", "off"}:
                tok_type = "keyword"
            add_token(tok_type, value, start_line, start_col)
            advance(value)
            i = j
            continue

        add_token("op", ch, line, col)
        advance(ch)
        i += 1

    return tokens


def tokenize_markup(source: str) -> "list[dict]":
    tokens: list[dict] = []
    i = 0
    line = 1
    col = 0
    length = len(source)

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

    def read_name(start: int) -> int:
        j = start
        while j < length and (source[j].isalnum() or source[j] in {"_", "-", ":", "."}):
            j += 1
        return j

    while i < length:
        ch = source[i]
        if source.startswith("<!--", i):
            start_line, start_col = line, col
            j = source.find("-->", i + 4)
            if j == -1:
                j = length
            else:
                j += 3
            value = source[i:j]
            add_token("comment", value, start_line, start_col)
            advance(value)
            i = j
            continue

        if ch == "<":
            start_line, start_col = line, col
            if source.startswith("</", i):
                add_token("punct", "</", start_line, start_col)
                advance("</")
                i += 2
            else:
                add_token("punct", "<", start_line, start_col)
                advance("<")
                i += 1

            name_start = i
            name_end = read_name(i)
            if name_end > name_start:
                value = source[name_start:name_end]
                add_token("keyword", value, line, col)
                advance(value)
                i = name_end

            while i < length:
                if source.startswith("/>", i):
                    add_token("punct", "/>", line, col)
                    advance("/>")
                    i += 2
                    break
                if source[i] == ">":
                    add_token("punct", ">", line, col)
                    advance(">")
                    i += 1
                    break
                if source[i].isspace():
                    if source[i] == "\n":
                        line += 1
                        col = 0
                    else:
                        col += 1
                    i += 1
                    continue

                attr_start = i
                attr_end = read_name(i)
                if attr_end > attr_start:
                    value = source[attr_start:attr_end]
                    add_token("attr", value, line, col)
                    advance(value)
                    i = attr_end

                while i < length and source[i].isspace():
                    if source[i] == "\n":
                        line += 1
                        col = 0
                    else:
                        col += 1
                    i += 1

                if i < length and source[i] == "=":
                    add_token("op", "=", line, col)
                    advance("=")
                    i += 1

                    while i < length and source[i].isspace():
                        if source[i] == "\n":
                            line += 1
                            col = 0
                        else:
                            col += 1
                        i += 1

                    if i < length and source[i] in {'"', "'"}:
                        delim = source[i]
                        start_line, start_col = line, col
                        j = i + 1
                        while j < length and source[j] != delim:
                            j += 1
                        if j < length:
                            j += 1
                        value = source[i:j]
                        add_token("string", value, start_line, start_col)
                        advance(value)
                        i = j
                    else:
                        start_line, start_col = line, col
                        j = i
                        while (
                            j < length
                            and not source[j].isspace()
                            and source[j] not in {">", "/"}
                        ):
                            j += 1
                        value = source[i:j]
                        if value:
                            add_token("string", value, start_line, start_col)
                            advance(value)
                        i = j
            continue

        if ch == "\n":
            line += 1
            col = 0
            i += 1
            continue

        start_line, start_col = line, col
        j = i
        while j < length and source[j] not in {"<", "\n"}:
            j += 1
        value = source[i:j]
        if value:
            add_token("other", value, start_line, start_col)
            advance(value)
        i = j

    return tokens
