"""PawPal+ logic layer.

Implements the four core classes for the PawPal+ pet care planner:

    Task          - a single care activity (duration, priority, frequency, status)
    Pet           - pet details plus the list of tasks that pet needs
    Owner         - manages multiple pets and exposes all their tasks
    Scheduler     - the "brain": pulls tasks from the Owner, then filters,
                    sorts, and allocates them into a daily plan within the
                    owner's available time, with an explanation of the plan.

Relationships: an Owner has many Pets; a Pet has many Tasks; the Scheduler
talks to ONE Owner and retrieves tasks through Owner.get_all_tasks().
"""

from dataclasses import dataclass, field

# Maps priority labels to a numeric rank so tasks can be sorted (higher = more urgent).
PRIORITY_RANK = {"high": 3, "medium": 2, "low": 1}


@dataclass
class Task:
    """A single pet care activity with duration, priority, frequency, and status."""

    title: str
    duration_minutes: int
    priority: str
    pet_name: str = ""          # which pet this task is for (set by Pet.add_task)
    frequency: str = "daily"    # e.g. "daily", "weekly"
    is_completed: bool = False

    def mark_completed(self) -> None:
        """Mark this task as completed."""
        self.is_completed = True


@dataclass
class Pet:
    """A pet's details plus the list of care tasks it needs."""

    name: str
    species: str
    preferences: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)

    def add_preference(self, pref: str) -> None:
        """Add a care preference, ignoring duplicates."""
        if pref not in self.preferences:
            self.preferences.append(pref)

    def add_task(self, task: Task) -> None:
        """Attach a task to this pet, stamping it with the pet's name."""
        # Stamp the task with this pet's name so it stays identifiable once
        # tasks are aggregated across pets by the Owner.
        task.pet_name = self.name
        self.tasks.append(task)

    def describe(self) -> str:
        """Return a short human-readable summary of the pet and its preferences."""
        prefs = ", ".join(self.preferences) if self.preferences else "no special preferences"
        return f"{self.name} the {self.species} ({prefs})"


@dataclass
class Owner:
    """A pet owner who manages multiple pets and their available care time."""

    name: str
    available_time: int  # minutes the owner can dedicate to pet care today
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self.pets.append(pet)

    def get_all_tasks(self) -> list[Task]:
        """Flatten and return every task across all of the owner's pets."""
        all_tasks: list[Task] = []
        for pet in self.pets:
            all_tasks.extend(pet.tasks)
        return all_tasks

    def remaining_time(self, used: int) -> int:
        """Minutes of care time still available after `used` minutes are spent."""
        return max(0, self.available_time - used)


@dataclass
class ScheduledTask:
    """Wraps a Task with the time it was placed in the day's plan."""

    task: Task
    start_minute: int  # minutes from day start; formatted to "08:00" in explain_plan


@dataclass
class Scheduler:
    """Planning engine that builds and explains a daily care plan for one owner."""

    owner: Owner
    daily_schedule: list[ScheduledTask] = field(default_factory=list)
    skipped: list[tuple[Task, str]] = field(default_factory=list)  # (task, reason)
    day_start_minute: int = 8 * 60  # plan starts at 08:00 by default

    def filter_tasks(self) -> list[Task]:
        """Active tasks to consider today: pull from the owner, drop completed ones."""
        return [task for task in self.owner.get_all_tasks() if not task.is_completed]

    def sort_tasks(self) -> list[Task]:
        """Filtered tasks ordered by priority (high first), then shortest duration."""
        return sorted(
            self.filter_tasks(),
            key=lambda t: (-PRIORITY_RANK.get(t.priority, 0), t.duration_minutes),
        )

    def build_schedule(self) -> list[ScheduledTask]:
        """Greedily allocate sorted tasks into the day without exceeding available time.

        Tasks that don't fit in the remaining time are recorded in `skipped`
        with a reason, so explain_plan() can justify the plan.
        """
        self.daily_schedule = []
        self.skipped = []
        used = 0
        current_minute = self.day_start_minute

        for task in self.sort_tasks():
            remaining = self.owner.remaining_time(used)
            if task.duration_minutes <= remaining:
                self.daily_schedule.append(ScheduledTask(task, current_minute))
                used += task.duration_minutes
                current_minute += task.duration_minutes
            else:
                self.skipped.append(
                    (task, f"not enough time left ({remaining} min remaining, "
                           f"needs {task.duration_minutes} min)")
                )
        return self.daily_schedule

    def explain_plan(self) -> str:
        """Human-readable explanation of the scheduled and skipped tasks."""
        if not self.daily_schedule and not self.skipped:
            return "No plan yet. Call build_schedule() first."

        lines = [
            f"Daily plan for {self.owner.name} "
            f"({self.owner.available_time} min available):"
        ]
        for item in self.daily_schedule:
            t = item.task
            lines.append(
                f"  {self._format_time(item.start_minute)} — {t.title} "
                f"({t.duration_minutes} min) [priority: {t.priority}] for {t.pet_name}"
            )
        if self.skipped:
            lines.append("Skipped:")
            for task, reason in self.skipped:
                lines.append(f"  - {task.title} ({task.pet_name}): {reason}")
        return "\n".join(lines)

    @staticmethod
    def _format_time(minute: int) -> str:
        """Convert minutes-from-midnight into a 'HH:MM' clock string."""
        hours, minutes = divmod(minute, 60)
        return f"{hours:02d}:{minutes:02d}"
