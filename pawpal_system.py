"""PawPal+ logic layer.

Class skeletons generated from the UML diagram in diagrams/uml.mmd.
Method bodies are intentionally left empty so these act as clean stubs.
"""

from dataclasses import dataclass, field


@dataclass
class Pet:
    name: str
    species: str
    preferences: list[str] = field(default_factory=list)

    def add_preference(self, pref: str) -> None:
        pass

    def describe(self) -> str:
        pass


@dataclass
class Owner:
    name: str
    available_time: int

    def remaining_time(self, used: int) -> int:
        pass


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: str
    is_completed: bool = False

    def mark_completed(self) -> None:
        pass


@dataclass
class Scheduler:
    owner: Owner
    pets: list[Pet] = field(default_factory=list)
    task_pool: list[Task] = field(default_factory=list)
    daily_schedule: list[Task] = field(default_factory=list)

    def filter_tasks(self) -> list[Task]:
        pass

    def sort_tasks(self) -> list[Task]:
        pass

    def build_schedule(self) -> list[Task]:
        pass

    def explain_plan(self) -> str:
        pass
