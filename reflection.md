# PawPal+ Project Reflection

## 1. System Design

**Three core actions a user should be able to perform**

1. Add a pet (name, species, age) to their household.
2. Schedule a care task for a pet: what it is, when, how long, how important, and whether it repeats.
3. See today's plan: which tasks fit in the time they have, in time order, with any conflicts flagged.

**a. Initial design**

The first UML (`diagrams/uml_draft.mmd`) had four classes:

- **Task**: one activity, with a description, time, frequency and completion flag. It is responsible for marking itself complete.
- **Pet**: a pet's details plus its list of tasks. It is responsible for adding tasks.
- **Owner**: holds multiple pets and gives access to all of their tasks in one list.
- **Scheduler**: the "brain". It takes an Owner and retrieves and sorts tasks across every pet.

Relationships: an Owner *has* many Pets, a Pet *has* many Tasks, and the Scheduler *reads from* the Owner. `Task` and `Pet` are dataclasses because they mostly hold data.

**b. Design changes**

- **Task gained `duration_minutes`, `priority`, `due_date` and `pet_name`.** Duration was needed for real overlap checks and the time budget, `due_date` for recurrence, and `pet_name` so a task pulled out of the flattened list still knows whose it is (for filtering, conflict messages, and putting the next occurrence on the right pet).
- **Owner gained `available_minutes`.** The starter README asks the plan to consider constraints such as time available, so the owner now carries a daily budget.
- **New `PlanEntry` dataclass.** `build_daily_plan()` returns `PlanEntry(task, scheduled, reason)` instead of bare tasks, so the UI can explain *why* each task was included or skipped.
- **Sorting methods became static and take a task list.** This lets the same `sort_by_time()` sort "all tasks", "today's tasks" or a filtered list, instead of always reading everything from the owner.
- **The Scheduler never stores its own copy of tasks.** It always reads live from `owner.pets`, so there is one source of truth and nothing gets out of sync after a pet or task is added.

The final diagram is in `diagrams/uml_final.mmd`.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers:

- **Time budget:** the owner's `available_minutes` for the day.
- **Priority:** high → medium → low decides who gets the budget first.
- **Clock time:** the earlier task wins a priority tie, and the final plan is shown in time order.
- **Date and completion:** only pending tasks due on the chosen day are planned.

Priority mattered most because missing meds or a meal is worse than skipping enrichment. The time budget was next because it is the real constraint for a busy owner.

**b. Tradeoffs**

- **The plan is greedy.** It walks tasks in priority order and takes each one that still fits. It doesn't search for the combination that uses the budget best. For example, one 45-min medium task might be picked when two 20-min medium tasks would have used the time better. This is reasonable here because a pet owner cares more that high-priority care always gets in, and that the plan is easy to predict and explain, than about squeezing out the last few minutes.
- **Conflicts are warnings, not fixes.** The scheduler reports overlapping tasks but doesn't move them. The owner knows whether two tasks can overlap (feeding the cat during the dog's walk might be fine if two people are home), so the app shouldn't guess.
- **The plan doesn't check whether chosen tasks overlap.** A task can be ✅ scheduled and also appear in a conflict warning, so the owner sees both pieces of information.

---

## 3. AI Collaboration

**a. How you used AI**

I used Claude in agent mode for nearly the whole build. I gave it the assignment page, and it found and cloned the CodePath starter repo, drafted the UML, generated the class skeleton, and then implemented the classes, the `main.py` demo, the pytest suite and the Streamlit wiring. The most effective feature was that the agent ran its own checks after each step: `python main.py`, `python -m pytest`, and a headless Streamlit test that clicked through adding pets, adding tasks and completing a task. That meant problems surfaced right away instead of at the end.

The most useful prompt was the full assignment text, because it already listed the phases, file names and required methods (`sort_by_time`, `mark_task_complete`, the README sections). The agent could follow that structure directly, and the commit history ended up matching the phases. I worked in one long session instead of separate chats per phase. That kept the full context in one place, but next time I would split design, algorithms and testing into separate chats so each review stays focused and I can compare them.

**b. Judgment and verification**

Several first drafts were changed before they were kept:

- **Conflict loop.** The first version of `detect_conflicts()` had a nested `if`/`break` that worked but was confusing to read. It was rewritten as one early-exit condition, with a comment explaining why stopping early is safe: tasks are sorted by start time, so once a task starts after the current one ends, nothing later can overlap it. The conflict tests (exact match, partial overlap, back-to-back, different days) passed both before and after, which confirmed the simpler version behaves the same.
- **Fragile demo lookups.** `main.py` first picked tasks with list indexes like `filter_tasks(...)[1]`. That would silently grab the wrong task if the order ever changed, so it was replaced with a lookup by description.
- **String sorting.** Sorting `"HH:MM"` strings directly gets `"9:00"` vs `"10:00"` wrong. Times are converted to minutes after midnight instead, and `test_sort_by_time_uses_minutes_not_string_order` locks that in.

In general, I didn't trust a feature until the demo output or a test showed it working.

---

## 4. Testing and Verification

**a. What you tested**

21 pytest tests (`tests/test_pawpal.py`) cover task completion, adding tasks, chronological and priority sorting, filtering by pet and status, daily/weekly/one-off recurrence (including a month boundary), conflict detection (exact match, partial overlap, back-to-back, different days, completed tasks), the time-budgeted plan, and JSON save/load. These matter because sorting, recurrence and conflicts are exactly where off-by-one or string-comparison bugs hide, and the UI depends on them being right.

**b. Confidence**

4/5. All core behaviors and their main edge cases pass. Next tests: tasks that cross midnight (e.g. 23:30 for 60 min), editing or deleting tasks from the UI, automated Streamlit UI tests, and a planner that suggests the next free slot when there's a conflict.

---

## 5. Reflection

**a. What went well**

The separation between the logic layer and the UI. Because `pawpal_system.py` was finished and tested from the command line first, wiring up Streamlit was mostly calling methods that already worked. The daily plan's "why" column is the feature I like best: it makes the scheduler's decisions easy to follow instead of a black box.

**b. What you would improve**

I would replace the greedy planner with one that picks the best combination of tasks for the time budget, have the app suggest the next free time slot when it finds a conflict, and add editing and deleting tasks in the UI. I would also handle tasks that run past midnight and add automated UI tests.

**c. Key takeaway**

AI can produce a working system very quickly, so the human's job shifts from typing code to setting direction and checking results. The assignment spec, the test suite and the demo output were what actually kept the project correct, not the AI's confidence. If I hand off more of the work, I have to be stricter about reviewing it, because I am still the one who has to explain and defend every design choice.
