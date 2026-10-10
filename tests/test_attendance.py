from conftest import login


def _scan(mod, monkeypatch, present_ids):
    def fake():
        c = mod.get_db()
        ids = [r[0] for r in c.execute("SELECT id FROM students")]
        c.close()
        return {i: (i in present_ids) for i in ids}
    monkeypatch.setattr(mod, "scan_faces", fake)


def _rows(mod):
    c = mod.get_db()
    r = c.execute("SELECT student_id, status, marked_by FROM attendance ORDER BY student_id").fetchall()
    c.close()
    return [tuple(x) for x in r]


def test_scan_does_not_write_to_db(with_students, mod, monkeypatch):
    _scan(mod, monkeypatch, {1})
    with_students.post("/attendance")
    assert _rows(mod) == []


def test_review_shows_checklist(with_students, mod, monkeypatch):
    _scan(mod, monkeypatch, {1})
    with_students.post("/attendance")
    html = with_students.get("/attendance/review").data.decode().split("<table")[1]
    assert "Asha Rao" in html
    assert "Bala K" not in html and "Chitra S" not in html  # only recognised students


def test_review_without_scan_redirects(admin):
    assert b"Nothing to review" in admin.get("/attendance/review", follow_redirects=True).data


def test_save_unchanged_marks_auto(with_students, mod, monkeypatch):
    _scan(mod, monkeypatch, {1})
    with_students.post("/attendance")
    with_students.post("/attendance/save", data={"present_1": "on"})
    assert _rows(mod) == [(1, "Present", "auto")]


def test_override_records_faculty_username(with_students, mod, monkeypatch):
    _scan(mod, monkeypatch, {1})
    with_students.post("/attendance")
    r = with_students.post("/attendance/save", data={}, follow_redirects=True)  # untick the recognised student
    assert _rows(mod) == [(1, "Absent", "boss")]
    assert b"manually corrected" in r.data


def test_resave_same_day_updates_not_duplicates(with_students, mod, monkeypatch):
    _scan(mod, monkeypatch, {1})
    with_students.post("/attendance")
    with_students.post("/attendance/save", data={"present_1": "on"})
    _scan(mod, monkeypatch, {1, 2})
    with_students.post("/attendance")
    with_students.post("/attendance/save", data={"present_1": "on", "present_2": "on"})
    rows = _rows(mod)
    assert len(rows) == 2 and rows[1] == (2, "Present", "auto")


def test_scan_error_is_flashed(with_students, mod, monkeypatch):
    def boom():
        raise RuntimeError("No trained model yet")
    monkeypatch.setattr(mod, "scan_faces", boom)
    assert b"No trained model" in with_students.post("/attendance", follow_redirects=True).data


def test_student_cannot_take_attendance(with_students, mod):
    with_students.get("/logout")
    login(with_students, "PES1", "PES1")
    assert with_students.post("/attendance").status_code in (302, 403)
    assert with_students.post("/attendance/save", data={}).status_code in (302, 403)


def test_absent_rows_are_not_counted_or_listed_as_present(with_students, mod, monkeypatch):
    """Regression: an unticked (Absent) row must not appear in 'Marked present today',
    the home counter or the dashboard numerator."""
    _scan(mod, monkeypatch, {1, 2})
    with_students.post("/attendance")
    with_students.post("/attendance/save", data={"present_1": "on"})  # student 2 unticked -> Absent
    page = with_students.get("/attendance").data.decode().split("<table")[1]
    assert "Asha Rao" in page and "Bala K" not in page
    dash = with_students.get("/dashboard").data.decode()
    assert "1 / 1" in dash and "0 / 1" in dash


def test_nobody_recognised_goes_back_with_message(with_students, mod, monkeypatch):
    _scan(mod, monkeypatch, set())
    r = with_students.post("/attendance", follow_redirects=True)
    assert b"No enrolled student was recognised" in r.data
    assert with_students.get("/attendance/review").status_code == 302  # nothing pending
