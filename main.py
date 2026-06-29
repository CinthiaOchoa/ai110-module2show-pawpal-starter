"""PawPal+ terminal demo.

Adds tasks out of order, then demonstrates the Scheduler's sorting and
filtering logic before building the final daily schedule.
"""

from pawpal_system import Owner, Pet, Scheduler, Task


def show(label, tasks):
    """Print a labeled list of tasks in their current order."""
    print(f"\n{label}")
    print("-" * len(label))
    if not tasks:
        print("  (none)")
    for t in tasks:
        done = "✅" if t.is_completed else "⬜"
        print(
            f"  {done} {t.title:<16} {t.pet_name:<8} "
            f"{t.duration_minutes:>3} min  [{t.priority}]"
        )


def main():
    print("🐾 --- PawPal+ Terminal Demo --- 🐾")

    # 1. Owner + pets.
    owner = Owner(name="Cinthia", available_time=60)
    mochi = Pet(name="Mochi", species="dog", preferences=["long walks"])
    luna = Pet(name="Luna", species="cat", preferences=["quiet spaces"])
    owner.add_pet(mochi)
    owner.add_pet(luna)

    # 2. Add tasks OUT OF ORDER (mixed priorities and durations) so the sort has
    #    real work to do. add_task() stamps each task with its pet's name.
    mochi.add_task(Task("Quick treat", duration_minutes=5, priority="low"))
    mochi.add_task(Task("Morning walk", duration_minutes=30, priority="high"))
    luna.add_task(Task("Brush fur", duration_minutes=15, priority="medium"))
    mochi.add_task(Task("Train commands", duration_minutes=20, priority="high"))
    luna.add_task(Task("Feeding", duration_minutes=10, priority="high"))

    scheduler = Scheduler(owner)

    # --- Show the pool in INSERTION order (what we typed in) ---
    show("1) Task pool — insertion order (out of order)", owner.get_all_tasks())

    # --- SORTING: high priority first, then shortest duration ---
    show("2) sort_tasks() — by priority, then shortest duration", scheduler.sort_tasks())

    # --- FILTERING by pet_name (active_pets) ---
    show("3) filter_tasks(active_pets={'Mochi'}) — only Mochi's tasks",
         scheduler.filter_tasks(active_pets={"Mochi"}))

    # --- FILTERING by completion status ---
    # Mark one task complete, then show the two completion views.
    luna.tasks[0].mark_completed()  # "Brush fur"
    show("4a) filter_tasks(is_completed=False) — active only (default)",
         scheduler.filter_tasks())
    show("4b) filter_tasks(is_completed=True) — completed only",
         scheduler.filter_tasks(is_completed=True))

    # --- Build and explain the final plan ---
    scheduler.build_schedule()
    print("\n5) Final daily plan")
    print("-" * 18)
    print(scheduler.explain_plan())


if __name__ == "__main__":
    main()
