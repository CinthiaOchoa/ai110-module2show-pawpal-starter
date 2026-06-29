"""Unit tests for the PawPal+ logic layer (unittest framework).

Principles:
- Determinism: recurrence tests use fixed date(...) values, never the system clock.
- Isolation: setUp() rebuilds a fresh Owner/Pet/Scheduler before every test, since
  the scheduler mutates task state.
- Specific assertions: overcommitment tests check the actual overage and skip reason,
  not just that "something" was flagged.
"""

import unittest
from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task


class TestTask(unittest.TestCase):
    """Behavior of the Task dataclass on its own."""

    def test_mark_completed_sets_flag(self):
        task = Task(title="Walk", duration_minutes=30, priority="high")
        self.assertFalse(task.is_completed)

        task.mark_completed()

        self.assertTrue(task.is_completed)

    def test_mark_completed_computes_next_due_with_timedelta(self):
        daily = Task(title="Feeding", duration_minutes=10, priority="high")
        weekly = Task(title="Grooming", duration_minutes=20, priority="low",
                      frequency="weekly")

        daily.mark_completed(day=date(2026, 6, 29))
        weekly.mark_completed(day=date(2026, 6, 29))

        self.assertEqual(daily.next_due, date(2026, 6, 30))   # +1 day
        self.assertEqual(weekly.next_due, date(2026, 7, 6))   # +7 days


class TestPet(unittest.TestCase):
    """Behavior of Pet task ownership."""

    def setUp(self):
        self.pet = Pet(name="Mochi", species="cat")

    def test_add_task_stores_and_stamps_pet_name(self):
        self.assertEqual(len(self.pet.tasks), 0)

        task = Task(title="Feeding", duration_minutes=10, priority="high")
        self.pet.add_task(task)

        self.assertEqual(len(self.pet.tasks), 1)
        self.assertIs(self.pet.tasks[0], task)
        self.assertEqual(task.pet_name, "Mochi")  # add_task stamps the pet's name


class TestScheduler(unittest.TestCase):
    """Sorting, filtering, building, and overcommitment behavior."""

    def setUp(self):
        # Fresh objects per test so mutations never leak between tests.
        self.owner = Owner(name="Jordan", available_time=60)
        self.pet = Pet(name="Mochi", species="dog")
        self.owner.add_pet(self.pet)
        self.scheduler = Scheduler(self.owner)

    # --- Happy path: sorting & building --------------------------------

    def test_sort_orders_by_priority_then_shortest_duration(self):
        # Added out of order, mixed priorities and durations.
        self.pet.add_task(Task("Treat", duration_minutes=5, priority="low"))
        self.pet.add_task(Task("Walk", duration_minutes=30, priority="high"))
        self.pet.add_task(Task("Brush", duration_minutes=15, priority="medium"))
        self.pet.add_task(Task("Train", duration_minutes=20, priority="high"))

        ordered = self.scheduler.sort_tasks()

        # high tasks first; within high, shorter (20) before longer (30).
        self.assertEqual(
            [t.title for t in ordered],
            ["Train", "Walk", "Brush", "Treat"],
        )

    def test_build_schedule_places_tasks_in_order_with_times(self):
        self.pet.add_task(Task("Walk", duration_minutes=30, priority="high"))
        self.pet.add_task(Task("Feeding", duration_minutes=10, priority="high"))

        self.scheduler.build_schedule()

        # Shorter high task first, then placed back-to-back from 08:00 (480 min).
        titles = [item.task.title for item in self.scheduler.daily_schedule]
        starts = [item.start_minute for item in self.scheduler.daily_schedule]
        self.assertEqual(titles, ["Feeding", "Walk"])
        self.assertEqual(starts, [480, 490])  # 08:00, then +10 min

    # --- Edge case: no tasks -------------------------------------------

    def test_empty_task_list_returns_empty_and_does_not_crash(self):
        # Owner has a pet but no tasks at all.
        self.assertEqual(self.scheduler.filter_tasks(), [])
        self.assertEqual(self.scheduler.sort_tasks(), [])
        self.assertEqual(self.scheduler.build_schedule(), [])
        self.assertEqual(self.scheduler.explain_plan(), "No plan yet. Call build_schedule() first.")

    def test_owner_with_no_pets_has_no_tasks(self):
        empty_owner = Owner(name="Sam", available_time=60)
        scheduler = Scheduler(empty_owner)

        self.assertEqual(empty_owner.get_all_tasks(), [])
        self.assertEqual(scheduler.build_schedule(), [])

    # --- Edge case: overcommitment + skipping --------------------------

    def test_overcommitment_flags_warning_with_exact_overage(self):
        # High-priority work totals 70 min against a 60 min budget.
        self.pet.add_task(Task("Vet", duration_minutes=40, priority="high"))
        self.pet.add_task(Task("Walk", duration_minutes=30, priority="high"))

        self.scheduler.build_schedule()

        self.assertEqual(len(self.scheduler.warnings), 1)
        self.assertIn("over budget by 10 min", self.scheduler.warnings[0])
        # The warning must surface in the explanation, and it must not crash.
        self.assertIn("over budget by 10 min", self.scheduler.explain_plan())

    def test_task_over_budget_is_skipped_with_reason(self):
        self.pet.add_task(Task("Quick feed", duration_minutes=20, priority="high"))
        self.pet.add_task(Task("Long grooming", duration_minutes=50, priority="medium"))

        self.scheduler.build_schedule()

        scheduled = [item.task.title for item in self.scheduler.daily_schedule]
        self.assertEqual(scheduled, ["Quick feed"])

        skipped_titles = [task.title for task, _reason in self.scheduler.skipped]
        self.assertEqual(skipped_titles, ["Long grooming"])
        # Assert the specific reason, not just that something was skipped.
        _, reason = self.scheduler.skipped[0]
        self.assertIn("not enough time left", reason)

    # --- Edge case: filtering by context -------------------------------

    def test_filter_by_active_pets(self):
        luna = Pet(name="Luna", species="cat")
        self.owner.add_pet(luna)
        self.pet.add_task(Task("Walk", duration_minutes=30, priority="high"))
        luna.add_task(Task("Litter", duration_minutes=5, priority="high"))

        kept = self.scheduler.filter_tasks(active_pets={"Mochi"})

        self.assertEqual([t.title for t in kept], ["Walk"])

    def test_filter_by_completion_status(self):
        active = Task("Walk", duration_minutes=30, priority="high")
        done = Task("Brush", duration_minutes=15, priority="low")
        done.mark_completed()
        self.pet.add_task(active)
        self.pet.add_task(done)

        self.assertEqual(
            [t.title for t in self.scheduler.filter_tasks(is_completed=False)],
            ["Walk"],
        )
        self.assertEqual(
            [t.title for t in self.scheduler.filter_tasks(is_completed=True)],
            ["Brush"],
        )


class TestRecurrence(unittest.TestCase):
    """Recurrence interval evaluation with deterministic fixed dates."""

    def setUp(self):
        self.owner = Owner(name="Jordan", available_time=120)
        self.pet = Pet(name="Mochi", species="cat")
        self.owner.add_pet(self.pet)
        self.scheduler = Scheduler(self.owner)
        self.completed = date(2026, 6, 29)

    def test_never_completed_is_always_due(self):
        weekly = Task("Grooming", duration_minutes=20, priority="low",
                      frequency="weekly")
        self.assertTrue(weekly.is_due(self.completed))

    def test_daily_not_due_same_day_but_due_next_day(self):
        daily = Task("Feeding", duration_minutes=10, priority="high")
        daily.mark_completed(day=self.completed)

        self.assertFalse(daily.is_due(self.completed))                # same day
        self.assertTrue(daily.is_due(self.completed + _days(1)))      # next day

    def test_weekly_respects_seven_day_interval(self):
        weekly = Task("Grooming", duration_minutes=20, priority="low",
                      frequency="weekly")
        weekly.mark_completed(day=self.completed)

        self.assertFalse(weekly.is_due(self.completed + _days(3)))    # too soon
        self.assertTrue(weekly.is_due(self.completed + _days(7)))     # interval met

    def test_completed_recurring_task_reschedules_when_date_advances(self):
        feeding = Task("Feeding", duration_minutes=10, priority="high")
        self.pet.add_task(feeding)
        feeding.mark_completed(day=self.completed)

        # Same day: already done, not scheduled.
        self.scheduler.build_schedule(day=self.completed)
        self.assertEqual(self.scheduler.daily_schedule, [])

        # Next day: due again, reopened and scheduled.
        self.scheduler.build_schedule(day=self.completed + _days(1))
        scheduled = [item.task.title for item in self.scheduler.daily_schedule]
        self.assertEqual(scheduled, ["Feeding"])
        self.assertFalse(feeding.is_completed)  # refresh() reopened it


def _days(n):
    """Small helper to build fixed-date offsets readably."""
    from datetime import timedelta

    return timedelta(days=n)


if __name__ == "__main__":
    unittest.main()
