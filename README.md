# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

```bash
🐾 --- PawPal+ Terminal Demo --- 🐾

1) Task pool — insertion order (out of order)
---------------------------------------------
  ⬜ Quick treat      Mochi      5 min  [low]
  ⬜ Morning walk     Mochi     30 min  [high]
  ⬜ Train commands   Mochi     20 min  [high]
  ⬜ Brush fur        Luna      15 min  [medium]
  ⬜ Feeding          Luna      10 min  [high]

2) sort_tasks() — by priority, then shortest duration
-----------------------------------------------------
  ⬜ Feeding          Luna      10 min  [high]
  ⬜ Train commands   Mochi     20 min  [high]
  ⬜ Morning walk     Mochi     30 min  [high]
  ⬜ Brush fur        Luna      15 min  [medium]
  ⬜ Quick treat      Mochi      5 min  [low]

3) filter_tasks(active_pets={'Mochi'}) — only Mochi's tasks
-----------------------------------------------------------
  ⬜ Quick treat      Mochi      5 min  [low]
  ⬜ Morning walk     Mochi     30 min  [high]
  ⬜ Train commands   Mochi     20 min  [high]

4a) filter_tasks(is_completed=False) — active only (default)
------------------------------------------------------------
  ⬜ Quick treat      Mochi      5 min  [low]
  ⬜ Morning walk     Mochi     30 min  [high]
  ⬜ Train commands   Mochi     20 min  [high]
  ⬜ Feeding          Luna      10 min  [high]

4b) filter_tasks(is_completed=True) — completed only
----------------------------------------------------
  ✅ Brush fur        Luna      15 min  [medium]

5) Final daily plan
------------------
Daily plan for Cinthia (60 min available):
  08:00 — Feeding (10 min) [priority: high] for Luna
  08:10 — Train commands (20 min) [priority: high] for Mochi
  08:30 — Morning walk (30 min) [priority: high] for Mochi
Skipped:
  - Quick treat (Mochi): not enough time left (0 min remaining, needs 5 min)

```

## 📐 Smarter Scheduling

PawPal+ goes beyond a flat to-do list. The `Scheduler` and `Task` classes work
together to decide **what** to do today, in **what order**, and **how much**
fits — then explain the result. The four algorithmic features below power that.

| Feature | Method(s) | What it does |
| --- | --- | --- |
| Sorting behavior | `Scheduler.sort_tasks()` | Orders tasks by priority rank, then shortest duration |
| Filtering behavior | `Scheduler.filter_tasks()` | Selects tasks by active pet, recurrence, and completion status |
| Recurring task logic | `Task.is_due()`, `Task.mark_completed()` | Schedules the next occurrence using frequency intervals |
| Conflict & overcommitment detection | `Scheduler.build_schedule()` | Flags (without crashing) when high-priority work exceeds the time budget |

### 1. Sorting behavior — `Scheduler.sort_tasks()`

Tasks are ordered so the most important care happens first. The sort key ranks
by **priority** (`high` → `medium` → `low`, via the `PRIORITY_RANK` map) and
breaks ties by **shortest duration**, so quick high-value tasks are placed
before long ones. Priority is negated in the key so it sorts descending while
duration still sorts ascending in a single pass; an unknown priority falls back
to `0` and sorts last instead of raising an error.

### 2. Filtering behavior — `Scheduler.filter_tasks()`

Returns a fresh list of eligible tasks (never mutating the original pool) using
three independent, optional filters:

* **Active pets** — limit the plan to specific pets by name (`active_pets={"Mochi"}`).
* **Recurrence** — when a `day` is given, keep only tasks that are due that day.
* **Completion status** — `is_completed=False` (default) keeps active tasks,
`True` keeps completed ones, and `None` keeps both.

### 3. Recurring task logic — `Task.is_due()` and `Task.mark_completed()`

Each task has a `frequency` (`daily`, `weekly`, `monthly`) mapped to a day
interval (`1`, `7`, `30`). When `mark_completed(day)` is called, it records the
completion date and uses `datetime.timedelta` to compute the task's `next_due`
date. `is_due(day)` then returns `True` once that date arrives. A completed
recurring task automatically reopens for its next occurrence — so a daily
feeding done today reappears on tomorrow's plan.

### 4. Conflict & overcommitment detection — `Scheduler.build_schedule()`

As it greedily packs tasks into the owner's `available_time`, the scheduler
checks whether the **high-priority workload alone** exceeds the budget. If it
does, it records a friendly warning (e.g. *"High-priority tasks need 80 min but
you have only 60 min — over budget by 20 min"*) in `warnings` and surfaces it in
`explain_plan()`. The plan is still produced — the program flags the conflict
rather than failing.

## 🧪 Testing PawPal+

The logic layer is covered by **15 unit tests** in [`tests/test_pawpal.py`](https://www.google.com/search?q=tests/test_pawpal.py),
written with Python's `unittest` framework. They verify the happy paths
(sorting, building) and the critical edge cases (empty task lists, owners with
no pets, overcommitment, and recurrence intervals). Recurrence tests use fixed
dates for determinism, and each `TestCase` rebuilds fresh objects in `setUp()`
for isolation.

**Run the tests:**

```bash
python -m pytest

```

You can also run the same suite through the `unittest` runner:

```bash
python -m unittest tests.test_pawpal

```

**What the suite covers:**

* **Sorting correctness** — tasks are ordered by priority rank (high → medium →
low) and then by shortest duration, and land in the schedule in that order.
* **Recurrence logic** — `is_due()` and `mark_completed()` use `datetime.timedelta`
to compute each task's next due date, so a task completed today is skipped today
but correctly reappears once its interval has passed.
* **Conflict / overcommitment detection** — when high-priority work exceeds the
owner's `available_time`, the scheduler flags a warning with the exact overage
and skips over-budget tasks with a clear reason, without crashing.

**Successful test run:**

```
$ python -m pytest
============================= test session starts ==============================
collected 15 items

tests/test_pawpal.py ...............                                      [100%]

============================== 15 passed in 0.01s ==============================

```

### Confidence Level

**Reliability: ⭐⭐⭐⭐⭐ (5/5)**

All **15 tests pass (100% pass rate)**, and the suite goes beyond happy-path
checks to cover the edge cases most likely to break a scheduler: empty task
lists, owners with no pets, recurrence boundaries (using deterministic fixed
dates), and budget overruns. Each test asserts on specific values — exact
orderings, dates, minute overages, and skip reasons — so a subtle regression
fails loudly rather than slipping through. Combined with per-test isolation via
`setUp()`, this gives high confidence that the core scheduling logic behaves
correctly and stays correct as the code evolves.

## 📸 Demo Walkthrough

A guided tour of the PawPal+ Streamlit interface. Launch it with
`streamlit run app.py` and follow along — the page is organized top-to-bottom
into four sections.

### 1. Owner profile

The **Owner** section configures who the plan is for and the day's time budget:

* **Owner name** — a text field identifying the owner (e.g. `Jordan`).
* **Available time today (minutes)** — the total minutes the owner can spend on
pet care. This is the hard budget the scheduler plans against.

Both fields write straight to the persisted `Owner` object, so edits survive
every interaction.

### 2. Pet registration

The **Pets** section adds one or more pets, each persisted on the owner:

* **Pet name** and **Species** (`dog`, `cat`, or `other`).
* **Preferences** — a comma-separated list (e.g. `quiet play, short walks`)
stored on the pet for context.
* Clicking **Add pet** registers the pet; a running list shows each pet and its
current task count.

### 3. Task management

The **Tasks** section attaches care tasks to a chosen pet:

* **Add task to which pet?** — a dropdown that targets one of the registered pets.
* **Task title** and **Duration (minutes)**.
* **Priority** — `High`, `Medium`, or `Low`.
* **Frequency** — `daily`, `weekly`, or `monthly` (drives recurrence).
* Clicking **Add task** appends it to that pet. The task pool then renders in two
groups:
* **Active tasks**, listed in scheduling order (highest priority first, then
shortest duration), each with a **Mark complete** button.
* **Completed today**, tucked into a collapsible expander.



### 4. Example workflow

A typical end-to-end session:

1. **Configure the profile** — set the owner to `Cinthia` with a **60-minute** budget.
2. **Register pets** — add `Mochi` (dog) and `Luna` (cat).
3. **Add tasks out of order** — for example:
* `Treat` — 5 min, Low (Mochi)
* `Vet` — 40 min, High (Luna)
* `Brush` — 15 min, Medium (Luna)
* `Walk` — 30 min, High (Mochi)


4. **Build the plan** — click **Generate schedule**. PawPal+ sorts, filters, and
packs the tasks into the available time, then displays the result.

### 5. Algorithmic visibility & interface design

The Streamlit UI doesn't just collect inputs — it surfaces the scheduler's
reasoning so the pet owner understands *why* a plan looks the way it does.

* **Overcommitment Visibility:** When `build_schedule()` detects that the high-priority workload exceeds the owner's available time, it records a friendly message in `scheduler.warnings`. After generating the plan, the UI loops over those warnings and renders each one with a highlighted yellow `st.warning()` block:
```python
for warning in scheduler.warnings:
    st.warning(f"⚠️ {warning}")

```


This displays the alert in a banner that is impossible to miss:
> ⚠️ High-priority tasks need 70 min but you have only 60 min — over budget by 10 min. Consider freeing up more time or deferring a high-priority task.


* **Clean Schedule Table:** The final plan renders with `st.table()`, showing one row per scheduled task with time, task, pet, duration, priority, and frequency.
* **Metric Cards:** `st.metric()` cards summarize the plan at a glance: **tasks scheduled**, **time used** (with remaining free minutes), and **tasks skipped**.
* **Plan Explanation:** A natural-language breakdown (`explain_plan()`) lists what was scheduled and why anything was skipped, ensuring the underlying processes are transparent to the user.