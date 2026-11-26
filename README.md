# 🐾 PawPal+

PawPal+ is a pet care planner built with Python OOP and Streamlit. An owner adds pets and care tasks (walks, feedings, meds, appointments), and the scheduler builds a daily plan that fits the owner's time budget, explains each choice, flags time conflicts, and automatically re-creates daily/weekly tasks when they're completed.

The backend (`pawpal_system.py`) was built and verified **CLI-first** with `main.py` and a pytest suite before being wired into the Streamlit UI (`app.py`).

## Features

- **Multi-pet management** — one `Owner` holds any number of `Pet`s; pet names are unique per owner.
- **Rich tasks** — each `Task` has a time (`HH:MM`), duration, priority (low/medium/high), frequency (once/daily/weekly) and due date. Bad input (e.g. `25:00`, unknown priority) is rejected with a clear error.
- **Sorting by time** — chronological order that compares real clock minutes, so `9:00` sorts before `10:00`.
- **Priority sorting** — high → medium → low, with start time as the tiebreaker.
- **Filtering** — by pet name, completion status, or both.
- **Daily recurrence** — completing a daily task creates tomorrow's copy; weekly tasks roll forward 7 days (`timedelta`).
- **Conflict warnings** — overlapping time windows are reported as readable warnings (same pet or different pets) instead of crashing.
- **Time-budgeted daily plan** — tasks are chosen highest priority first until the owner's available minutes run out; each entry says *why* it was scheduled or skipped.
- **Data persistence** — pets and tasks are saved to `data.json` and reloaded on startup (stretch Challenge 2).

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python main.py          # CLI demo
python -m pytest        # tests
streamlit run app.py    # web app
```

## Project structure

| File | Purpose |
|------|---------|
| `pawpal_system.py` | Logic layer: `Task`, `Pet`, `Owner`, `Scheduler`, `PlanEntry` |
| `main.py` | CLI demo script that exercises every scheduler feature |
| `app.py` | Streamlit UI wired to the logic layer via `st.session_state` |
| `tests/test_pawpal.py` | Automated pytest suite (21 tests) |
| `diagrams/uml_draft.mmd` | Phase 1 UML draft |
| `diagrams/uml_final.mmd` | Final UML matching the implementation |
| `reflection.md` | Design and AI-collaboration reflection |

## 🖥️ Sample Output

Output of `python main.py` (the "Today's Schedule" portion). The owner has a 90-minute budget, so lower-priority tasks are skipped once it runs out:

```
🐾 Today's Schedule for Kamar — Wednesday, Nov 25 2026
   Time budget: 85/90 min used
------------------------------------------------------------------------
 ✅ 07:00-07:30  Biscuit  Morning walk           [high, daily]
      ↳ high priority, fits in budget (60 min left)
 ✅ 07:30-07:35  Biscuit  Heartworm pill         [high, once]
      ↳ high priority, fits in budget (55 min left)
 ✅ 07:30-07:40  Mochi    Breakfast              [high, daily]
      ↳ high priority, fits in budget (45 min left)
 ✅ 09:00-09:10  Mochi    Litter box             [medium, daily]
      ↳ medium priority, fits in budget (5 min left)
 ⏭️  15:00-15:20  Biscuit  Puzzle toy             [low, daily]
      ↳ skipped: needs 20 min, only 5 min left
 ⏭️  16:00-16:45  Mochi    Vet appointment        [medium, once]
      ↳ skipped: needs 45 min, only 5 min left
 ✅ 18:30-19:00  Biscuit  Evening walk           [high, daily]
      ↳ high priority, fits in budget (15 min left)
 ⏭️  18:45-19:00  Biscuit  Brushing               [low, weekly]
      ↳ skipped: needs 15 min, only 5 min left
------------------------------------------------------------------------
⚠️ Conflict on 2026-11-25 (different pets): Biscuit's 'Heartworm pill' 07:30-07:35 overlaps Mochi's 'Breakfast' 07:30-07:40
⚠️ Conflict on 2026-11-25 (same pet): Biscuit's 'Evening walk' 18:30-19:00 overlaps Biscuit's 'Brushing' 18:45-19:00
```

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time()`, `Scheduler.sort_by_priority()` | `sorted()` with a lambda key of `(due_date, start_minutes)`; priority sort uses `(PRIORITY_RANK, date, start)` |
| Filtering | `Scheduler.filter_tasks(pet_name=..., completed=...)`, `Scheduler.get_tasks_for_date()` | Either filter can be omitted; pet names match case-insensitively |
| Conflict handling | `Scheduler.detect_conflicts()`, `Task.overlaps()` | Flags overlapping windows (`start < other.end and other.start < end`) on the same date, ignores completed tasks, returns warning strings |
| Recurring tasks | `Scheduler.mark_task_complete()`, `Task.next_occurrence()` | Daily → `+timedelta(days=1)`, weekly → `+timedelta(weeks=1)`, once → no copy |
| Time-budget planning | `Scheduler.build_daily_plan()`, `Scheduler.format_schedule()` | Greedy by priority until `Owner.available_minutes` is used up; output shown in time order with a reason per task |

**Sorting.** Times are stored as `"HH:MM"` strings but compared as minutes after midnight (`Task.start_minutes`), so input like `"7:05"` is normalized and sorts correctly.

**Filtering.** `filter_tasks()` treats `None` as "don't filter on this", so the same method powers "Mochi only", "completed only", and "Biscuit's pending tasks".

**Conflict detection.** Tasks are sorted by start time, then each task is compared with the ones after it until one starts after it ends. Exact same-time tasks and partial overlaps are both caught; back-to-back tasks (08:00–08:30 then 08:30) are not conflicts.

**Recurring tasks.** `mark_task_complete()` marks the task done and, if it repeats, attaches the next occurrence to the same pet, so history is kept and the new task shows up in future plans.

## 🧪 Testing PawPal+

```bash
python -m pytest
```

The suite in `tests/test_pawpal.py` covers:

- **Basics:** `mark_complete()` changes status; adding a task increases the pet's task count; owners collect tasks across pets; invalid times and duplicate pet names are rejected.
- **Sorting correctness:** chronological order, real-time comparison (`9:00` before `10:00`), priority-then-time ordering.
- **Filtering:** by pet, by status, combined; a pet with no tasks.
- **Recurrence:** daily → next day, weekly → next week, one-off tasks don't recur, month boundary (Oct 31 → Nov 1).
- **Conflict detection:** exact duplicate times, overlapping durations for the same pet, back-to-back tasks (no conflict), same time on different days (no conflict), completed tasks ignored.
- **Planning and persistence:** the daily plan respects the time budget and priority; JSON save/load round-trips.

Sample run:

```
============================= test session starts ==============================
platform linux -- Python 3.13.18, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/claude/pawpal-plus
plugins: platformdirs-4.13.5, anyio-4.15.1
collected 21 items

tests/test_pawpal.py .....................                               [100%]

============================== 21 passed in 0.04s ==============================
```

**Confidence level:** ⭐⭐⭐⭐ (4/5). Every core behavior and the main edge cases are tested and passing. The greedy planner is simple by design (see `reflection.md`), and the Streamlit layer is tested by hand rather than automatically.

## 📸 Demo Walkthrough

**Main UI features**

- **Sidebar:** set the owner's name and the minutes available for pet care today; reset all data.
- **🐶 Pets:** add a pet (name, species, age); a table shows each pet and its pending task count.
- **📝 Schedule a task:** pick the pet, describe the task, then set date, time, duration, priority and how often it repeats.
- **📅 Daily plan:** choose a day and see the scheduler's plan in time order. ✅ means scheduled, ⏭️ means skipped, and a "Why" column explains each one. A progress bar shows how much of the time budget is used. Conflicts appear as yellow `st.warning` banners above the plan.
- **🔎 All tasks:** filter by pet and status, sort by time or priority, and click **Done** to complete a task. Repeating tasks show a toast with the next due date.

**Example workflow**

1. Set the owner to "Kamar" with 90 minutes available.
2. Add pets **Biscuit** (dog) and **Mochi** (cat).
3. Schedule Biscuit's *Morning walk* at 07:00 (30 min, high, daily) and Mochi's *Breakfast* at 07:15 (10 min, high, daily).
4. The Daily plan shows a warning that the walk (07:00–07:30) overlaps breakfast (07:15–07:25), so the owner can move one.
5. Add a 200-minute low-priority *Puzzle toy* session. The plan marks it ⏭️ *skipped: needs 200 min, only 50 min left*.
6. Click **Done** on the morning walk. It is struck through, and a new *Morning walk* appears for tomorrow.
7. Refresh the browser. Everything is still there, loaded from `data.json`.

**Key scheduler behaviors shown:** priority-first budgeting, chronological display, conflict warnings, daily recurrence, filtering, and persistence.

**CLI output** (rest of `python main.py`: sorting, filtering, recurrence, conflicts):

```
Sorted by time:
   2026-11-25 07:00  Biscuit  Morning walk           [high] (todo)
   2026-11-25 07:30  Biscuit  Heartworm pill         [high] (todo)
   2026-11-25 07:30  Mochi    Breakfast              [high] (todo)
   2026-11-25 09:00  Mochi    Litter box             [medium] (todo)
   2026-11-25 15:00  Biscuit  Puzzle toy             [low] (todo)
   2026-11-25 16:00  Mochi    Vet appointment        [medium] (todo)
   2026-11-25 18:30  Biscuit  Evening walk           [high] (todo)
   2026-11-25 18:45  Biscuit  Brushing               [low] (todo)

Sorted by priority, then time:
   2026-11-25 07:00  Biscuit  Morning walk           [high] (todo)
   2026-11-25 07:30  Biscuit  Heartworm pill         [high] (todo)
   2026-11-25 07:30  Mochi    Breakfast              [high] (todo)
   2026-11-25 18:30  Biscuit  Evening walk           [high] (todo)
   2026-11-25 09:00  Mochi    Litter box             [medium] (todo)
   2026-11-25 16:00  Mochi    Vet appointment        [medium] (todo)
   2026-11-25 15:00  Biscuit  Puzzle toy             [low] (todo)
   2026-11-25 18:45  Biscuit  Brushing               [low] (todo)

Filter — Mochi only:
   2026-11-25 07:30  Mochi    Breakfast              [high] (todo)
   2026-11-25 09:00  Mochi    Litter box             [medium] (todo)
   2026-11-25 16:00  Mochi    Vet appointment        [medium] (todo)

Marked 'Morning walk' complete → next occurrence created for 2026-11-26
Marked 'Heartworm pill' complete → next occurrence: None

Filter — completed tasks:
   2026-11-25 07:00  Biscuit  Morning walk           [high] (done)
   2026-11-25 07:30  Biscuit  Heartworm pill         [high] (done)

Filter — Biscuit, still pending:
   2026-11-25 18:30  Biscuit  Evening walk           [high] (todo)
   2026-11-25 15:00  Biscuit  Puzzle toy             [low] (todo)
   2026-11-25 18:45  Biscuit  Brushing               [low] (todo)
   2026-11-26 07:00  Biscuit  Morning walk           [high] (todo)

Conflict check (all pending tasks):
   ⚠️ Conflict on 2026-11-25 (same pet): Biscuit's 'Evening walk' 18:30-19:00 overlaps Biscuit's 'Brushing' 18:45-19:00
```
