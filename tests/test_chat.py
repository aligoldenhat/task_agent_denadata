import uuid
from unittest.mock import patch

import pytest
import httpx
from asgi_lifespan import LifespanManager

from src.main import app


@pytest.fixture
async def client():
    with (
        patch("src.graph.utils.tools.update_task", return_value=True),
        patch(
            "src.graph.utils.tools.create_task",
            return_value={
                "id": 151,
                "title": "new test task",
                "assignee_name": "علی صابری",
                "status": "Open",
                "priority": "Medium",
                "due_time": "",
                "description": "test",
            },
        ),
        patch("src.config.settings.DB_PATH", ":memory:"),
    ):
        async with LifespanManager(app) as manager:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=manager.app),
                base_url="http://test",
            ) as ac:
                yield ac


def _conv() -> str:
    return str(uuid.uuid4())


async def ask(client: httpx.AsyncClient, message: str, conv_id: str) -> str:
    response = await client.post(
        "/chat",
        json={"message": message, "conversation_id": conv_id},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["conversation_id"] == conv_id
    return data["answer"]


# Statistical
async def test_total_task_count(client):
    answer = await ask(client, "چند تسک داریم؟", _conv())
    assert any(n in answer for n in ["150", "۱۵۰"])


async def test_open_tasks(client):
    # Open(27) + In Progress(25) + Review(21) = 73 non-Done tasks
    answer = await ask(client, "چند تسک باز داریم؟", _conv())
    assert any(n in answer for n in ["27", "۲۷"])


async def test_done_tasks(client):
    answer = await ask(client, "چند تسک بسته شده؟", _conv())
    assert any(n in answer for n in ["77", "۷۷"])


async def test_closed_in_last_month(client):
    answer = await ask(client, "چند تسک طی یک ماه اخیر بسته شده؟", _conv())
    assert any(ch.isdigit() for ch in answer)


async def test_high_priority_count(client):
    answer = await ask(client, "چند تسک با اولویت بالا داریم؟", _conv())
    assert any(n in answer for n in ["49", "۴۹"])


# Analytical
async def test_person_with_most_tasks(client):
    # assignee_ids 1-50 cycle, so everyone gets 3 tasks — agent should return a name
    answer = await ask(client, "بیشترین تعداد تسک متعلق به چه شخصی است؟", _conv())
    assert len(answer) > 0


async def test_department_with_most_tasks(client):
    # فنی has the most users (14) so likely the most tasks
    answer = await ask(client, "کدام دپارتمان بیشترین تسک را دارد؟", _conv())
    assert "فنی" in answer


async def test_average_close_time(client):
    answer = await ask(client, "میانگین زمان بسته شدن تسک‌ها چقدر است؟", _conv())
    assert any(ch.isdigit() for ch in answer)


async def test_overdue_tasks(client):
    answer = await ask(client, "چند تسک معوق داریم؟", _conv())
    assert any(ch.isdigit() for ch in answer)


# Search
async def test_tasks_for_ali_saberi(client):
    # علی صابری is assignee_id=1, has tasks: 1, 51, 101
    answer = await ask(client, "تسک‌های مربوط به علی صابری را نشان بده", _conv())
    assert any(
        t in answer
        for t in ["رفع باگ ورود کاربران", "پیاده سازی لاگ متمرکز", "پیاده سازی سیستم Audit Log"]
    )


async def test_open_tasks_for_support_dept(client):
    # پشتیبانی dept has some Open/In Progress tasks
    answer = await ask(client, "تسک‌های باز دپارتمان پشتیبانی را نشان بده", _conv())
    assert len(answer) > 0


async def test_high_priority_tasks(client):
    answer = await ask(client, "تسک‌های با اولویت بالا را نشان بده", _conv())
    assert len(answer) > 0


# Operational
async def test_create_task_for_ali_saberi(client):
    answer = await ask(client, "برای علی صابری یک تسک ایجاد کن", _conv())
    assert len(answer) > 0


async def test_update_task_120_to_done(client):
    # task 120 exists in the real CSV (کنترل مغایرت حساب‌ها, already Done)
    answer = await ask(client, "وضعیت تسک ۱۲۰ را به Done تغییر بده", _conv())
    assert "120" in answer or "Done" in answer or "تغییر" in answer


# Memory (multi-turn)
async def test_conversation_memory(client):
    """
    Turn 1: ask about Ali Saberi's tasks.
    Turn 2: follow-up — agent must remember the context from turn 1.
    """
    conv_id = _conv()
    await ask(client, "تسک‌های علی صابری را نشان بده", conv_id)
    answer = await ask(client, "فقط باز ها را بگو", conv_id)
    # علی صابری has In Progress and Open tasks — agent should list them
    # or at minimum reference the previous context without asking who
    assert any(
        t in answer
        for t in [
            "پیاده سازی لاگ متمرکز",  # In Progress
            "پیاده سازی سیستم Audit Log",  # Open
            "باز",
            "In Progress",
            "Open",
        ]
    )
