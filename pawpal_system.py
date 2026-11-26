"""PawPal+ logic layer.

Classes:
    Task      - a single care activity (walk, feeding, meds, appointment...).
    Pet       - a pet and the tasks that belong to it.
    Owner     - a pet owner who manages several pets and a daily time budget.
    Scheduler - the "brain": retrieves, sorts, filters, plans and checks tasks
                across all of an owner's pets.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from pathlib import Path

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}
VALID_FREQUENCIES = ("once", "daily", "weekly")


def _parse_hhmm(value: str) -> int:
    """Convert an "HH:MM" string to minutes after midnight (raises ValueError if invalid)."""
    parsed = datetime.strptime(value.strip(), "%H:%M")
    return parsed.hour * 60 + parsed.minute


def _format_hhmm(minutes: int) -> str:
    """Convert minutes after midnight back to an "HH:MM" string."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


# --------------------------------------------------------------------------- #
# Task
# --------------------------------------------------------------------------- #
@dataclass
class Task:
    """A single pet care activity scheduled at a time on a given date."""

    description: str
    time: str  # "HH:MM", 24-hour clock
    duration_minutes: int = 15
    priority: str = "medium"  # "low" | "medium" | "high"
    frequency: str = "once"  # "once" | "daily" | "weekly"
    due_date: date = field(default_factory=date.today)
    completed: bool = False
    pet_name: str = ""  # filled in by Pet.add_task

    def __post_init__(self) -> None:
        """Validate and normalize fields so bad input fails early with a clear message."""
        self.priority = self.priority.lower()
        self.frequency = self.frequency.lower()
        if self.priority not in PRIORITY_RANK:
            raise ValueError(f"priority must be one of {list(PRIORITY_RANK)}, got {self.priority!r}")
        if self.frequency not in VALID_FREQUENCIES:
            raise ValueError(f"frequency must be one of {VALID_FREQUENCIES}, got {self.frequency!r}")
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        self.time = _format_hhmm(_parse_hhmm(self.time))  # normalizes "8:05" -> "08:05"

    @property
    def start_minutes(self) -> int:
        """Start time as minutes after midnight."""
        return _parse_hhmm(self.time)

    @property
    def end_minutes(self) -> int:
        """End time as minutes after midnight."""
        return self.start_minutes + self.duration_minutes

    @property
    def end_time(self) -> str:
        """End time as an "HH:MM" string."""
        return _format_hhmm(self.end_minutes)

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def next_occurrence(self) -> Task | None:
        """Return a fresh copy of this task for its next due date, or None if it does not repeat."""
        step = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1)}.get(self.frequency)
        if step is None:
            return None
        return Task(
            description=self.description,
            time=self.time,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            frequency=self.frequency,
            due_date=self.due_date + step,
            completed=False,
            pet_name=self.pet_name,
        )

    def overlaps(self, other: Task) -> bool:
        """True if both tasks fall on the same date and their time windows intersect."""
        if self.due_date != other.due_date:
            return False
        return self.start_minutes < other.end_minutes and other.start_minutes < self.end_minutes

    def to_dict(self) -> dict:
        """Serialize to a JSON-friendly dict."""
        data = asdict(self)
        data["due_date"] = self.due_date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        """Rebuild a Task from a dict produced by to_dict()."""
        data = dict(data)
        data["due_date"] = date.fromisoformat(data["due_date"])
        return cls(**data)


# --------------------------------------------------------------------------- #
# Pet
# --------------------------------------------------------------------------- #
@dataclass
class Pet:
    """A pet and the care tasks that belong to it."""

    name: str
    species: str = "dog"
    age: int | None = None
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> Task:
        """Attach a task to this pet (tagging it with the pet's name) and return it."""
        task.pet_name = self.name
        self.tasks.append(task)
        return task

    def remove_task(self, task: Task) -> bool:
        """Remove a task from this pet; return True if it was found."""
        if task in self.tasks:
            self.tasks.remove(task)
            return True
        return False

    def task_count(self) -> int:
        """Number of tasks this pet has (complete or not)."""
        return len(self.tasks)

    def pending_tasks(self) -> list[Task]:
        """Tasks that are not yet completed."""
        return [t for t in self.tasks if not t.completed]

    def to_dict(self) -> dict:
        """Serialize to a JSON-friendly dict."""
        return {
            "name": self.name,
            "species": self.species,
            "age": self.age,
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Pet:
        """Rebuild a Pet (and its tasks) from a dict produced by to_dict()."""
        pet = cls(name=data["name"], species=data.get("species", "dog"), age=data.get("age"))
        for task_data in data.get("tasks", []):
            pet.add_task(Task.from_dict(task_data))
        return pet


# --------------------------------------------------------------------------- #
# Owner
# --------------------------------------------------------------------------- #
class Owner:
    """A pet owner who manages several pets and has a limited amount of care time per day."""

    def __init__(self, name: str, available_minutes: int = 120):
        """Create an owner with a daily time budget (minutes available for pet care)."""
        self.name = name
        self.available_minutes = available_minutes
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> Pet:
        """Add a pet; pet names must be unique (case-insensitive) for this owner."""
        if self.get_pet(pet.name) is not None:
            raise ValueError(f"{self.name} already has a pet named {pet.name!r}")
        self.pets.append(pet)
        return pet

    def get_pet(self, name: str) -> Pet | None:
        """Find a pet by name (case-insensitive), or None."""
        for pet in self.pets:
            if pet.name.lower() == name.lower():
                return pet
        return None

    def get_all_tasks(self) -> list[Task]:
        """Every task across every pet, flattened into one list."""
        return [task for pet in self.pets for task in pet.tasks]

    def to_dict(self) -> dict:
        """Serialize to a JSON-friendly dict."""
        return {
            "name": self.name,
            "available_minutes": self.available_minutes,
            "pets": [p.to_dict() for p in self.pets],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Owner:
        """Rebuild an Owner (with pets and tasks) from a dict produced by to_dict()."""
        owner = cls(data["name"], data.get("available_minutes", 120))
        for pet_data in data.get("pets", []):
            owner.add_pet(Pet.from_dict(pet_data))
        return owner

    def save_to_json(self, path: str | Path = "data.json") -> None:
        """Write this owner, their pets and tasks to a JSON file."""
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load_from_json(cls, path: str | Path = "data.json") -> Owner | None:
        """Load an owner from a JSON file, or return None if the file does not exist."""
        path = Path(path)
        if not path.exists():
            return None
        return cls.from_dict(json.loads(path.read_text()))


# --------------------------------------------------------------------------- #
# Scheduler
# --------------------------------------------------------------------------- #
@dataclass
class PlanEntry:
    """One line of a daily plan: the task and why the scheduler included or skipped it."""

    task: Task
    scheduled: bool
    reason: str


class Scheduler:
    """The "brain": reads tasks from an Owner's pets and organizes them."""

    def __init__(self, owner: Owner):
        """Attach the scheduler to an owner; tasks are always read live from owner.pets."""
        self.owner = owner

    # ---- retrieval -------------------------------------------------------- #
    def get_all_tasks(self) -> list[Task]:
        """All tasks for all of the owner's pets."""
        return self.owner.get_all_tasks()

    def get_tasks_for_date(self, day: date | None = None) -> list[Task]:
        """Tasks due on a given date (defaults to today)."""
        day = day or date.today()
        return [t for t in self.get_all_tasks() if t.due_date == day]

    # ---- sorting ---------------------------------------------------------- #
    @staticmethod
    def sort_by_time(tasks: list[Task]) -> list[Task]:
        """Return tasks in chronological order (date, then HH:MM start time)."""
        return sorted(tasks, key=lambda t: (t.due_date, t.start_minutes))

    @staticmethod
    def sort_by_priority(tasks: list[Task]) -> list[Task]:
        """Return tasks with high priority first; ties broken by start time."""
        return sorted(tasks, key=lambda t: (PRIORITY_RANK[t.priority], t.due_date, t.start_minutes))

    # ---- filtering -------------------------------------------------------- #
    def filter_tasks(
        self,
        pet_name: str | None = None,
        completed: bool | None = None,
        tasks: list[Task] | None = None,
    ) -> list[Task]:
        """Filter tasks by pet name and/or completion status; None means "don't filter on this"."""
        tasks = self.get_all_tasks() if tasks is None else tasks
        result = []
        for t in tasks:
            if pet_name is not None and t.pet_name.lower() != pet_name.lower():
                continue
            if completed is not None and t.completed != completed:
                continue
            result.append(t)
        return result

    # ---- recurring tasks -------------------------------------------------- #
    def mark_task_complete(self, task: Task) -> Task | None:
        """Complete a task; if it repeats, add and return its next occurrence on the same pet."""
        task.mark_complete()
        nxt = task.next_occurrence()
        if nxt is None:
            return None
        pet = self.owner.get_pet(task.pet_name)
        if pet is None:
            raise ValueError(f"Task {task.description!r} is not attached to one of {self.owner.name}'s pets")
        return pet.add_task(nxt)

    # ---- conflict detection ---------------------------------------------- #
    def detect_conflicts(self, tasks: list[Task] | None = None) -> list[str]:
        """Return warning messages for pending tasks whose time windows overlap (never raises)."""
        tasks = self.get_all_tasks() if tasks is None else tasks
        pending = self.sort_by_time([t for t in tasks if not t.completed])
        warnings = []
        for i, a in enumerate(pending):
            for b in pending[i + 1:]:
                # List is sorted by (date, start): once b starts after a ends (or is on a
                # later date), no later task can overlap a, so stop scanning early.
                if b.due_date != a.due_date or b.start_minutes >= a.end_minutes:
                    break
                kind = "same pet" if a.pet_name == b.pet_name else "different pets"
                warnings.append(
                    f"⚠️ Conflict on {a.due_date.isoformat()} ({kind}): "
                    f"{a.pet_name}'s '{a.description}' {a.time}-{a.end_time} overlaps "
                    f"{b.pet_name}'s '{b.description}' {b.time}-{b.end_time}"
                )
        return warnings

    # ---- daily plan ------------------------------------------------------- #
    def build_daily_plan(self, day: date | None = None) -> list[PlanEntry]:
        """Pick which of the day's pending tasks fit the owner's time budget and explain each choice.

        Tasks are considered highest priority first (earlier time breaks ties). A task is
        scheduled if its duration still fits in the remaining budget; otherwise it is skipped.
        The returned plan is in chronological order.
        """
        remaining = self.owner.available_minutes
        entries: list[PlanEntry] = []
        pending = [t for t in self.get_tasks_for_date(day) if not t.completed]
        for task in self.sort_by_priority(pending):
            if task.duration_minutes <= remaining:
                remaining -= task.duration_minutes
                reason = f"{task.priority} priority, fits in budget ({remaining} min left)"
                entries.append(PlanEntry(task, True, reason))
            else:
                reason = f"skipped: needs {task.duration_minutes} min, only {remaining} min left"
                entries.append(PlanEntry(task, False, reason))
        entries.sort(key=lambda e: e.task.start_minutes)
        return entries

    def format_schedule(self, day: date | None = None) -> str:
        """Readable multi-line "Today's Schedule" for the terminal."""
        day = day or date.today()
        plan = self.build_daily_plan(day)
        used = sum(e.task.duration_minutes for e in plan if e.scheduled)
        lines = [
            f"🐾 Today's Schedule for {self.owner.name} — {day.strftime('%A, %b %d %Y')}",
            f"   Time budget: {used}/{self.owner.available_minutes} min used",
            "-" * 72,
        ]
        if not plan:
            lines.append("   No pending tasks today.")
        for e in plan:
            mark = "✅" if e.scheduled else "⏭️ "
            t = e.task
            lines.append(
                f" {mark} {t.time}-{t.end_time}  {t.pet_name:<8} {t.description:<22} "
                f"[{t.priority}, {t.frequency}]"
            )
            lines.append(f"      ↳ {e.reason}")
        conflicts = self.detect_conflicts(self.get_tasks_for_date(day))
        if conflicts:
            lines.append("-" * 72)
            lines.extend(conflicts)
        return "\n".join(lines)
