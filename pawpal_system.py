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
from datetime import date, timedelta

# Maps priority labels to a numeric rank so tasks can be sorted (higher = more urgent).
PRIORITY_RANK = {"high": 3, "medium": 2, "low": 1}

# Minimum days between occurrences of a recurring task, keyed by frequency label.
FREQUENCY_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}


@dataclass
class Task:
    """A single pet care activity with duration, priority, frequency, and status."""

    title: str
    duration_minutes: int
    priority: str
    pet_name: str = ""              # which pet this task is for (set by Pet.add_task)
    frequency: str = "daily"        # "daily", "weekly", or "monthly"
    is_completed: bool = False
    last_completed: date | None = None  # last day this task was done
    next_due: date | None = None        # day the next occurrence becomes due

    def mark_completed(self, day: date | None = None) -> None:
        """Mark this task complete and, given a day, schedule its next occurrence.

        Uses the frequency interval (daily=1, weekly=7, monthly=30) and
        datetime.timedelta to compute when the task is next due.
        """
        self.is_completed = True
        if day is not None:
            self.last_completed = day
            interval = FREQUENCY_DAYS.get(self.frequency, 1)
            self.next_due = day + timedelta(days=interval)

    def is_due(self, day: date) -> bool:
        """Whether this task should appear on `day` (due once next_due is reached).

        A task never completed (next_due is None) is always due.
        """
        if self.next_due is None:
            return True
        return day >= self.next_due

    def refresh(self, day: date) -> None:
        """Reopen a completed recurring task once its next due date has arrived.

        This is what stops a completed instance from permanently blocking the
        future occurrence: when the calendar advances to next_due, the task
        becomes active (incomplete) again so it can be re-scheduled.
        """
        if self.is_completed and self.next_due is not None and day >= self.next_due:
            self.is_completed = False


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
    warnings: list[str] = field(default_factory=list)  # overcommitment / conflict notes
    day_start_minute: int = 8 * 60  # plan starts at 08:00 by default

    def filter_tasks(
        self,
        day: date | None = None,
        active_pets: set[str] | None = None,
        is_completed: bool | None = False,
    ) -> list[Task]:
        """Tasks matching the given context filters (returns a fresh list).

        is_completed: False (default) keeps only active tasks, True keeps only
            completed tasks, None keeps both.
        active_pets: when given, limits results to tasks for those pet names.
        day: when given, limits to recurring tasks due that day.
        """
        eligible: list[Task] = []
        for task in self.owner.get_all_tasks():
            if is_completed is not None and task.is_completed != is_completed:
                continue
            if active_pets is not None and task.pet_name not in active_pets:
                continue
            if day is not None and not task.is_due(day):
                continue
            eligible.append(task)
        return eligible

    def sort_tasks(
        self,
        day: date | None = None,
        active_pets: set[str] | None = None,
    ) -> list[Task]:
        """Filtered tasks ordered by priority (high first), then shortest duration."""
        # Key negates priority so higher ranks sort first while duration still
        # sorts ascending (a single reverse=True can't do both directions). An
        # unknown priority falls back to 0, so it sorts last instead of crashing.
        return sorted(
            self.filter_tasks(day, active_pets),
            key=lambda t: (-PRIORITY_RANK.get(t.priority, 0), t.duration_minutes),
        )

    def build_schedule(
        self,
        day: date | None = None,
        active_pets: set[str] | None = None,
    ) -> list[ScheduledTask]:
        """Greedily allocate sorted tasks into the day without exceeding available time.

        Tasks that don't fit in the remaining time are recorded in `skipped`
        with a reason, so explain_plan() can justify the plan. If the critical
        (high-priority) workload alone exceeds the available time, a friendly
        warning is recorded in `warnings` instead of failing.
        """
        self.daily_schedule = []
        self.skipped = []
        self.warnings = []
        used = 0
        current_minute = self.day_start_minute

        # Reopen any recurring task whose next due date has arrived, so a past
        # completion does not block today's occurrence.
        if day is not None:
            for task in self.owner.get_all_tasks():
                task.refresh(day)

        eligible = self.sort_tasks(day, active_pets)

        # Overcommitment detection: can all the high-priority work even fit?
        self._check_overcommitment(eligible)

        for task in eligible:
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

    def _check_overcommitment(self, eligible: list[Task]) -> None:
        """Warn (don't fail) when high-priority work alone exceeds available time."""
        high_minutes = sum(
            t.duration_minutes for t in eligible if t.priority == "high"
        )
        if high_minutes > self.owner.available_time:
            over = high_minutes - self.owner.available_time
            self.warnings.append(
                f"High-priority tasks need {high_minutes} min but you have only "
                f"{self.owner.available_time} min — over budget by {over} min. "
                f"Consider freeing up more time or deferring a high-priority task."
            )

    def explain_plan(self) -> str:
        """Human-readable explanation of the scheduled and skipped tasks."""
        if not self.daily_schedule and not self.skipped and not self.warnings:
            return "No plan yet. Call build_schedule() first."

        lines = []
        for warning in self.warnings:
            lines.append(f"⚠️  Warning: {warning}")
        if self.warnings:
            lines.append("")

        lines.append(
            f"Daily plan for {self.owner.name} "
            f"({self.owner.available_time} min available):"
        )
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
