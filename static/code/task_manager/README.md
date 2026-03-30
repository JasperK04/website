# Task Manager CLI

A command-line task management tool with persistent storage, tagging, and priority filtering.

## Features

- Add, list, complete, and remove tasks
- Tag-based and priority-based filtering
- Persistent JSON storage in your home directory
- Sortable by priority, creation date, or title
- Clean, readable output with status icons

## Installation

```bash
python main.py --help
```

## Usage

```bash
# Add a task
python main.py add "Write unit tests" --tag work --priority high

# List pending tasks
python main.py list

# List all tasks sorted by priority
python main.py list --status all --sort priority

# Mark done
python main.py done 1

# Remove a task
python main.py remove 2

# Show details
python main.py show 3
```

## Storage

Tasks are stored in `~/.task_manager.json`. The file is updated atomically
to prevent corruption.

## Priority Levels

- 🔴 `high`
- 🟡 `medium` (default)
- 🟢 `low`
