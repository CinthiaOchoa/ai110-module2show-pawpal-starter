"""Unit tests for the PawPal+ logic layer."""

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
