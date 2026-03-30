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
