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

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
