# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

My initial design breaks down the PawPal+ application into four core object-oriented classes using Python Dataclasses to keep data structures lightweight and readable. The components and their specific responsibilities are:

* **`Pet`**: A dataclass responsible for modeling individual animal data (`name`, `species`, and a dynamic list of `preferences`). It includes stubs for appending preferences and returning a formatted summary of the pet's profile.
* **`Owner`**: Represents the user running the system, tracking their `name` and their total daily allocation of `available_time`. It manages time bookkeeping via the `remaining_time()` method stub.
* **`Task`**: A simple data object capturing critical scheduling constraints: `title`, how long it takes (`duration_minutes`), and its importance (`priority`). It also tracks execution state via `is_completed`.
* **`Scheduler`**: The coordinator or orchestrator of the logic layer. It holds references to the `Owner`, the associated `Pets`, and the input `task_pool`. Its primary responsibility is broken down into structured steps: filtering tasks based on relevance, sorting them systematically by priority weights, executing the time-constraint allocation logic in `build_schedule()`, and explaining the final itinerary output in natural language via `explain_plan()`.

**b. Design changes**

Yes, my design evolved after a structural review with the AI assistant to prevent logical bottlenecks before implementing the scheduling engine:

1. **Task-to-Pet Context (`pet_name`)**: Added a `pet_name` string attribute to the `Task` class. Originally, tasks were ambiguous; linking them by a pet's name prevents ambiguity when scheduling for multiple animals without creating tight circular coupling.
2. **Time Allocation Tracker (`ScheduledTask`)**: Instead of storing the final itinerary as a raw list of tasks, I introduced a `ScheduledTask` wrapper class that pairs a `Task` with a specific `start_minute`. This directly addresses the requirement to explain *when* a task happens.
3. **Decision Transparency (`skipped` tracking)**: Added a `skipped` tracking list (`list[tuple[Task, str]]`) inside the `Scheduler`. This ensures that when `build_schedule()` drops a task due to time constraints, the reason is preserved so `explain_plan()` can justify why it was omitted.
4. **Priority Weights (`PRIORITY_RANK`)**: Established a constant mapping for priorities (`high`: 3, `medium`: 2, `low`: 1) to ensure robust mathematical sorting, avoiding buggy alphabetical string comparisons.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler balances three constraints, applied in this order:

- **Recurrence (`frequency` via `is_due()`)** decides *what is even eligible today*. A task only enters the day's pool if it is due — a daily task is due every day, while weekly/monthly tasks are filtered out until their `next_due` date arrives. This is the first gate because there is no point ranking or fitting a task that should not happen today.
- **Priority (`priority` rank)** decides *what order* eligible tasks are considered in. `sort_tasks()` ranks high → medium → low (breaking ties by shortest duration), so the most important care happens first and is most likely to fit.
- **Time (`available_time` budget)** decides *how much* actually gets scheduled. `build_schedule()` greedily fills tasks back-to-back while tracking minutes used, and stops adding a task once it would exceed the owner's available time.

I decided **time was the hardest constraint** because it is the real-world bottleneck for a busy owner — there are always more care tasks than minutes in the day. Priority matters most *within* that budget, since it determines which tasks "win" the limited time. Recurrence sits on top as an eligibility filter so the plan reflects only today's actual obligations. Preferences are stored on the `Pet` for context/display but are intentionally not a scheduling constraint yet (noted as future work).

**b. Tradeoffs**

- **Greedy time-budget accounting over rigid hourly slots.** Our scheduler tracks a running total of minutes used against the owner's `available_time` and places each task back-to-back, rather than reserving fixed clock slots (e.g. "9:00–9:30"). This favors *fitting the most high-priority work into the available time* over committing to exact appointment times.
- **Why it's reasonable here.** A busy pet owner cares far more about *what* gets done within their limited time than about a task happening at a precise hour — feeding "sometime in the morning block" is fine. Rigid slots would create artificial conflicts and waste capacity by leaving unfillable gaps, whereas back-to-back packing uses every available minute.
- **The accepted cost.** Tasks have no guaranteed wall-clock time and we don't model fixed-time commitments (like a 2:00 PM vet visit), so true time-of-day overlaps can't occur or be detected. We consciously accepted this and instead flag the higher-value risk — *overcommitment*, when high-priority work exceeds the budget — which matters more for a daily planner than slot-level collisions.

---

## 3. AI Collaboration

**a. How you used AI**

I used the AI coding assistant across the entire lifecycle — design brainstorming, implementation, testing, and documentation — but two uses stood out as especially effective:

- **Multi-file synchronized edits.** The assistant was most valuable when a single feature touched several files at once. For example, automating recurring tasks required adding `next_due`/`refresh()` logic to `pawpal_system.py`, then wiring `mark_completed(day=date.today())` and `build_schedule(day=...)` into `app.py` — all in one coordinated pass. Connecting the logic layer to the Streamlit UI this way kept the two files consistent and avoided the drift that happens when you edit them separately.
- **Translating requirements into concrete test plans.** Vague goals like "test the edge cases" became a structured plan — happy-path sorting, empty/no-pet inputs, overcommitment with an exact overage, and recurrence boundaries using fixed dates. Turning fuzzy intent into specific, named test functions with deterministic assertions was a real accelerator.

The most helpful prompts were **specific and context-rich**: naming the exact method, the file, and the expected behavior produced far better results than open-ended requests. Asking the assistant to *explain its reasoning before writing code* (e.g. the conceptual algorithm plan before Phase 5) also caught design issues early.

One workflow choice that paid off was **keeping isolated chat sessions for each phase** — Core Implementation, Testing Suite Generation, and Streamlit UI Integration each had their own thread. This kept context clean and focused, avoided polluting prompts with unrelated history, and — most importantly — prevented stale or competing code versions from bleeding between concerns (e.g. an early `task_pool` design contaminating the final `Owner.get_all_tasks()` approach). Each session stayed anchored to one clear objective.

**b. Judgment and verification**

The clearest example of not accepting a suggestion as-is was the **`sort_tasks()` refactor**. During the "Evaluate and Refine" step, the assistant proposed extracting the multi-key sort lambda into a separate `_sort_key()` helper method — arguing it would be more testable and self-documenting.

I **rejected the extraction** and instead kept the logic inline with a clear explanatory comment. My reasoning: in a lightweight module, pulling a one-line key function into its own method is *over-abstraction* — it adds indirection and a second place to look for what is fundamentally a simple sort. A well-placed comment explaining the priority-negation trick (so it sorts descending while duration stays ascending) achieves the same readability without the structural overhead.

I verified decisions throughout by **running the test suite after every change** (15 passing tests) and by **driving the Streamlit app end-to-end** to confirm behavior — for example, watching the overcommitment warning fire when 70 minutes of high-priority work hit a 60-minute budget. AI suggestions were treated as drafts to evaluate, not answers to accept blindly.

---

## 4. Testing and Verification

**a. What you tested**

I built a suite of **15 unit tests** (`tests/test_pawpal.py`, using Python's `unittest` framework) covering the core algorithmic behaviors:

- **Sorting correctness** — tasks ordered by priority rank, then shortest duration, and placed into the schedule in that order.
- **Filtering** — by active pet and by completion status (active-only, completed-only, or both).
- **Recurrence logic** — `is_due()` and `mark_completed()` correctly compute the next due date with `timedelta`, so a task completed today is skipped today but reappears once its interval passes.
- **Conflict / overcommitment** — a warning fires with the *exact* overage when high-priority work exceeds the budget, and over-budget tasks are skipped with a clear reason.
- **Edge cases** — empty task lists and owners with no pets return safely instead of crashing.

These tests mattered because the scheduler is the heart of the app, and its behavior is easy to break subtly. Asserting on *specific values* — exact orderings, dates, minute overages, and skip reasons — means a quiet regression fails loudly rather than slipping through. Recurrence tests use **fixed dates** for determinism, and each `TestCase` rebuilds fresh objects in `setUp()` so mutations never leak between tests.

**b. Confidence**

I am highly confident the scheduling **logic layer** works correctly: all 15 tests pass, they cover both happy paths and the edge cases most likely to fail, and I verified the full flow interactively in the Streamlit app. The one honest caveat is that the UI itself (`app.py`) is exercised through manual/driven verification rather than automated UI tests, so my confidence is strongest for the underlying engine.

If I had more time, I would add tests for: tie-breaking when two tasks share a priority *and* duration; monthly recurrence across month boundaries (e.g. completing on Jan 31); a zero-available-time owner; and behavior when many pets each contribute tasks that compete for the same budget.

---

## 5. Reflection

**a. What went well**

I am most satisfied with the **clean separation between the logic layer and the UI**. Because `pawpal_system.py` is pure, testable Python with no Streamlit dependency, I could test the scheduler thoroughly in isolation and then connect it to `app.py` with confidence. The recurrence engine — completing a task today and watching it correctly reappear tomorrow — and the overcommitment detection that *warns instead of crashing* are the features I'm proudest of, because they turn a basic to-do list into something that genuinely reasons about a busy owner's day.

**b. What you would improve**

In another iteration I would: make **preferences an actual scheduling input** (they're currently stored but not used to influence the plan); add support for **fixed-time commitments** (like a 2:00 PM vet visit) with real overlap detection; let the user **choose a sorting strategy** (e.g. value-density to maximize priority-per-minute); and add **automated UI tests** so the Streamlit layer is covered as rigorously as the logic layer.

**c. Key takeaway**

The biggest lesson was understanding the human engineer's role as the **lead architect**. The AI assistant is excellent at producing boilerplate, math logic, and well-structured first drafts — it wrote correct sorting keys, `timedelta` recurrence math, and test scaffolding quickly. But it does not own the *design*. It was my job to enforce the design boundaries (keeping the logic layer free of UI code), to resist over-abstraction (rejecting the `_sort_key` extraction), to maintain a clean and consistent structure across files, and to insist on readability and meaningful tests. AI accelerates the *how*; the engineer must still own the *what* and the *why*. The best results came from treating the assistant as a fast, knowledgeable collaborator whose output I always reviewed, verified, and shaped — never as an autopilot.
