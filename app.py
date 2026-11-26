"""PawPal+ Streamlit UI — a thin layer over the classes in pawpal_system.py."""

from datetime import date, time

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

DATA_FILE = "data.json"

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Plan your pets' walks, meals, meds and appointments — sorted, budgeted and conflict-checked.")

# --------------------------------------------------------------------------- #
# Session "memory": create the Owner once, then reuse it on every rerun.
# --------------------------------------------------------------------------- #
if "owner" not in st.session_state:
    st.session_state.owner = Owner.load_from_json(DATA_FILE) or Owner("Jordan", available_minutes=120)

owner: Owner = st.session_state.owner
scheduler = Scheduler(owner)


def save() -> None:
    """Persist the current owner to data.json after every change."""
    owner.save_to_json(DATA_FILE)


# --------------------------------------------------------------------------- #
# Owner settings
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("👤 Owner")
    new_name = st.text_input("Owner name", value=owner.name)
    new_budget = st.number_input(
        "Minutes available for pet care today", min_value=10, max_value=1440,
        value=owner.available_minutes, step=10,
    )
    if new_name != owner.name or new_budget != owner.available_minutes:
        owner.name, owner.available_minutes = new_name, int(new_budget)
        save()
    st.divider()
    if st.button("🗑️ Reset all data"):
        st.session_state.owner = Owner("Jordan", available_minutes=120)
        save()
        st.rerun()

# --------------------------------------------------------------------------- #
# Add a pet
# --------------------------------------------------------------------------- #
st.subheader("🐶 Pets")
with st.form("add_pet", clear_on_submit=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    pet_name = c1.text_input("Pet name")
    species = c2.selectbox("Species", ["dog", "cat", "bird", "other"])
    age = c3.number_input("Age", min_value=0, max_value=40, value=1)
    if st.form_submit_button("Add pet"):
        if not pet_name.strip():
            st.error("Give your pet a name first.")
        else:
            try:
                owner.add_pet(Pet(pet_name.strip(), species, int(age)))
                save()
                st.success(f"Added {pet_name.strip()}!")
            except ValueError as err:
                st.error(str(err))

if owner.pets:
    st.table([
        {"Pet": p.name, "Species": p.species, "Age": p.age, "Pending tasks": len(p.pending_tasks())}
        for p in owner.pets
    ])
else:
    st.info("No pets yet — add one above.")

# --------------------------------------------------------------------------- #
# Schedule a task
# --------------------------------------------------------------------------- #
st.subheader("📝 Schedule a task")
if owner.pets:
    with st.form("add_task", clear_on_submit=True):
        c1, c2 = st.columns(2)
        task_pet = c1.selectbox("For", [p.name for p in owner.pets])
        desc = c2.text_input("Task", placeholder="Morning walk")
        c3, c4, c5 = st.columns(3)
        when_day = c3.date_input("Date", value=date.today())
        when_time = c4.time_input("Time", value=time(8, 0), step=300)
        duration = c5.number_input("Duration (min)", min_value=1, max_value=480, value=20)
        c6, c7 = st.columns(2)
        priority = c6.selectbox("Priority", ["high", "medium", "low"], index=1)
        frequency = c7.selectbox("Repeats", ["once", "daily", "weekly"])
        if st.form_submit_button("Add task"):
            if not desc.strip():
                st.error("Describe the task first.")
            else:
                owner.get_pet(task_pet).add_task(Task(
                    desc.strip(), when_time.strftime("%H:%M"), int(duration),
                    priority, frequency, when_day,
                ))
                save()
                st.success(f"Scheduled '{desc.strip()}' for {task_pet}.")
else:
    st.caption("Add a pet to start scheduling tasks.")

# --------------------------------------------------------------------------- #
# Today's plan (Scheduler.build_daily_plan + detect_conflicts)
# --------------------------------------------------------------------------- #
st.divider()
st.subheader("📅 Daily plan")
plan_day = st.date_input("Plan for", value=date.today(), key="plan_day")

conflicts = scheduler.detect_conflicts(scheduler.get_tasks_for_date(plan_day))
for warning in conflicts:
    st.warning(warning + " — consider moving one of these tasks.")

plan = scheduler.build_daily_plan(plan_day)
if not plan:
    st.info("Nothing pending for this day. 🎉")
else:
    used = sum(e.task.duration_minutes for e in plan if e.scheduled)
    st.progress(min(used / owner.available_minutes, 1.0),
                text=f"{used} of {owner.available_minutes} minutes planned")
    st.table([
        {
            "": "✅" if e.scheduled else "⏭️",
            "Time": f"{e.task.time}–{e.task.end_time}",
            "Pet": e.task.pet_name,
            "Task": e.task.description,
            "Priority": e.task.priority,
            "Repeats": e.task.frequency,
            "Why": e.reason,
        }
        for e in plan
    ])
    skipped = [e for e in plan if not e.scheduled]
    if skipped:
        st.caption(f"{len(skipped)} task(s) skipped because they didn't fit your time budget. "
                   "Lower-priority tasks are dropped first.")
    else:
        st.success("Everything fits in today's time budget!")

# --------------------------------------------------------------------------- #
# Browse, filter and complete tasks
# --------------------------------------------------------------------------- #
st.divider()
st.subheader("🔎 All tasks")
f1, f2, f3 = st.columns(3)
pet_filter = f1.selectbox("Pet", ["All"] + [p.name for p in owner.pets])
status_filter = f2.selectbox("Status", ["Pending", "Completed", "All"])
sort_mode = f3.selectbox("Sort by", ["Time", "Priority"])

filtered = scheduler.filter_tasks(
    pet_name=None if pet_filter == "All" else pet_filter,
    completed={"Pending": False, "Completed": True, "All": None}[status_filter],
)
filtered = scheduler.sort_by_time(filtered) if sort_mode == "Time" else scheduler.sort_by_priority(filtered)

if not filtered:
    st.caption("No tasks match these filters.")
for i, task in enumerate(filtered):
    c1, c2 = st.columns([5, 1])
    label = (f"**{task.due_date:%a %b %d} {task.time}** · {task.pet_name} · {task.description} "
             f"· {task.duration_minutes} min · {task.priority} · {task.frequency}")
    c1.markdown(("~~" + label + "~~") if task.completed else label)
    if not task.completed and c2.button("Done", key=f"done_{i}_{id(task)}"):
        nxt = scheduler.mark_task_complete(task)
        save()
        if nxt:
            st.toast(f"Next '{nxt.description}' scheduled for {nxt.due_date:%a %b %d}")
        st.rerun()
