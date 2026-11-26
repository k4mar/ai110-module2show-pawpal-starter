"""Automated tests for the PawPal+ logic layer (run with: python -m pytest)."""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pawpal_system import Owner, Pet, Scheduler, Task  # noqa: E402

DAY = date(2026, 10, 5)


@pytest.fixture
def owner():
    """An owner with two pets and no tasks."""
    o = Owner("Kamar", available_minutes=60)
    o.add_pet(Pet("Biscuit", "dog"))
    o.add_pet(Pet("Mochi", "cat"))
    return o


@pytest.fixture
def scheduler(owner):
    """A scheduler attached to the sample owner."""
    return Scheduler(owner)


# ---- Phase 2 basics -------------------------------------------------------- #
def test_mark_complete_changes_status():
    task = Task("Walk", "08:00")
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_adding_task_increases_pet_task_count(owner):
    pet = owner.get_pet("Biscuit")
    assert pet.task_count() == 0
    pet.add_task(Task("Walk", "08:00"))
    assert pet.task_count() == 1
    assert pet.tasks[0].pet_name == "Biscuit"


def test_owner_collects_tasks_across_pets(owner):
    owner.get_pet("Biscuit").add_task(Task("Walk", "08:00"))
    owner.get_pet("Mochi").add_task(Task("Feed", "09:00"))
    assert {t.description for t in owner.get_all_tasks()} == {"Walk", "Feed"}


def test_duplicate_pet_name_rejected(owner):
    with pytest.raises(ValueError):
        owner.add_pet(Pet("biscuit"))


def test_invalid_time_rejected():
    with pytest.raises(ValueError):
        Task("Walk", "25:00")


# ---- Sorting ---------------------------------------------------------------- #
def test_sort_by_time_is_chronological(owner, scheduler):
    pet = owner.get_pet("Biscuit")
    for desc, time in [("Dinner", "18:00"), ("Walk", "7:05"), ("Lunch", "12:30"), ("Meds", "07:00")]:
        pet.add_task(Task(desc, time, due_date=DAY))
    ordered = scheduler.sort_by_time(scheduler.get_all_tasks())
    assert [t.description for t in ordered] == ["Meds", "Walk", "Lunch", "Dinner"]


def test_sort_by_time_uses_minutes_not_string_order(scheduler):
    # As raw strings "9:00" > "10:00"; the scheduler must compare real times.
    tasks = [Task("Late", "10:00", due_date=DAY), Task("Early", "9:00", due_date=DAY)]
    assert [t.description for t in scheduler.sort_by_time(tasks)] == ["Early", "Late"]


def test_sort_by_priority_then_time(scheduler):
    tasks = [
        Task("Low", "06:00", priority="low", due_date=DAY),
        Task("High late", "20:00", priority="high", due_date=DAY),
        Task("High early", "08:00", priority="high", due_date=DAY),
        Task("Medium", "07:00", priority="medium", due_date=DAY),
    ]
    assert [t.description for t in scheduler.sort_by_priority(tasks)] == [
        "High early", "High late", "Medium", "Low"
    ]


# ---- Filtering -------------------------------------------------------------- #
def test_filter_by_pet_and_status(owner, scheduler):
    walk = owner.get_pet("Biscuit").add_task(Task("Walk", "08:00"))
    owner.get_pet("Biscuit").add_task(Task("Brush", "09:00"))
    owner.get_pet("Mochi").add_task(Task("Feed", "08:00"))
    walk.mark_complete()
    assert {t.description for t in scheduler.filter_tasks(pet_name="biscuit")} == {"Walk", "Brush"}
    assert [t.description for t in scheduler.filter_tasks(completed=True)] == ["Walk"]
    assert [t.description for t in scheduler.filter_tasks(pet_name="Biscuit", completed=False)] == ["Brush"]


def test_pet_with_no_tasks(owner, scheduler):
    assert scheduler.filter_tasks(pet_name="Mochi") == []
    assert scheduler.build_daily_plan(DAY) == []
    assert scheduler.detect_conflicts() == []


# ---- Recurrence ------------------------------------------------------------- #
def test_daily_task_completion_creates_next_day(owner, scheduler):
    walk = owner.get_pet("Biscuit").add_task(Task("Walk", "08:00", frequency="daily", due_date=DAY))
    nxt = scheduler.mark_task_complete(walk)
    assert walk.completed
    assert nxt is not None and nxt.due_date == DAY + timedelta(days=1)
    assert nxt.completed is False and nxt.time == "08:00" and nxt.pet_name == "Biscuit"
    assert owner.get_pet("Biscuit").task_count() == 2


def test_weekly_task_completion_creates_next_week(owner, scheduler):
    bath = owner.get_pet("Mochi").add_task(Task("Bath", "10:00", frequency="weekly", due_date=DAY))
    assert scheduler.mark_task_complete(bath).due_date == DAY + timedelta(weeks=1)


def test_one_off_task_does_not_recur(owner, scheduler):
    vet = owner.get_pet("Mochi").add_task(Task("Vet", "10:00", frequency="once", due_date=DAY))
    assert scheduler.mark_task_complete(vet) is None
    assert owner.get_pet("Mochi").task_count() == 1


def test_recurrence_crosses_month_boundary(owner, scheduler):
    t = owner.get_pet("Biscuit").add_task(Task("Walk", "08:00", frequency="daily", due_date=date(2026, 10, 31)))
    assert scheduler.mark_task_complete(t).due_date == date(2026, 11, 1)


# ---- Conflict detection ----------------------------------------------------- #
def test_conflict_flags_exact_same_time(owner, scheduler):
    owner.get_pet("Biscuit").add_task(Task("Walk", "08:00", 30, due_date=DAY))
    owner.get_pet("Mochi").add_task(Task("Feed", "08:00", 10, due_date=DAY))
    warnings = scheduler.detect_conflicts()
    assert len(warnings) == 1
    assert "Walk" in warnings[0] and "Feed" in warnings[0] and "different pets" in warnings[0]


def test_conflict_flags_overlapping_durations_same_pet(owner, scheduler):
    pet = owner.get_pet("Biscuit")
    pet.add_task(Task("Walk", "08:00", 30, due_date=DAY))
    pet.add_task(Task("Brush", "08:15", 10, due_date=DAY))
    assert "same pet" in scheduler.detect_conflicts()[0]


def test_back_to_back_tasks_do_not_conflict(owner, scheduler):
    pet = owner.get_pet("Biscuit")
    pet.add_task(Task("Walk", "08:00", 30, due_date=DAY))
    pet.add_task(Task("Feed", "08:30", 10, due_date=DAY))
    assert scheduler.detect_conflicts() == []


def test_same_time_different_days_do_not_conflict(owner, scheduler):
    pet = owner.get_pet("Biscuit")
    pet.add_task(Task("Walk", "08:00", 30, due_date=DAY))
    pet.add_task(Task("Walk", "08:00", 30, due_date=DAY + timedelta(days=1)))
    assert scheduler.detect_conflicts() == []


def test_completed_tasks_ignored_by_conflicts(owner, scheduler):
    walk = owner.get_pet("Biscuit").add_task(Task("Walk", "08:00", 30, due_date=DAY))
    owner.get_pet("Mochi").add_task(Task("Feed", "08:00", 10, due_date=DAY))
    walk.mark_complete()
    assert scheduler.detect_conflicts() == []


# ---- Daily plan + persistence ---------------------------------------------- #
def test_daily_plan_respects_time_budget_and_priority(owner, scheduler):
    pet = owner.get_pet("Biscuit")  # owner has 60 minutes
    pet.add_task(Task("Long low", "07:00", 40, "low", due_date=DAY))
    pet.add_task(Task("Walk", "08:00", 30, "high", due_date=DAY))
    pet.add_task(Task("Meds", "09:00", 20, "medium", due_date=DAY))
    plan = scheduler.build_daily_plan(DAY)
    scheduled = [e.task.description for e in plan if e.scheduled]
    skipped = [e.task.description for e in plan if not e.scheduled]
    assert scheduled == ["Walk", "Meds"]  # chronological output
    assert skipped == ["Long low"]
    assert sum(e.task.duration_minutes for e in plan if e.scheduled) <= owner.available_minutes


def test_json_round_trip(tmp_path, owner):
    owner.get_pet("Biscuit").add_task(Task("Walk", "08:00", 30, "high", "daily", DAY))
    path = tmp_path / "data.json"
    owner.save_to_json(path)
    loaded = Owner.load_from_json(path)
    assert loaded.to_dict() == owner.to_dict()
    assert Owner.load_from_json(tmp_path / "missing.json") is None
