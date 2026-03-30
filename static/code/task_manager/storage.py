"""
Task Manager CLI - Persistent Storage Layer
Handles reading and writing tasks to a JSON file.
"""
import json
import os
import time
from typing import Optional


DEFAULT_DB_PATH = os.path.expanduser("~/.task_manager.json")
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


class TaskStorage:
    """Manages persistent task storage using a JSON file."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Create the database file if it doesn't exist."""
        if not os.path.exists(self.db_path):
            self._write({"tasks": [], "next_id": 1})

    def _read(self) -> dict:
        """Read and return the database contents."""
        with open(self.db_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _write(self, data: dict) -> None:
        """Write data to the database file atomically."""
        tmp_path = self.db_path + ".tmp"
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, self.db_path)

    def add_task(
        self,
        title: str,
        tags: list = None,
        priority: str = "medium",
        notes: str = "",
    ) -> dict:
        """Add a new task and return it."""
        data = self._read()
        task = {
            "id": data["next_id"],
            "title": title,
            "status": "pending",
            "priority": priority,
            "tags": tags or [],
            "notes": notes,
            "created_at": time.strftime("%Y-%m-%d %H:%M"),
        }
        data["tasks"].append(task)
        data["next_id"] += 1
        self._write(data)
        return task

    def list_tasks(
        self,
        status: str = "pending",
        tag: Optional[str] = None,
        priority: Optional[str] = None,
        sort_by: str = "created",
    ) -> list:
        """Return filtered and sorted list of tasks."""
        data = self._read()
        tasks = data["tasks"]

        if status != "all":
            tasks = [t for t in tasks if t["status"] == status]
        if tag:
            tasks = [t for t in tasks if tag in t.get("tags", [])]
        if priority:
            tasks = [t for t in tasks if t["priority"] == priority]

        if sort_by == "priority":
            tasks = sorted(tasks, key=lambda t: PRIORITY_ORDER.get(t["priority"], 99))
        elif sort_by == "title":
            tasks = sorted(tasks, key=lambda t: t["title"].lower())
        # default: "created" — preserve insertion order

        return tasks

    def get_task(self, task_id: int) -> Optional[dict]:
        """Return a single task by ID, or None."""
        data = self._read()
        return next((t for t in data["tasks"] if t["id"] == task_id), None)

    def mark_done(self, task_id: int) -> Optional[dict]:
        """Mark a task as done. Returns the updated task or None."""
        data = self._read()
        for task in data["tasks"]:
            if task["id"] == task_id:
                task["status"] = "done"
                task["done_at"] = time.strftime("%Y-%m-%d %H:%M")
                self._write(data)
                return task
        return None

    def remove_task(self, task_id: int) -> bool:
        """Remove a task by ID. Returns True if removed."""
        data = self._read()
        original_len = len(data["tasks"])
        data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
        if len(data["tasks"]) < original_len:
            self._write(data)
            return True
        return False

    def update_task(self, task_id: int, **kwargs) -> Optional[dict]:
        """Update allowed fields on a task."""
        allowed = {"title", "notes", "priority", "tags", "status"}
        data = self._read()
        for task in data["tasks"]:
            if task["id"] == task_id:
                for key, value in kwargs.items():
                    if key in allowed:
                        task[key] = value
                self._write(data)
                return task
        return None
