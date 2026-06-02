from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timedelta
from typing import Any

from langchain_core.tools import tool

from src.graph.utils.data_store import create_task, get_tasks, get_users, update_task

logger = logging.getLogger(__name__)


# helpers
def _df():
    return get_tasks()


def _parse_date(value: Any) -> datetime | None:
    try:
        return datetime.strptime(str(value), "%Y/%m/%d")
    except Exception:
        return None


# Statistical
@tool
def count_tasks_by_status(status: str) -> str:
    """
    Count tasks with a given status.
    Pass 'all' to get a breakdown of every status.
    Valid statuses: 'Open', 'In Progress', 'Review', 'Done'
    """
    logger.debug("count_tasks_by_status called with status=%r", status)
    df = _df()
    if status.lower() == "all":
        result = json.dumps(df["status"].value_counts().to_dict(), ensure_ascii=False)
    else:
        result = str(int((df["status"] == status).sum()))
    logger.info("count_tasks_by_status(status=%r) -> %s", status, result)
    return result


@tool
def count_tasks_by_priority(priority: str) -> str:
    """
    Count tasks with a given priority.
    Pass 'all' to get a breakdown of every priority.
    Valid priorities: 'Low', 'Medium', 'High', 'Critical'
    """
    logger.debug("count_tasks_by_priority called with priority=%r", priority)
    df = _df()
    if priority.lower() == "all":
        result = json.dumps(df["priority"].value_counts().to_dict(), ensure_ascii=False)
    else:
        result = str(int((df["priority"] == priority).sum()))
    logger.info("count_tasks_by_priority(priority=%r) -> %s", priority, result)
    return result


@tool
def count_tasks_closed_in_last_n_days(days: int) -> str:
    """
    Count tasks with status 'Done' whose due_time falls within the last `days` days.
    Use days=30 for 'last month', days=7 for 'last week'.
    """
    logger.debug("count_tasks_closed_in_last_n_days called with days=%r", days)
    df = _df()
    done = df[df["status"] == "Done"].copy()
    cutoff = datetime.now() - timedelta(days=days)
    done["due_dt"] = done["due_time"].apply(_parse_date)
    result = str(int((done["due_dt"] >= cutoff).sum()))
    logger.info("count_tasks_closed_in_last_n_days(days=%r) -> %s", days, result)
    return result


@tool
def count_overdue_tasks() -> str:
    """Count tasks that are not Done but whose due_time has already passed."""
    logger.debug("count_overdue_tasks called")
    df = _df()
    active = df[df["status"] != "Done"].copy()
    active["due_dt"] = active["due_time"].apply(_parse_date)
    today = datetime.now()
    result = str(int((active["due_dt"] < today).sum()))
    logger.info("count_overdue_tasks() -> %s", result)
    return result


@tool
def average_close_time_days() -> str:
    """
    Average number of days between create_time and due_time for Done tasks.
    Returns a float formatted to one decimal place.
    """
    logger.debug("average_close_time_days called")
    df = _df()
    done = df[df["status"] == "Done"].copy()
    done["create_dt"] = done["create_time"].apply(_parse_date)
    done["due_dt"] = done["due_time"].apply(_parse_date)
    done = done.dropna(subset=["create_dt", "due_dt"])
    done["delta"] = (done["due_dt"] - done["create_dt"]).dt.days
    avg = done["delta"].mean()
    result = f"{avg:.1f}" if not math.isnan(avg) else "0"
    logger.info("average_close_time_days() -> %s", result)
    return result


# Analytical
@tool
def tasks_per_person() -> str:
    """Return a JSON object mapping each person's fullname to their task count, sorted descending."""
    logger.debug("tasks_per_person called")
    df = _df()
    counts = df.groupby("assignee_name")["id"].count().sort_values(ascending=False).to_dict()
    result = json.dumps(counts, ensure_ascii=False)
    logger.info("tasks_per_person() -> %s", result)
    return result


@tool
def tasks_per_department() -> str:
    """Return a JSON object mapping each department to its task count, sorted descending."""
    logger.debug("tasks_per_department called")
    df = _df()
    counts = df.groupby("assignee_dept")["id"].count().sort_values(ascending=False).to_dict()
    result = json.dumps(counts, ensure_ascii=False)
    logger.info("tasks_per_department() -> %s", result)
    return result


# Search
@tool
def get_tasks_for_person(name: str) -> str:
    """
    Return a JSON list of tasks assigned to a person whose fullname contains `name`.
    Supports partial matches, e.g. 'Saberi' matches 'Ali Saberi'.
    """
    logger.debug("get_tasks_for_person called with name=%r", name)
    df = _df()
    matched = df[df["assignee_name"].str.contains(name, na=False)]
    logger.info("get_tasks_for_person(name=%r) -> %d rows", name, len(matched))
    cols = ["id", "title", "status", "priority", "due_time", "assignee_name"]
    return matched[cols].to_json(orient="records", force_ascii=False)


@tool
def get_tasks_for_department(department: str) -> str:
    """
    Return a JSON list of tasks belonging to a department.
    Use the exact department name as it appears in the data.
    """
    logger.debug("get_tasks_for_department called with department=%r", department)
    df = _df()
    matched = df[df["assignee_dept"].str.contains(department, na=False)]
    logger.info("get_tasks_for_department(department=%r) -> %d rows", department, len(matched))
    cols = ["id", "title", "status", "priority", "assignee_name"]
    return matched[cols].to_json(orient="records", force_ascii=False)


@tool
def get_tasks_by_status_and_department(status: str, department: str) -> str:
    """
    Filter tasks by status AND department.
    Pass an empty string '' to skip filtering on either field.
    """
    logger.debug(
        "get_tasks_by_status_and_department called with status=%r, department=%r",
        status,
        department,
    )
    df = _df()
    if status:
        df = df[df["status"] == status]
    if department:
        df = df[df["assignee_dept"].str.contains(department, na=False)]
    logger.info(
        "get_tasks_by_status_and_department(status=%r, department=%r) -> %d rows",
        status,
        department,
        len(df),
    )
    cols = ["id", "title", "status", "priority", "assignee_name", "due_time"]
    return df[cols].to_json(orient="records", force_ascii=False)


@tool
def get_task_by_id(task_id: int) -> str:
    """Return the full details of a single task by its numeric ID."""
    logger.debug("get_task_by_id called with task_id=%r", task_id)
    df = _df()
    row = df[df["id"] == task_id]
    if row.empty:
        logger.warning("get_task_by_id(task_id=%r) -> not found", task_id)
        return json.dumps({"error": f"Task with id {task_id} not found."})
    logger.info("get_task_by_id(task_id=%r) -> found", task_id)
    return row.iloc[0].to_json(force_ascii=False)


@tool
def get_tasks_by_priority(priority: str, status: str = "") -> str:
    """
    Return tasks matching the given priority, optionally filtered by status.
    priority: 'Low', 'Medium', 'High', 'Critical'
    status:   'Open', 'In Progress', 'Review', 'Done' — or '' for all
    """
    logger.debug("get_tasks_by_priority called with priority=%r, status=%r", priority, status)
    df = _df()
    df = df[df["priority"] == priority]
    if status:
        df = df[df["status"] == status]
    logger.info(
        "get_tasks_by_priority(priority=%r, status=%r) -> %d rows", priority, status, len(df)
    )
    cols = ["id", "title", "status", "priority", "assignee_name", "due_time"]
    return df[cols].to_json(orient="records", force_ascii=False)


# Operational (mutations)
@tool
def update_task_status(task_id: int, new_status: str) -> str:
    """
    Update the status of an existing task.
    Valid statuses: 'Open', 'In Progress', 'Review', 'Done'
    """
    logger.debug("update_task_status called with task_id=%r, new_status=%r", task_id, new_status)
    ok = update_task(task_id, "status", new_status)
    if ok:
        logger.info("update_task_status(task_id=%r) -> updated to %r", task_id, new_status)
        return f"Task {task_id} status successfully updated to '{new_status}'."
    logger.warning("update_task_status(task_id=%r) -> not found", task_id)
    return f"Error: task with id {task_id} not found."


@tool
def create_new_task(
    title: str,
    description: str,
    assignee_name: str,
    priority: str = "Medium",
    due_time: str = "",
) -> str:
    """
    Create a new task assigned to a person by fullname (partial match OK).
    priority: 'Low', 'Medium', 'High', 'Critical'
    due_time: YYYY/MM/DD format, or empty string if not specified.
    """
    logger.debug(
        "create_new_task called with title=%r, assignee_name=%r, priority=%r",
        title,
        assignee_name,
        priority,
    )
    users = get_users()
    matched = users[users["fullname"].str.contains(assignee_name, na=False)]
    if matched.empty:
        logger.warning("create_new_task: no user found matching %r", assignee_name)
        return f"Error: no user found matching '{assignee_name}'."

    user = matched.iloc[0]
    task = create_task(
        title=title,
        description=description,
        assignee_id=int(user["id"]),
        priority=priority,
        due_time=due_time or None,
    )
    logger.info("create_new_task -> created task id=%r for user %r", task["id"], user["fullname"])
    return json.dumps(task, ensure_ascii=False)


# Registry
ALL_TOOLS = [
    count_tasks_by_status,
    count_tasks_by_priority,
    count_tasks_closed_in_last_n_days,
    count_overdue_tasks,
    average_close_time_days,
    tasks_per_person,
    tasks_per_department,
    get_tasks_for_person,
    get_tasks_for_department,
    get_tasks_by_status_and_department,
    get_task_by_id,
    get_tasks_by_priority,
    update_task_status,
    create_new_task,
]

