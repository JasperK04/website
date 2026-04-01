## Installation

Create a virtual environment and install the dependencies.

```bash
uv sync
source .venv/bin/activate
```

## Usage

### main.py

Runs a small sanity check over a subset of windows from the training file and
counts line breaks in the human vs machine segments.

```bash
python main.py
```

### JsonIterator

Iterate over a JSONL file in fixed-size batches, yielding one parsed JSON
object per iteration.

```python
from utils import JsonIterator

it = JsonIterator("data/subtaskC_train.jsonl", batch_size=64)
for item in it:
    print(item["id"], item["text"], item["label"])
```

Windowed text access is available in two forms. Use `windows()` for per-line
iteration (nested loops), or `continuous_windows()` for a flat stream of window
dicts. The `window` argument is the number of words on each side of the center
word.

```python
from utils import JsonIterator

it = JsonIterator("data/subtaskC_train.jsonl")
for line in it.windows(3, label=True):
    for item in line:
        print(item["text"], item["label"])
```

```python
from utils import JsonIterator

it = JsonIterator("data/subtaskC_train.jsonl")
for item in it.continuous_windows(3, label=True):
    print(item["text"], item["label"])
```