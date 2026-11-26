"""CLI demo for PawPal+: exercises the logic layer without the Streamlit UI."""

from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task


def print_tasks(title: str, tasks: list[Task]) -> None:
    """Print a titled list of tasks, one per line."""
    print(f"\n{title}")
    if not tasks:
        print("   (none)")
    for t in tasks:
        status = "done" if t.completed else "todo"
        print(f"   {t.due_date} {t.time}  {t.pet_name:<8} {t.description:<22} [{t.priority}] ({status})")


def main() -> None:
    """Build a sample owner with two pets and demo every Scheduler feature."""
    today = date.today()
    owner = Owner("Kamar", available_minutes=90)
    biscuit = owner.add_pet(Pet("Biscuit", "dog", age=4))
    mochi = owner.add_pet(Pet("Mochi", "cat", age=2))

    # Added deliberately out of order to show sorting.
    biscuit.add_task(Task("Evening walk", "18:30", 30, "high", "daily", today))
    mochi.add_task(Task("Breakfast", "07:30", 10, "high", "daily", today))
    biscuit.add_task(Task("Morning walk", "07:00", 30, "high", "daily", today))
    mochi.add_task(Task("Litter box", "09:00", 10, "medium", "daily", today))
    biscuit.add_task(Task("Heartworm pill", "07:30", 5, "high", "once", today))   # conflicts with Mochi's breakfast
    biscuit.add_task(Task("Puzzle toy", "15:00", 20, "low", "daily", today))
    mochi.add_task(Task("Vet appointment", "16:00", 45, "medium", "once", today))
    biscuit.add_task(Task("Brushing", "18:45", 15, "low", "weekly", today))       # overlaps Biscuit's evening walk

    scheduler = Scheduler(owner)

    print(scheduler.format_schedule(today))

    print_tasks("Sorted by time:", scheduler.sort_by_time(scheduler.get_tasks_for_date(today)))
    print_tasks("Sorted by priority, then time:", scheduler.sort_by_priority(scheduler.get_tasks_for_date(today)))
    print_tasks("Filter — Mochi only:", scheduler.filter_tasks(pet_name="Mochi"))

    def find(pet: str, description: str) -> Task:
        return next(t for t in scheduler.filter_tasks(pet_name=pet) if t.description == description)

    morning_walk = find("Biscuit", "Morning walk")
    nxt = scheduler.mark_task_complete(morning_walk)
    print(f"\nMarked '{morning_walk.description}' complete → next occurrence created for {nxt.due_date}")
    pill = find("Biscuit", "Heartworm pill")
    print(f"Marked '{pill.description}' complete → next occurrence: {scheduler.mark_task_complete(pill)}")

    print_tasks("Filter — completed tasks:", scheduler.filter_tasks(completed=True))
    print_tasks("Filter — Biscuit, still pending:", scheduler.filter_tasks(pet_name="Biscuit", completed=False))

    print("\nConflict check (all pending tasks):")
    for warning in scheduler.detect_conflicts() or ["   No conflicts 🎉"]:
        print("  ", warning)


if __name__ == "__main__":
    main()
