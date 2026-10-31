from datetime import datetime


def test_health_and_root(client):
    assert client.get("/health").json() == {"status": "ok"}
    root = client.get("/").json()
    assert root["docs"] == "/docs"
    assert root["openapi"] == "/openapi.json"


def test_todo_lifecycle_and_filters(client):
    created = client.post(
        "/api/v1/todos",
        json={
            "title": "  写周报  ",
            "description": "总结本周进度",
            "priority": "high",
            "due_at": "2020-01-01T00:00:00+08:00",
        },
    )
    assert created.status_code == 201
    todo = created.json()
    assert todo["title"] == "写周报"
    assert todo["status"] == "pending"
    assert todo["is_overdue"] is True
    assert datetime.fromisoformat(todo["due_at"]).utcoffset().total_seconds() == 0

    other = client.post(
        "/api/v1/todos",
        json={"title": "买牛奶", "priority": "low", "status": "pending"},
    )
    assert other.status_code == 201

    filtered = client.get(
        "/api/v1/todos",
        params=[("priority", "high"), ("priority", "medium")],
    ).json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["title"] == "写周报"

    searched = client.get("/api/v1/todos", params={"search": "牛奶"}).json()
    assert searched["total"] == 1
    assert searched["items"][0]["title"] == "买牛奶"

    updated = client.patch(f"/api/v1/todos/{todo['id']}", json={"status": "completed"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "completed"
    assert updated.json()["completed_at"] is not None
    assert updated.json()["is_overdue"] is False

    reopened = client.patch(
        f"/api/v1/todos/{todo['id']}", json={"status": "pending", "due_at": None}
    )
    assert reopened.status_code == 200
    assert reopened.json()["completed_at"] is None
    assert reopened.json()["due_at"] is None

    assert (
        client.patch(f"/api/v1/todos/{todo['id']}", json={"title": " "}).status_code
        == 422
    )
    assert (
        client.patch(f"/api/v1/todos/{todo['id']}", json={"status": None}).status_code
        == 422
    )

    deleted = client.delete(f"/api/v1/todos/{todo['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/todos/{todo['id']}").status_code == 404


def test_ledger_summary_and_filters(client):
    transactions = [
        {
            "type": "income",
            "amount_cents": 100_000,
            "category": "工资",
            "occurred_at": "2026-08-01T10:00:00+08:00",
        },
        {
            "type": "expense",
            "amount_cents": 2_500,
            "category": "餐饮",
            "note": "午饭",
            "occurred_at": "2026-08-02T12:00:00+08:00",
        },
        {
            "type": "expense",
            "amount_cents": 1_500,
            "category": "交通",
            "occurred_at": "2026-08-03T09:00:00+08:00",
        },
    ]
    for payload in transactions:
        response = client.post("/api/v1/ledger/transactions", json=payload)
        assert response.status_code == 201
        assert response.json()["occurred_at"].endswith(("Z", "+00:00"))

    summary = client.get("/api/v1/ledger/summary", params={"group_by": "category"})
    assert summary.status_code == 200
    body = summary.json()
    assert body["income_cents"] == 100_000
    assert body["expense_cents"] == 4_000
    assert body["balance_cents"] == 96_000
    assert body["transaction_count"] == 3
    assert {group["key"] for group in body["groups"]} == {"工资", "餐饮", "交通"}

    daily = client.get(
        "/api/v1/ledger/transactions",
        params={
            "start_at": "2026-08-02T00:00:00+08:00",
            "end_at": "2026-08-03T00:00:00+08:00",
        },
    ).json()
    assert daily["total"] == 1
    assert daily["items"][0]["category"] == "餐饮"

    expenses = client.get(
        "/api/v1/ledger/transactions", params={"type": "expense"}
    ).json()
    assert expenses["total"] == 2

    search = client.get("/api/v1/ledger/summary", params={"search": "午饭"}).json()
    assert search["expense_cents"] == 2_500

    assert (
        client.post(
            "/api/v1/ledger/transactions",
            json={"type": "expense", "amount_cents": 0, "category": "测试"},
        ).status_code
        == 422
    )


def test_schedule_overlap_and_validation(client):
    first = client.post(
        "/api/v1/schedules",
        json={
            "title": "评审",
            "start_at": "2026-09-01T10:00:00+08:00",
            "end_at": "2026-09-01T11:00:00+08:00",
        },
    )
    assert first.status_code == 201
    assert first.json()["start_at"].endswith(("Z", "+00:00"))

    second = client.post(
        "/api/v1/schedules",
        json={
            "title": "午餐",
            "start_at": "2026-09-01T12:00:00+08:00",
            "end_at": "2026-09-01T13:00:00+08:00",
        },
    )
    overlapping = client.post(
        "/api/v1/schedules",
        json={
            "title": "电话",
            "start_at": "2026-09-01T10:30:00+08:00",
            "end_at": "2026-09-01T10:45:00+08:00",
        },
    )
    assert second.status_code == 201
    assert overlapping.status_code == 201

    window = client.get(
        "/api/v1/schedules",
        params={
            "range_start": "2026-09-01T10:15:00+08:00",
            "range_end": "2026-09-01T11:30:00+08:00",
        },
    ).json()
    assert window["total"] == 2
    assert {item["title"] for item in window["items"]} == {"评审", "电话"}

    invalid_create = client.post(
        "/api/v1/schedules",
        json={
            "title": "错误日程",
            "start_at": "2026-09-01T11:00:00+08:00",
            "end_at": "2026-09-01T10:00:00+08:00",
        },
    )
    assert invalid_create.status_code == 422

    invalid_update = client.patch(
        f"/api/v1/schedules/{first.json()['id']}",
        json={"end_at": "2026-09-01T09:00:00+08:00"},
    )
    assert invalid_update.status_code == 422


def test_diary_unique_date_search_and_update(client):
    first = client.post(
        "/api/v1/diary/entries",
        json={
            "entry_date": "2026-10-01",
            "title": "假期第一天",
            "content": "去公园散步。",
            "mood": "good",
            "weather": "晴",
        },
    )
    assert first.status_code == 201
    entry = first.json()

    duplicate = client.post(
        "/api/v1/diary/entries",
        json={"entry_date": "2026-10-01", "content": "重复条目"},
    )
    assert duplicate.status_code == 409

    by_date = client.get("/api/v1/diary/entries/by-date/2026-10-01")
    assert by_date.status_code == 200
    assert by_date.json()["id"] == entry["id"]

    searched = client.get("/api/v1/diary/entries", params={"search": "公园"}).json()
    assert searched["total"] == 1

    second = client.post(
        "/api/v1/diary/entries",
        json={"entry_date": "2026-10-02", "content": "在家读书。"},
    )
    assert second.status_code == 201

    conflict = client.patch(
        f"/api/v1/diary/entries/{second.json()['id']}",
        json={"entry_date": "2026-10-01"},
    )
    assert conflict.status_code == 409

    mood_filter = client.get("/api/v1/diary/entries", params={"mood": "good"}).json()
    assert mood_filter["total"] == 1

    assert client.delete(f"/api/v1/diary/entries/{entry['id']}").status_code == 204
    assert client.get("/api/v1/diary/entries/by-date/2026-10-01").status_code == 404
