"""Unit tests for the PawPal+ logic layer."""

from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task


def test_task_mark_completed():
    """Calling mark_completed() flips is_completed from False to True."""
    task = Task(title="Morning walk", duration_minutes=30, priority="high")

    assert task.is_completed is False

    task.mark_completed()

    assert task.is_completed is True


def test_pet_add_task_stores_task():
    """Adding a task to a Pet stores it and increases the task count."""
    pet = Pet(name="Mochi", species="cat")
    assert len(pet.tasks) == 0

    task = Task(title="Feeding", duration_minutes=10, priority="high")
    pet.add_task(task)

    assert len(pet.tasks) == 1
    assert pet.tasks[0] is task


def test_sort_tasks_orders_high_to_low_priority():
    """Tasks are sorted from high to low priority."""
    owner = Owner(name="Jordan", available_time=120)
    pet = Pet(name="Mochi", species="cat")
    owner.add_pet(pet)

    pet.add_task(Task(title="Low task", duration_minutes=10, priority="low"))
    pet.add_task(Task(title="High task", duration_minutes=10, priority="high"))
    pet.add_task(Task(title="Medium task", duration_minutes=10, priority="medium"))

    scheduler = Scheduler(owner)
    ordered = scheduler.sort_tasks()

    assert [t.priority for t in ordered] == ["high", "medium", "low"]


def test_build_schedule_skips_tasks_over_time_budget():
    """Tasks that exceed the remaining available time are skipped and recorded."""
    owner = Owner(name="Jordan", available_time=30)
    pet = Pet(name="Mochi", species="cat")
    owner.add_pet(pet)

    fits = Task(title="Quick feed", duration_minutes=20, priority="high")
    too_long = Task(title="Long grooming", duration_minutes=40, priority="medium")
    pet.add_task(fits)
    pet.add_task(too_long)

    scheduler = Scheduler(owner)
    scheduler.build_schedule()

    scheduled_titles = [item.task.title for item in scheduler.daily_schedule]
    skipped_titles = [task.title for task, _reason in scheduler.skipped]

    assert scheduled_titles == ["Quick feed"]
    assert skipped_titles == ["Long grooming"]


def test_build_schedule_filters_out_completed_tasks():
    """Tasks already marked completed are filtered out and never scheduled."""
    owner = Owner(name="Jordan", available_time=120)
    pet = Pet(name="Mochi", species="cat")
    owner.add_pet(pet)

    active = Task(title="Walk", duration_minutes=20, priority="high")
    done = Task(title="Already fed", duration_minutes=10, priority="high")
    done.mark_completed()
    pet.add_task(active)
    pet.add_task(done)

    scheduler = Scheduler(owner)
    scheduler.build_schedule()

    scheduled_titles = [item.task.title for item in scheduler.daily_schedule]
    skipped_titles = [task.title for task, _reason in scheduler.skipped]

    assert scheduled_titles == ["Walk"]
    # A completed task is filtered before scheduling, so it is not even "skipped".
    assert "Already fed" not in scheduled_titles
    assert "Already fed" not in skipped_titles


# --- Step 1: Recurring tasks (is_due) -------------------------------------


def test_is_due_never_completed_is_always_due():
    """A task that has never been completed is due regardless of frequency."""
    weekly = Task(title="Grooming", duration_minutes=20, priority="low",
                  frequency="weekly")
    assert weekly.is_due(date(2026, 6, 29)) is True


def test_is_due_weekly_respects_interval():
    """A weekly task is not due until 7 days after it was last completed."""
    weekly = Task(title="Grooming", duration_minutes=20, priority="low",
                  frequency="weekly")
    weekly.mark_completed(day=date(2026, 6, 29))

    assert weekly.is_due(date(2026, 7, 2)) is False   # 3 days later
    assert weekly.is_due(date(2026, 7, 6)) is True     # 7 days later


def test_is_due_daily_not_due_again_same_day():
    """A daily task completed today is not due again until the next day."""
    daily = Task(title="Feeding", duration_minutes=10, priority="high")
    daily.mark_completed(day=date(2026, 6, 29))

    assert daily.is_due(date(2026, 6, 29)) is False
    assert daily.is_due(date(2026, 6, 30)) is True


# --- Step 2: Context filtering --------------------------------------------


def test_filter_tasks_by_active_pets():
    """Only tasks belonging to the active pets are kept."""
    owner = Owner(name="Jordan", available_time=120)
    mochi = Pet(name="Mochi", species="cat")
    biscuit = Pet(name="Biscuit", species="dog")
    owner.add_pet(mochi)
    owner.add_pet(biscuit)

    mochi.add_task(Task(title="Litter", duration_minutes=5, priority="high"))
    biscuit.add_task(Task(title="Walk", duration_minutes=30, priority="high"))

    scheduler = Scheduler(owner)
    kept = scheduler.filter_tasks(active_pets={"Mochi"})

    assert [t.title for t in kept] == ["Litter"]


def test_filter_tasks_excludes_not_due_recurring():
    """Recurring tasks not due on the given day are filtered out."""
    owner = Owner(name="Jordan", available_time=120)
    pet = Pet(name="Mochi", species="cat")
    owner.add_pet(pet)

    daily = Task(title="Feeding", duration_minutes=10, priority="high")
    weekly = Task(title="Grooming", duration_minutes=20, priority="low",
                  frequency="weekly")
    weekly.mark_completed(day=date(2026, 6, 29))  # just done, not due for a week
    pet.add_task(daily)
    pet.add_task(weekly)

    scheduler = Scheduler(owner)
    kept = scheduler.filter_tasks(day=date(2026, 6, 30))

    assert [t.title for t in kept] == ["Feeding"]


def test_mark_completed_sets_next_due_via_frequency():
    """mark_completed(day) computes next_due using the frequency interval."""
    daily = Task(title="Feeding", duration_minutes=10, priority="high")
    weekly = Task(title="Grooming", duration_minutes=20, priority="low",
                  frequency="weekly")

    daily.mark_completed(day=date(2026, 6, 29))
    weekly.mark_completed(day=date(2026, 6, 29))

    assert daily.next_due == date(2026, 6, 30)   # +1 day
    assert weekly.next_due == date(2026, 7, 6)   # +7 days


def test_completed_recurring_task_reschedules_when_date_advances():
    """A completed daily task is skipped today but reappears the next day."""
    owner = Owner(name="Jordan", available_time=120)
    pet = Pet(name="Mochi", species="cat")
    owner.add_pet(pet)

    feeding = Task(title="Feeding", duration_minutes=10, priority="high")
    pet.add_task(feeding)

    today = date(2026, 6, 29)
    feeding.mark_completed(day=today)  # done for today

    # Same day: completed instance must NOT be scheduled again.
    scheduler = Scheduler(owner)
    scheduler.build_schedule(day=today)
    assert [i.task.title for i in scheduler.daily_schedule] == []

    # Next day: the occurrence is due again and gets scheduled.
    scheduler.build_schedule(day=date(2026, 6, 30))
    assert [i.task.title for i in scheduler.daily_schedule] == ["Feeding"]
    assert feeding.is_completed is False  # reopened by refresh()


# --- Step 4: Overcommitment detection -------------------------------------


def test_build_schedule_warns_when_high_priority_exceeds_budget():
    """A warning is recorded when high-priority work alone exceeds available time."""
    owner = Owner(name="Jordan", available_time=60)
    pet = Pet(name="Mochi", species="dog")
    owner.add_pet(pet)

    pet.add_task(Task("Walk", duration_minutes=30, priority="high"))
    pet.add_task(Task("Vet", duration_minutes=50, priority="high"))  # 80 > 60

    scheduler = Scheduler(owner)
    scheduler.build_schedule()

    assert len(scheduler.warnings) == 1
    assert "over budget by 20 min" in scheduler.warnings[0]
    assert "over budget by 20 min" in scheduler.explain_plan()


def test_no_warning_when_high_priority_within_budget():
    """No warning when high-priority work fits inside the available time."""
    owner = Owner(name="Jordan", available_time=60)
    pet = Pet(name="Mochi", species="dog")
    owner.add_pet(pet)

    pet.add_task(Task("Walk", duration_minutes=30, priority="high"))
    pet.add_task(Task("Long grooming", duration_minutes=45, priority="low"))

    scheduler = Scheduler(owner)
    scheduler.build_schedule()

    assert scheduler.warnings == []
