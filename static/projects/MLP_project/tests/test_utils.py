"""Pytest coverage for utils module."""

from pathlib import Path

import pytest

from utils import JsonIterator, JsonLine


def _write_jsonl(path: Path, lines: list[str]) -> None:
    path.write_text("".join(lines), encoding="utf-8")


def test_json_line_iteration():
    line = JsonLine("a b c d e", label_index=3, window=1, label=True)
    windows = list(line)
    assert windows == [
        {"text": "a b c", "label": 0},
        {"text": "b c d", "label": 0},
        {"text": "c d e", "label": 1},
    ]


def test_json_iterator_batches(tmp_path: Path):
    file_path = tmp_path / "data.jsonl"
    _write_jsonl(
        file_path,
        [
            '{"text": "a b c", "label": 1}\n',
            '{"text": "d e f", "label": 2}\n',
            '{"text": "g h i", "label": 0}\n',
        ],
    )

    iterator = JsonIterator(file_path, batch_size=2)
    items = list(iterator)
    assert [item["text"] for item in items] == ["a b c", "d e f", "g h i"]


def test_json_iterator_resets_on_iter(tmp_path: Path):
    file_path = tmp_path / "data.jsonl"
    _write_jsonl(
        file_path,
        [
            '{"text": "a b", "label": 0}\n',
            '{"text": "c d", "label": 1}\n',
        ],
    )

    iterator = JsonIterator(file_path, batch_size=1)
    first_pass = [item["text"] for item in iterator]
    second_pass = [item["text"] for item in iterator]
    assert first_pass == ["a b", "c d"]
    assert second_pass == ["a b", "c d"]


def test_windows_and_continuous_windows(tmp_path: Path):
    file_path = tmp_path / "data.jsonl"
    _write_jsonl(
        file_path,
        [
            '{"text": "a b c d", "label": 2}\n',
            '{"text": "e f g h", "label": 1}\n',
        ],
    )

    iterator = JsonIterator(file_path, batch_size=2)
    windowed_lines = list(iterator.windows(1, label=True))
    assert len(windowed_lines) == 2

    windows = [window for line in windowed_lines for window in line]
    assert windows[0] == {"text": "a b c", "label": 0}
    assert windows[-1] == {"text": "f g h", "label": 1}

    iterator = JsonIterator(file_path, batch_size=2)
    continuous = list(iterator.continuous_windows(1, label=True))
    assert continuous[0] == {"text": "a b c", "label": 0}
    assert continuous[-1] == {"text": "f g h", "label": 1}


def test_negative_window_raises(tmp_path: Path):
    file_path = tmp_path / "data.jsonl"
    _write_jsonl(file_path, ['{"text": "a b c", "label": 1}\n'])

    iterator = JsonIterator(file_path, batch_size=1)
    with pytest.raises(ValueError):
        list(iterator.windows(-1))

    iterator = JsonIterator(file_path, batch_size=1)
    with pytest.raises(ValueError):
        list(iterator.continuous_windows(-1))
