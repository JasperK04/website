import re
import statistics
from collections import Counter
from pathlib import Path
from typing import Sequence, TypedDict

from utils import JsonIterator

SENTENCE_RE = re.compile(r"[.!?]+")
PUNCTUATION = set(".,!?;:'\"()[]{}-")


class Stats(TypedDict):
    docs: int
    words: int
    chars: int
    sentences: int
    punctuation: int
    special: int
    words_per_doc: list[int]
    words_per_sentence: list[float]
    word_lengths: list[int]
    sentence_lengths: list[float]
    punctuation_freq: Counter[str]


def _avg(values: Sequence[float | int]) -> float:
    return statistics.mean(values) if values else 0.0


def _count_sentences(text: str) -> int:
    hits = SENTENCE_RE.findall(text)
    return max(1, len(hits)) if text.strip() else 0


def _accumulate_stats(text: str, stats: Stats) -> None:
    words = text.split()
    word_count = len(words)
    char_count = len(text)
    sentence_count = _count_sentences(text)

    stats["docs"] += 1
    stats["words"] += word_count
    stats["chars"] += char_count
    stats["sentences"] += sentence_count

    stats["words_per_doc"].append(word_count)
    stats["words_per_sentence"].append(
        word_count / sentence_count if sentence_count else 0.0
    )
    stats["word_lengths"].extend(len(word) for word in words)
    stats["sentence_lengths"].append(
        word_count / sentence_count if sentence_count else 0.0
    )

    punctuation_count = sum(1 for ch in text if ch in PUNCTUATION)
    special_count = sum(1 for ch in text if not ch.isalnum() and not ch.isspace())
    stats["punctuation"] += punctuation_count
    stats["special"] += special_count

    stats["punctuation_freq"].update(ch for ch in text if ch in PUNCTUATION)


def _init_stats() -> Stats:
    return {
        "docs": 0,
        "words": 0,
        "chars": 0,
        "sentences": 0,
        "punctuation": 0,
        "special": 0,
        "words_per_doc": [],
        "words_per_sentence": [],
        "word_lengths": [],
        "sentence_lengths": [],
        "punctuation_freq": Counter(),
    }


def _summary(stats: Stats) -> dict[str, float]:
    docs = stats["docs"]
    words = stats["words"]
    chars = stats["chars"]
    sentences = stats["sentences"]
    punctuation = stats["punctuation"]
    special = stats["special"]

    words_per_doc = stats["words_per_doc"]
    words_per_sentence = stats["words_per_sentence"]
    word_lengths = stats["word_lengths"]

    punctuation_per_1k = punctuation / chars * 1000 if chars else 0.0
    special_per_1k = special / chars * 1000 if chars else 0.0
    chars_per_doc = chars / docs if docs else 0.0
    sentences_per_doc = sentences / docs if docs else 0.0
    punctuation_per_doc = punctuation / docs if docs else 0.0
    special_per_doc = special / docs if docs else 0.0
    punctuation_per_100_words = punctuation / words * 100 if words else 0.0
    special_per_100_words = special / words * 100 if words else 0.0

    return {
        "docs": float(docs),
        "words": float(words),
        "chars": float(chars),
        "sentences": float(sentences),
        "avg_words_doc": _avg(words_per_doc),
        "min_words_doc": float(min(words_per_doc) if words_per_doc else 0),
        "max_words_doc": float(max(words_per_doc) if words_per_doc else 0),
        "avg_words_sentence": _avg(words_per_sentence),
        "avg_word_length": _avg(word_lengths),
        "min_word_length": float(min(word_lengths) if word_lengths else 0),
        "max_word_length": float(max(word_lengths) if word_lengths else 0),
        "punctuation": float(punctuation),
        "special": float(special),
        "punctuation_per_1k": punctuation_per_1k,
        "special_per_1k": special_per_1k,
        "chars_per_doc": chars_per_doc,
        "sentences_per_doc": sentences_per_doc,
        "punctuation_per_doc": punctuation_per_doc,
        "special_per_doc": special_per_doc,
        "punctuation_per_100_words": punctuation_per_100_words,
        "special_per_100_words": special_per_100_words,
    }


def _fmt(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    if abs(value * 10 - round(value * 10)) < 1e-9:
        return f"{value:.1f}"
    return f"{value:.2f}"


def _build_table(machine: Stats, human: Stats) -> str:
    machine_summary = _summary(machine)
    human_summary = _summary(human)

    rows = [
        ("Docs", "docs"),
        ("Words", "words"),
        ("Chars", "chars"),
        ("Sentences", "sentences"),
        ("Avg words/doc", "avg_words_doc"),
        ("Chars/doc", "chars_per_doc"),
        ("Sentences/doc", "sentences_per_doc"),
        ("Min words/doc", "min_words_doc"),
        ("Max words/doc", "max_words_doc"),
        ("Avg words/sentence", "avg_words_sentence"),
        ("Avg word length", "avg_word_length"),
        ("Min word length", "min_word_length"),
        ("Max word length", "max_word_length"),
        ("Punctuation count", "punctuation"),
        ("Special char count", "special"),
        ("Punctuation/doc", "punctuation_per_doc"),
        ("Special/doc", "special_per_doc"),
        ("Punctuation per 100 words", "punctuation_per_100_words"),
        ("Special per 100 words", "special_per_100_words"),
        ("Punctuation per 1k chars", "punctuation_per_1k"),
        ("Special per 1k chars", "special_per_1k"),
    ]

    lines = ["| stat | machine | human | delta |", "| --- | --- | --- | --- |"]
    for label, key in rows:
        machine_value = machine_summary[key]
        human_value = human_summary[key]
        delta = machine_value - human_value
        lines.append(
            f"| {label} | {_fmt(machine_value)} | {_fmt(human_value)} | {_fmt(delta)} |"
        )

    return "\n".join(lines)


def main() -> None:
    path = Path("data/subtaskC_train.jsonl")
    if not path.exists():
        print("Data file not found")
        return
    data = JsonIterator(path)
    human_stats = _init_stats()
    machine_stats = _init_stats()

    for item in data:
        text = str(item["text"])
        label_index = int(item["label"])
        words = text.split(" ")

        human_text = " ".join(words[:label_index])
        machine_text = " ".join(words[label_index:])

        _accumulate_stats(human_text, human_stats)
        _accumulate_stats(machine_text, machine_stats)

    table = _build_table(machine_stats, human_stats)
    print(table)
    with open("stats.md", "w", encoding="utf-8") as f:
        f.write(table)


if __name__ == "__main__":
    main()
