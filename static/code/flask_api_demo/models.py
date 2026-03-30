"""
Data models for Flask API Demo.
"""
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class Task:
    """Represents a task in the system."""
    id: int
    title: str
    description: str = ""
    status: str = "pending"
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: Optional[float] = None

    VALID_STATUSES = ("pending", "in_progress", "done", "cancelled")

    def update(self, **kwargs) -> None:
        """Update allowed fields and set updated_at timestamp."""
        allowed = {"title", "description", "status", "tags"}
        for key, value in kwargs.items():
            if key in allowed:
                if key == "status" and value not in self.VALID_STATUSES:
                    raise ValueError(f"Invalid status: {value}")
                setattr(self, key, value)
        self.updated_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class User:
    """Represents an authenticated user."""
    username: str
    password_hash: str
    created_at: float = field(default_factory=time.time)
    is_active: bool = True

    def to_dict(self) -> dict:
        """Return public-safe user representation."""
        return {
            "username": self.username,
            "created_at": self.created_at,
            "is_active": self.is_active,
        }


class TaskRepository:
    """In-memory repository for tasks."""

    def __init__(self):
        self._tasks: List[Task] = []
        self._counter: int = 1

    def create(self, title: str, description: str = "", tags: List[str] = None) -> Task:
        """Create and store a new task."""
        task = Task(
            id=self._counter,
            title=title,
            description=description,
            tags=tags or [],
        )
        self._tasks.append(task)
        self._counter += 1
        return task

    def find_by_id(self, task_id: int) -> Optional[Task]:
        return next((t for t in self._tasks if t.id == task_id), None)

    def find_all(self, status: Optional[str] = None) -> List[Task]:
        if status:
            return [t for t in self._tasks if t.status == status]
        return list(self._tasks)

    def delete(self, task_id: int) -> bool:
        original_len = len(self._tasks)
        self._tasks = [t for t in self._tasks if t.id != task_id]
        return len(self._tasks) < original_len
