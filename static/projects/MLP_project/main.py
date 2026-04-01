from pathlib import Path

from utils import JsonIterator


def example_usage(data: JsonIterator) -> None:
    idx = 200
    for i, item in enumerate(data.continuous_windows(3, label=True)):
        if i >= idx:
            print(item)
            break

    for line in data.windows(3, label=True):
        for i, window in enumerate(line):
            if i >= idx:
                print(window)
                break
        break


def main():
    path = Path("data/subtaskC_train.jsonl")
    if not path.exists():
        print("Data file not found")
        return
    data = JsonIterator(path)
    example_usage(data)


if __name__ == "__main__":
    main()
