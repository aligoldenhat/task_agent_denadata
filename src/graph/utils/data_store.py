from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import settings


# Load & join
def _load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    tasks = pd.read_csv(settings.TASK_CSV)
    users = pd.read_csv(settings.USERS_CSV)
    tasks.columns = tasks.columns.str.strip()
    users.columns = users.columns.str.strip()

    merged = tasks.merge(
        users.rename(
            columns={
                "id": "assignee_id",
                "fullname": "assignee_name",
                "department": "assignee_dept",
            }
        ),
        on="assignee_id",
        how="left",
    )
    return tasks, users, merged


_tasks_df, _users_df, _merged_df = _load()

# Runtime mutation store
# Keyed by str(task_id) for updates, "new_{id}" for created tasks.
_SIDECAR = Path("runtime_mutations.json")


def _load_runtime() -> dict[str, Any]:
    if _SIDECAR.exists():
        try:
            return json.loads(_SIDECAR.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


_runtime: dict[str, Any] = _load_runtime()


def _persist() -> None:
    _SIDECAR.write_text(
        json.dumps(_runtime, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# Public read helpers
def get_tasks() -> pd.DataFrame:
    """
    Merged tasks+users DataFrame with any runtime patches applied.
    Newly created tasks are appended at the bottom.
    """
    df = _merged_df.copy()

    # apply field-level updates
    for key, val in _runtime.items():
        if key.startswith("new_"):
            continue
        mask = df["id"] == int(key)
        for col, v in val.items():
            df.loc[mask, col] = v

    # append newly created tasks
    new_rows = [v for k, v in _runtime.items() if k.startswith("new_") and isinstance(v, dict)]
    if new_rows:
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)

    return df


def get_users() -> pd.DataFrame:
    return _users_df.copy()


# Public write helpers
def update_task(task_id: int, field: str, value: str) -> bool:
    """Update a single field on an existing task. Returns False if not found."""
    if task_id not in _merged_df["id"].values:
        return False
    _runtime.setdefault(str(task_id), {})[field] = value
    _persist()
    return True


def create_task(
    title: str,
    description: str,
    assignee_id: int,
    priority: str = "Medium",
    status: str = "Open",
    due_time: str | None = None,
) -> dict[str, Any]:
    """Append a new task; returns the created task dict."""
    df = get_tasks()
    new_id = int(df["id"].max()) + 1

    user_row = _users_df[_users_df["id"] == assignee_id]
    assignee_name = user_row["fullname"].iloc[0] if not user_row.empty else "unknown"
    assignee_dept = user_row["department"].iloc[0] if not user_row.empty else "unknown"

    task: dict[str, Any] = {
        "id": new_id,
        "title": title,
        "description": description,
        "create_time": datetime.now().strftime("%Y/%m/%d"),
        "status": status,
        "assignee_id": assignee_id,
        "priority": priority,
        "due_time": due_time or "",
        "assignee_name": assignee_name,
        "assignee_dept": assignee_dept,
    }
    _runtime[f"new_{new_id}"] = task
    _persist()
    return task
