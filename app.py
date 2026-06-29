from datetime import date

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
PawPal+ helps a busy pet owner plan care tasks for their pet based on the time
they have available, task priority, and preferences.
"""
)

# ---------------------------------------------------------------------------
# Persistent app state ("memory")
# Streamlit re-runs this script top-to-bottom on every interaction, which would
# reset ordinary variables. st.session_state is a dict that SURVIVES reruns, so
# we create our objects there once and reuse them on every later click.
# ---------------------------------------------------------------------------

# The `if "key" not in st.session_state` guard is True only on the first run,
# so the default Owner is built exactly once and never wiped out by later clicks.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", available_time=60)

if "scheduler" not in st.session_state:
    # Hand the Scheduler the SAME Owner instance (a reference, not a copy). The
    # Scheduler reads tasks live via owner.get_all_tasks(), so it automatically
    # sees any pets/tasks added later — no need to ever rebuild or re-link it.
    st.session_state.scheduler = Scheduler(st.session_state.owner)

# Local handles to the persisted objects. These are the SAME objects in memory
# as st.session_state.owner / .scheduler, so mutating them (owner.add_pet(...),
# owner.name = ...) writes straight through to session_state and persists.
# NOTE: only *mutation* persists. Reassigning (owner = Owner(...)) would just
# repoint this local name and leave the stored object untouched — to replace it
# you must assign back into the dict (st.session_state.owner = ...).
owner = st.session_state.owner
scheduler = st.session_state.scheduler

# ---------------------------------------------------------------------------
# Owner inputs (kept in sync with the persisted Owner)
# ---------------------------------------------------------------------------
st.subheader("Owner")

col_owner, col_time = st.columns(2)
with col_owner:
    # Writing onto owner.name mutates the persisted object directly, so the new
    # name survives the next rerun without touching st.session_state explicitly.
    owner.name = st.text_input("Owner name", value=owner.name)
with col_time:
    owner.available_time = int(
        st.number_input(
            "Available time today (minutes)",
            min_value=1,
            max_value=1440,
            value=owner.available_time,
        )
    )

st.divider()

# ---------------------------------------------------------------------------
# Pets (added incrementally; persisted on the Owner)
# ---------------------------------------------------------------------------
st.subheader("Pets")

col_pet, col_species = st.columns(2)
with col_pet:
    new_pet_name = st.text_input("Pet name", value="Mochi")
with col_species:
    new_species = st.selectbox("Species", ["dog", "cat", "other"])

new_prefs_raw = st.text_input(
    "Pet preferences (comma-separated)", value="quiet play, short walks"
)

if st.button("Add pet"):
    if new_pet_name.strip():
        prefs = [p.strip() for p in new_prefs_raw.split(",") if p.strip()]
        owner.add_pet(Pet(name=new_pet_name.strip(), species=new_species, preferences=prefs))
    else:
        st.warning("Give the pet a name first.")

if owner.pets:
    st.write("Current pets:")
    for pet in owner.pets:
        st.write(f"- {pet.describe()} — {len(pet.tasks)} task(s)")
else:
    st.info("No pets yet. Add one above.")

st.divider()

# ---------------------------------------------------------------------------
# Tasks (added to a chosen pet; persisted on that Pet)
# ---------------------------------------------------------------------------
st.subheader("Tasks")
st.caption("Add care tasks to a pet. These feed directly into the scheduler.")

if owner.pets:
    pet_names = [pet.name for pet in owner.pets]
    target_name = st.selectbox("Add task to which pet?", pet_names)

    col1, col2 = st.columns(2)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
        duration = st.number_input(
            "Duration (minutes)", min_value=1, max_value=240, value=20
        )
    with col2:
        priority = st.selectbox("Priority", ["high", "medium", "low"], index=0)
        frequency = st.selectbox("Frequency", ["daily", "weekly", "monthly"], index=0)

    if st.button("Add task", use_container_width=True):
        target_pet = next(pet for pet in owner.pets if pet.name == target_name)
        target_pet.add_task(
            Task(
                title=task_title,
                duration_minutes=int(duration),
                priority=priority,
                frequency=frequency,
            )
        )

    # get_all_tasks() returns the real Task objects (references), so calling
    # task.mark_completed() below mutates the object stored in session_state.
    all_tasks = owner.get_all_tasks()
    if all_tasks:
        st.write("Current task pool:")
        for i, task in enumerate(all_tasks):
            col_info, col_action = st.columns([4, 1])
            with col_info:
                status = "✅" if task.is_completed else "⬜"
                st.write(
                    f"{status} **{task.title}** ({task.pet_name}) — "
                    f"{task.duration_minutes} min · {task.priority} · {task.frequency}"
                )
            with col_action:
                if task.is_completed:
                    st.caption("Done")
                # A unique key per task is required so Streamlit can tell the
                # buttons apart across reruns.
                elif st.button("Mark complete", key=f"complete_{i}"):
                    # Record today's date so recurrence (next_due) is computed;
                    # the task reopens automatically once that date arrives.
                    task.mark_completed(day=date.today())
                    st.rerun()              # rerun so the UI reflects it instantly
    else:
        st.info("No tasks yet. Add one above.")
else:
    st.info("Add a pet before adding tasks.")

st.divider()

# ---------------------------------------------------------------------------
# Build schedule
# ---------------------------------------------------------------------------
st.subheader("Build Schedule")

col_build, col_reset = st.columns(2)
with col_build:
    generate = st.button("Generate schedule", type="primary", use_container_width=True)
with col_reset:
    if st.button("Reset all", use_container_width=True):
        # To REPLACE (not mutate) the stored objects we must clear them from
        # session_state; deleting the keys makes the guards above rebuild fresh
        # defaults on the rerun triggered by st.rerun().
        del st.session_state.owner
        del st.session_state.scheduler
        st.rerun()

if generate:
    if not owner.get_all_tasks():
        st.warning("Add at least one task before generating a schedule.")
    else:
        # Build for today's date so recurring tasks are filtered by is_due(day)
        # and any completed-but-now-due tasks are reopened.
        scheduler.build_schedule(day=date.today())

        st.markdown("### Daily plan")

        # Visual timeline / table of scheduled tasks.
        if scheduler.daily_schedule:
            rows = [
                {
                    "Time": Scheduler._format_time(item.start_minute),
                    "Task": item.task.title,
                    "Pet": item.task.pet_name,
                    "Duration (min)": item.task.duration_minutes,
                    "Priority": item.task.priority,
                    "Frequency": item.task.frequency,
                }
                for item in scheduler.daily_schedule
            ]
            st.table(rows)

            used = sum(item.task.duration_minutes for item in scheduler.daily_schedule)
            st.success(
                f"Scheduled {len(scheduler.daily_schedule)} task(s) using "
                f"{used} of {owner.available_time} available minutes."
            )
        else:
            st.warning("No tasks could be scheduled within the available time.")

        # Skipped tasks.
        if scheduler.skipped:
            st.markdown("#### Skipped tasks")
            for task, reason in scheduler.skipped:
                st.write(f"- **{task.title}** ({task.pet_name}): {reason}")

        # Natural-language explanation of the plan.
        st.markdown("#### Why this plan?")
        st.code(scheduler.explain_plan(), language="text")
