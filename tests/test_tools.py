import json
from unittest.mock import patch

import pandas as pd
import pytest

from src.config import settings

_tasks = pd.read_csv(settings.TASK_CSV)
_users = pd.read_csv(settings.USERS_CSV)
_merged = _tasks.merge(
    _users.rename(
        columns={"id": "assignee_id", "fullname": "assignee_name", "department": "assignee_dept"}
    ),
    on="assignee_id",
    how="left",
)

TOTAL = len(_tasks)
DONE_COUNT = int((_tasks["status"] == "Done").sum())
HIGH_COUNT = int((_tasks["priority"] == "High").sum())
CRITICAL_COUNT = int((_tasks["priority"] == "Critical").sum())
TOP_DEPT = _merged.groupby("assignee_dept")["id"].count().idxmax()
TOP_PERSON = _merged.groupby("assignee_name")["id"].count().idxmax()


# Fixture


@pytest.fixture(autouse=True)
def patch_data():
    """All tool tests use the real CSV data but block any writes."""
    with (
        patch("src.graph.utils.tools.update_task", return_value=True),
        patch(
            "src.graph.utils.tools.create_task",
            return_value={
                "id": TOTAL + 1,
                "title": "test task",
                "assignee_name": "علی صابری",
                "status": "Open",
                "priority": "Medium",
                "due_time": "",
            },
        ),
    ):
        yield


# statistical


def test_count_all_statuses():
    from src.graph.utils.tools import count_tasks_by_status

    result = json.loads(count_tasks_by_status.invoke({"status": "all"}))
    assert isinstance(result, dict)
    assert sum(result.values()) == TOTAL


def test_count_done():
    from src.graph.utils.tools import count_tasks_by_status

    assert count_tasks_by_status.invoke({"status": "Done"}) == str(DONE_COUNT)


def test_count_in_progress():
    from src.graph.utils.tools import count_tasks_by_status

    expected = int((_tasks["status"] == "In Progress").sum())
    assert count_tasks_by_status.invoke({"status": "In Progress"}) == str(expected)


def test_count_high_priority():
    from src.graph.utils.tools import count_tasks_by_priority

    assert count_tasks_by_priority.invoke({"priority": "High"}) == str(HIGH_COUNT)


def test_count_critical_priority():
    from src.graph.utils.tools import count_tasks_by_priority

    assert count_tasks_by_priority.invoke({"priority": "Critical"}) == str(CRITICAL_COUNT)


def test_count_all_priorities():
    from src.graph.utils.tools import count_tasks_by_priority

    result = json.loads(count_tasks_by_priority.invoke({"priority": "all"}))
    assert sum(result.values()) == TOTAL


def test_count_overdue_returns_number():
    from src.graph.utils.tools import count_overdue_tasks

    result = count_overdue_tasks.invoke({})
    assert result.isdigit()


def test_average_close_time_is_numeric():
    from src.graph.utils.tools import average_close_time_days

    result = average_close_time_days.invoke({})
    assert float(result) >= 0


def test_closed_in_last_30_days_returns_number():
    from src.graph.utils.tools import count_tasks_closed_in_last_n_days

    result = count_tasks_closed_in_last_n_days.invoke({"days": 30})
    assert result.isdigit()


# analytaical


def test_tasks_per_department_top():
    from src.graph.utils.tools import tasks_per_department

    result = json.loads(tasks_per_department.invoke({}))
    assert isinstance(result, dict)
    assert list(result.keys())[0] == TOP_DEPT


def test_tasks_per_department_sum():
    from src.graph.utils.tools import tasks_per_department

    result = json.loads(tasks_per_department.invoke({}))
    assert sum(result.values()) == TOTAL


def test_tasks_per_person_top():
    from src.graph.utils.tools import tasks_per_person

    result = json.loads(tasks_per_person.invoke({}))
    assert isinstance(result, dict)
    assert list(result.keys())[0] == TOP_PERSON


def test_tasks_per_person_sum():
    from src.graph.utils.tools import tasks_per_person

    result = json.loads(tasks_per_person.invoke({}))
    assert sum(result.values()) == TOTAL


# search


def test_get_tasks_for_ali_saberi():
    from src.graph.utils.tools import get_tasks_for_person

    result = json.loads(get_tasks_for_person.invoke({"name": "علی صابری"}))
    assert len(result) > 0
    assert all(r["assignee_name"] == "علی صابری" for r in result)


def test_get_tasks_for_person_partial_match():
    from src.graph.utils.tools import get_tasks_for_person

    result = json.loads(get_tasks_for_person.invoke({"name": "صابری"}))
    assert len(result) > 0


def test_get_tasks_for_person_not_found():
    from src.graph.utils.tools import get_tasks_for_person

    result = json.loads(get_tasks_for_person.invoke({"name": "nobody_xyz"}))
    assert result == []


def test_get_tasks_for_department_fanni():
    from src.graph.utils.tools import get_tasks_for_department

    result = json.loads(get_tasks_for_department.invoke({"department": "فنی"}))
    assert len(result) > 0
    assert all(r["assignee_name"] != "" for r in result)


def test_get_tasks_for_department_not_found():
    from src.graph.utils.tools import get_tasks_for_department

    result = json.loads(get_tasks_for_department.invoke({"department": "nonexistent_dept"}))
    assert result == []


def test_get_task_by_id_exists():
    from src.graph.utils.tools import get_task_by_id

    result = json.loads(get_task_by_id.invoke({"task_id": 1}))
    assert result["id"] == 1
    assert "title" in result


def test_get_task_by_id_not_found():
    from src.graph.utils.tools import get_task_by_id

    result = json.loads(get_task_by_id.invoke({"task_id": 99999}))
    assert "error" in result


def test_get_tasks_by_priority_high():
    from src.graph.utils.tools import get_tasks_by_priority

    result = json.loads(get_tasks_by_priority.invoke({"priority": "High"}))
    assert len(result) == HIGH_COUNT
    assert all(r["priority"] == "High" for r in result)


def test_get_tasks_by_priority_with_status_filter():
    from src.graph.utils.tools import get_tasks_by_priority

    result = json.loads(get_tasks_by_priority.invoke({"priority": "High", "status": "Done"}))
    assert all(r["priority"] == "High" for r in result)
    assert all(r["status"] == "Done" for r in result)


def test_get_tasks_by_status_and_department_both_filters():
    from src.graph.utils.tools import get_tasks_by_status_and_department

    result = json.loads(
        get_tasks_by_status_and_department.invoke({"status": "Done", "department": "فنی"})
    )
    assert all(r["status"] == "Done" for r in result)


def test_get_tasks_by_status_and_department_status_only():
    from src.graph.utils.tools import get_tasks_by_status_and_department

    result = json.loads(
        get_tasks_by_status_and_department.invoke({"status": "Done", "department": ""})
    )
    assert len(result) == DONE_COUNT


def test_get_tasks_by_status_and_department_no_filter():
    from src.graph.utils.tools import get_tasks_by_status_and_department

    result = json.loads(get_tasks_by_status_and_department.invoke({"status": "", "department": ""}))
    assert len(result) == TOTAL


# operational
def test_update_task_status_success():
    from src.graph.utils.tools import update_task_status

    with patch("src.graph.utils.tools.update_task", return_value=True) as mock:
        result = update_task_status.invoke({"task_id": 1, "new_status": "Done"})
        mock.assert_called_once_with(1, "status", "Done")
        assert "1" in result
        assert "Done" in result


def test_update_task_status_not_found():
    from src.graph.utils.tools import update_task_status

    with patch("src.graph.utils.tools.update_task", return_value=False):
        result = update_task_status.invoke({"task_id": 99999, "new_status": "Done"})
        assert "99999" in result
        assert "Error" in result


def test_create_new_task_success():
    from src.graph.utils.tools import create_new_task

    result = json.loads(
        create_new_task.invoke(
            {
                "title": "test task",
                "description": "test description",
                "assignee_name": "علی صابری",
                "priority": "High",
                "due_time": "2026/08/01",
            }
        )
    )
    assert result["assignee_name"] == "علی صابری"
    assert result["id"] == TOTAL + 1


def test_create_new_task_user_not_found():
    from src.graph.utils.tools import create_new_task

    result = create_new_task.invoke(
        {
            "title": "test",
            "description": "test",
            "assignee_name": "nobody_xyz",
            "priority": "Medium",
        }
    )
    assert "Error" in result
    assert "nobody_xyz" in result
