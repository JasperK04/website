import io
import json
from collections.abc import Iterator
from pathlib import Path
from typing import TypedDict

type JsonObject = dict[str, str | int]
type JsonData = list[JsonObject]


class JsonWindow(TypedDict):
    text: str
    label: int | None


class JsonLine(str):
    """String wrapper that yields windowed segments when iterated.

    The instance value is the full line text. Extra attributes store window
    parameters so iteration can produce per-line windows without crossing line
    boundaries.
    """

    _label_index: int
    _window: int
    _label: bool

    def __new__(
        cls, text: str, label_index: int, window: int, label: bool
    ) -> "JsonLine":
        """Create a JsonLine with window configuration.

        Args:
            text: Full line text from the JSONL file.
            label_index: Word index where the label boundary occurs.
            window: Number of words on each side of the center word.
            label: Whether to emit 0/1 labels for the center word.
        """
        obj = super().__new__(cls, text)
        obj._label_index = label_index
        obj._window = window
        obj._label = label
        return obj

    def __iter__(self) -> Iterator[JsonWindow]:
        words = self.split(" ")
        start = self._window
        end = len(words) - self._window
        for center in range(start, end):
            window_words = " ".join(
                words[center - self._window : center + self._window + 1]
            )
            center_label = 0 if center < self._label_index else 1
            yield {
                "text": window_words,
                "label": center_label if self._label else None,
            }


class JsonIterator:
    """Iterate over a JSONL file in fixed-size batches.

    Each line is parsed with ``json.loads`` and returned as a Python object.
    Iteration is stateful and re-usable: calling ``iter()`` resets the reader.
    """

    def __init__(self, file_path: str | Path, batch_size: int = 64) -> None:
        """Create an iterator for a JSONL file.

        Args:
            file_path: Path to a JSON Lines (JSONL) file.
            batch_size: Number of lines to read per batch.
        """
        self.file_path: str | Path = file_path
        self.batch_size: int = batch_size
        self._file: io.TextIOWrapper | None = None
        self._buffer: list[JsonObject] = []
        self._buffer_index: int = 0

    def __iter__(self) -> "JsonIterator":
        """Return an iterator and reset internal state."""
        if self._file:
            self._file.close()
        self._file = open(self.file_path, "r", encoding="utf-8")
        self._buffer = []
        self._buffer_index = 0
        return self

    def __next__(self) -> JsonObject:
        """Return the next JSON value from the file."""
        if self._buffer_index >= len(self._buffer):
            self._load_batch()
            if not self._buffer:
                if self._file:
                    self._file.close()
                self._file = None
                raise StopIteration

        item = self._buffer[self._buffer_index]
        self._buffer_index += 1
        return item

    def continuous_windows(
        self, window: int, *, label: bool = False
    ) -> Iterator[JsonWindow]:
        """Yield fixed-size windows of words from each JSON line.

        Args:
            window: Number of words on each side of the center word.
            label: When True, also yield the binary label for the center word.

        Yields:
            A dict with keys ``text`` and ``label``. The ``text`` value contains
            the window as a string. The ``label`` value is None when
            ``label=False``, otherwise 0 when the center index is before the JSON
            ``label`` value, else 1.
        """
        if window < 0:
            raise ValueError("window must be >= 0")

        for item in self:
            text = str(item["text"])
            label_index = int(item["label"])
            words = text.split(" ")

            start = window
            end = len(words) - window
            for center in range(start, end):
                window_words = " ".join(words[center - window : center + window + 1])
                center_label = 0 if center < label_index else 1
                yield {
                    "text": window_words,
                    "label": center_label if label else None,
                }

    def windows(self, window: int, *, label: bool = False) -> Iterator[JsonLine]:
        """Yield per-line iterables that produce windows scoped to each line.

        Each yielded `JsonLine` is a string subclass representing the line text.
        Iterating it yields dicts with `text` (the window) and `label` (0/1 for
        the center word, or None when `label=False`). Windows never span across
        lines.
        """
        if window < 0:
            raise ValueError("window must be >= 0")

        for item in self:
            text = str(item["text"])
            label_index = int(item["label"])
            yield JsonLine(text, label_index, window, label)

    def _load_batch(self) -> None:
        """Load the next batch of JSON values into the buffer."""
        self._buffer = []
        self._buffer_index = 0
        assert self._file is not None, "File is not open"

        if self.batch_size < 0:
            for line in self._file:
                self._buffer.append(json.loads(line))
            return

        for _ in range(self.batch_size):
            line = self._file.readline()
            if not line:
                break
            self._buffer.append(json.loads(line))
