from app.timetable_parser import parse_timetable_html

SAMPLE_TIMETABLE_HTML = """
<!DOCTYPE html>
<html>
<body>
<table>
  <thead>
    <tr>
      <th>Time</th>
      <th>Monday</th>
      <th>Tuesday</th>
      <th>Wednesday</th>
      <th>Thursday</th>
      <th>Friday</th>
      <th>Saturday</th>
      <th>Sunday</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>8.00am-9.00am</td>
      <td rowspan="2">CS101<br />Intro to CS<br />Prof A<br />Room 1<br />(Week 1-2)</td>
      <td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td>
    </tr>
    <tr>
      <td>9.00am-10.00am</td>
      <td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td>
    </tr>
    <tr>
      <td>10.00am-11.00am</td>
      <td>&nbsp;</td><td>&nbsp;</td>
      <td>MA101<br />Calculus<br />Prof B<br />Room 2<br />(Week 3-4)</td>
      <td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td>
    </tr>
    <tr>
      <td>11.00am-12.00pm</td>
      <td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td>
    </tr>
  </tbody>
</table>
</body>
</html>
"""


def test_parse_reference_format():
    parsed = parse_timetable_html(SAMPLE_TIMETABLE_HTML.encode())
    assert parsed.warnings == []
    assert len(parsed.sessions) == 2

    first = parsed.sessions[0]
    assert first.weekday == 1
    assert (first.start_time.hour, first.start_time.minute) == (8, 0)
    assert (first.end_time.hour, first.end_time.minute) == (10, 0)
    assert first.course_code == "CS101"
    assert first.course_name == "Intro to CS"
    assert first.teacher == "Prof A"
    assert first.location == "Room 1"
    assert (first.week_start, first.week_end) == (1, 2)

    second = parsed.sessions[1]
    assert second.weekday == 3
    assert (second.week_start, second.week_end) == (3, 4)


def _import_sample(client, *, name="2026 Fall", active=True):
    return client.post(
        "/api/v1/timetables/import",
        files={
            "file": (
                "202609 Semester Timetable.html",
                SAMPLE_TIMETABLE_HTML.encode(),
                "text/html",
            )
        },
        data={
            "name": name,
            "semester_start_date": "2026-09-07",
            "set_active": str(active).lower(),
        },
    )


def test_timetable_import_dashboard_and_activation(client):
    imported = _import_sample(client)
    assert imported.status_code == 201
    body = imported.json()
    assert body["warnings"] == []
    timetable = body["timetable"]
    assert timetable["name"] == "2026 Fall"
    assert timetable["active"] is True
    assert timetable["session_count"] == 2
    assert len(timetable["sessions"]) == 2

    listed = client.get("/api/v1/timetables").json()
    assert len(listed) == 1
    assert listed[0]["session_count"] == 2

    active = client.get("/api/v1/timetables/active")
    assert active.status_code == 200
    assert active.json()["id"] == timetable["id"]

    week_one = client.get("/api/v1/timetables/dashboard", params={"date": "2026-09-09"})
    assert week_one.status_code == 200
    dashboard = week_one.json()
    assert dashboard["current_week"] == 1
    assert dashboard["week_start_date"] == "2026-09-07"
    assert dashboard["week_end_date"] == "2026-09-13"
    assert len(dashboard["days"]) == 7
    assert len(dashboard["days"][0]["courses"]) == 1
    assert dashboard["days"][0]["courses"][0]["course_code"] == "CS101"
    assert dashboard["days"][2]["courses"] == []

    week_three = client.get(
        "/api/v1/timetables/dashboard", params={"date": "2026-09-23"}
    ).json()
    assert week_three["current_week"] == 3
    assert week_three["days"][0]["courses"] == []
    assert len(week_three["days"][2]["courses"]) == 1
    assert week_three["days"][2]["courses"][0]["course_code"] == "MA101"

    second = _import_sample(client, name="Backup", active=False)
    assert second.status_code == 201
    second_id = second.json()["timetable"]["id"]
    assert second.json()["timetable"]["active"] is False
    assert client.get("/api/v1/timetables/active").json()["id"] == timetable["id"]

    activated = client.post(f"/api/v1/timetables/{second_id}/activate")
    assert activated.status_code == 200
    assert activated.json()["active"] is True
    assert client.get("/api/v1/timetables/active").json()["id"] == second_id

    renamed = client.patch(
        f"/api/v1/timetables/{second_id}",
        json={"name": "Current Semester", "semester_start_date": None},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Current Semester"
    assert renamed.json()["semester_start_date"] is None

    no_week = client.get(
        "/api/v1/timetables/dashboard", params={"date": "2027-01-06"}
    ).json()
    assert no_week["current_week"] is None
    assert len(no_week["days"][0]["courses"]) == 1

    assert client.delete(f"/api/v1/timetables/{second_id}").status_code == 204
    assert client.get("/api/v1/timetables/active").status_code == 404


def test_timetable_import_validation(client):
    unsupported = client.post(
        "/api/v1/timetables/import",
        files={"file": ("timetable.txt", b"hello", "text/plain")},
    )
    assert unsupported.status_code == 422

    invalid_html = client.post(
        "/api/v1/timetables/import",
        files={
            "file": ("timetable.html", b"<html><body>empty</body></html>", "text/html")
        },
    )
    assert invalid_html.status_code == 422

    empty = client.post(
        "/api/v1/timetables/import",
        files={"file": ("timetable.html", b"", "text/html")},
    )
    assert empty.status_code == 422

    assert client.get("/api/v1/timetables/dashboard").status_code == 404
    assert client.get("/api/v1/timetables/active").status_code == 404
