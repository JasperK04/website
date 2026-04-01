"""
Python-specific syntax parser.

Uses the standard `tokenize` module to classify source tokens into
semantic categories for frontend syntax highlighting.
"""

import io
import tokenize

# Mapping from tokenize constants → CSS token type names
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

PYTHON_KEYWORDS = frozenset(
    [
        "False",
        "None",
        "True",
        "and",
        "as",
        "assert",
        "async",
        "await",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "nonlocal",
        "not",
        "or",
        "pass",
        "raise",
        "return",
        "try",
        "while",
        "with",
        "yield",
    ]
)

BUILTIN_NAMES = frozenset(
    [
        "abs",
        "all",
        "any",
        "ascii",
        "bin",
        "bool",
        "breakpoint",
        "bytearray",
        "bytes",
        "callable",
        "chr",
        "classmethod",
        "compile",
        "complex",
        "delattr",
        "dict",
        "dir",
        "divmod",
        "enumerate",
        "eval",
        "exec",
        "filter",
        "float",
        "format",
        "frozenset",
        "getattr",
        "globals",
        "hasattr",
        "hash",
        "help",
        "hex",
        "id",
        "input",
        "int",
        "isinstance",
        "issubclass",
        "iter",
        "len",
        "list",
        "locals",
        "map",
        "max",
        "memoryview",
        "min",
        "next",
        "object",
        "oct",
        "open",
        "ord",
        "pow",
        "print",
        "property",
        "range",
        "repr",
        "reversed",
        "round",
        "set",
        "setattr",
        "slice",
        "sorted",
        "staticmethod",
        "str",
        "sum",
        "super",
        "tuple",
        "type",
        "vars",
        "zip",
        "__import__",
    ]
)

JS_KEYWORDS = frozenset(
    [
        "await",
        "break",
        "case",
        "catch",
        "class",
        "const",
        "continue",
        "debugger",
        "default",
        "delete",
        "do",
        "else",
        "export",
        "extends",
        "false",
        "finally",
        "for",
        "function",
        "if",
        "import",
        "in",
        "instanceof",
        "let",
        "new",
        "null",
        "return",
        "super",
        "switch",
        "this",
        "throw",
        "true",
        "try",
        "typeof",
        "var",
        "void",
        "while",
        "with",
        "yield",
    ]
)

JS_BUILTINS = frozenset(
    [
        "Array",
        "Boolean",
        "Date",
        "JSON",
        "Math",
        "Number",
        "Object",
        "Promise",
        "RegExp",
        "String",
        "Map",
        "Set",
        "WeakMap",
        "WeakSet",
        "console",
        "document",
        "window",
        "globalThis",
        "undefined",
        "NaN",
        "Infinity",
    ]
)


def tokenize_python(source: str) -> "list[dict]":
    """
    Tokenize Python source code and return structured token dicts.

    Each dict contains:
        type  – semantic CSS class name (keyword, string, comment, …)
        value – raw token text
        line  – 1-based line number
        col   – 0-based column offset
    """
    tokens: list[dict] = []
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

            if "\n" in tok_val:
                parts = tok_val.split("\n")
                for idx, part in enumerate(parts):
                    part_line = line + idx
                    part_col = col if idx == 0 else 0
                    tokens.append(
                        {"type": t, "value": part, "line": part_line, "col": part_col}
                    )
            else:
                tokens.append({"type": t, "value": tok_val, "line": line, "col": col})

    except tokenize.TokenError:
        # Graceful fallback: return source as plain line tokens
        for i, line_text in enumerate(source.splitlines(), 1):
            tokens.append(
                {"type": "other", "value": line_text + "\n", "line": i, "col": 0}
            )

    return tokens


def tokenize_plain(source: str) -> "list[dict]":
    """Return one 'other' token per line for non-Python files."""
    return [
        {"type": "other", "value": line + "\n", "line": i, "col": 0}
        for i, line in enumerate(source.splitlines(), 1)
    ]


def tokenize_javascript(source: str) -> "list[dict]":
    """
    Tokenize JavaScript source into lightweight semantic tokens.

    Each dict contains:
        type  – CSS class name (keyword, string, comment, number, op, builtin, name)
        value – raw token text
        line  – 1-based line number
        col   – 0-based column offset
    """
    tokens: list[dict] = []
    i = 0
    line = 1
    col = 0
    length = len(source)

    operators = {
        "===",
        "!==",
        "==",
        "!=",
        ">=",
        "<=",
        "=>",
        "++",
        "--",
        "+=",
        "-=",
        "*=",
        "/=",
        "%=",
        "&&",
        "||",
        "??",
        "?.",
        "<<",
        ">>",
        "**",
    }

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

        if ch == "/" and i + 1 < length and source[i + 1] == "/":
            start_line, start_col = line, col
            end = source.find("\n", i)
            if end == -1:
                end = length
            value = source[i:end]
            add_token("comment", value, start_line, start_col)
            col += len(value)
            i = end
            continue

        if ch == "/" and i + 1 < length and source[i + 1] == "*":
            start_line, start_col = line, col
            j = i + 2
            while j < length - 1 and not (source[j] == "*" and source[j + 1] == "/"):
                if source[j] == "\n":
                    line += 1
                    col = 0
                else:
                    col += 1
                j += 1
            j = min(j + 2, length)
            value = source[i:j]
            add_token("comment", value, start_line, start_col)
            i = j
            continue

        if ch in {"'", '"', "`"}:
            quote = ch
            start_line, start_col = line, col
            j = i + 1
            escaped = False
            while j < length:
                c = source[j]
                if c == "\n" and quote != "`":
                    break
                if escaped:
                    escaped = False
                elif c == "\\":
                    escaped = True
                elif c == quote:
                    j += 1
                    break
                j += 1
            value = source[i:j]
            add_token("string", value, start_line, start_col)
            lines = value.split("\n")
            if len(lines) > 1:
                line += len(lines) - 1
                col = len(lines[-1])
            else:
                col += len(value)
            i = j
            continue

        if ch.isdigit():
            start_line, start_col = line, col
            j = i + 1
            while j < length and (source[j].isdigit() or source[j] in {".", "_"}):
                j += 1
            value = source[i:j]
            add_token("number", value, start_line, start_col)
            col += len(value)
            i = j
            continue

        if ch.isalpha() or ch in {"_", "$"}:
            start_line, start_col = line, col
            j = i + 1
            while j < length and (source[j].isalnum() or source[j] in {"_", "$"}):
                j += 1
            value = source[i:j]
            if value in JS_KEYWORDS:
                tok_type = "keyword"
            elif value in JS_BUILTINS:
                tok_type = "builtin"
            else:
                tok_type = "name"
            add_token(tok_type, value, start_line, start_col)
            col += len(value)
            i = j
            continue

        start_line, start_col = line, col
        two = source[i : i + 2]
        three = source[i : i + 3]
        if three in operators:
            add_token("op", three, start_line, start_col)
            col += 3
            i += 3
        elif two in operators:
            add_token("op", two, start_line, start_col)
            col += 2
            i += 2
        else:
            add_token("op", ch, start_line, start_col)
            col += 1
            i += 1

    return tokens
