import csv
import io

from conftest import login


def _mark(mod, sid, day, status="Present"):
    c = mod.get_db()
    c.execute("INSERT INTO attendance (student_id, att_date, att_time, status, marked_by) "
              "VALUES (?, ?, '10:00:00', ?, 'auto')", (sid, day, status))
    c.commit()
    c.close()


def test_percentage_and_low_flag(with_students, mod):
    # 4 sessions; student 1 present 4/4, student 2 present 2/4 (50%)
    for d in ("2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04"):
        _mark(mod, 1, d)
    _mark(mod, 2, "2026-10-01")
    _mark(mod, 2, "2026-10-02")
    html = with_students.get("/dashboard").data.decode()
    assert "100" in html and "50" in html


def test_rounding(with_students, mod):
    for d in ("2026-10-01", "2026-10-02", "2026-10-03"):
        _mark(mod, 3, d)
    _mark(mod, 1, "2026-10-01")  # 1/3 = 33%
    assert "33" in with_students.get("/dashboard").data.decode()


def test_dashboard_empty_has_zero_sessions(admin):
    assert admin.get("/dashboard").status_code == 200


def test_student_sees_only_own_record(with_students, mod):
    _mark(mod, 1, "2026-10-01")
    with_students.get("/logout")
    login(with_students, "PES1", "PES1")
    html = with_students.get("/dashboard").data.decode()
    assert "Asha Rao" in html and "Bala K" not in html and "Chitra S" not in html


def test_student_cannot_export(with_students):
    with_students.get("/logout")
    login(with_students, "PES1", "PES1")
    assert with_students.get("/export").status_code in (302, 403)


def test_csv_export(with_students, mod):
    _mark(mod, 1, "2026-10-01")
    r = with_students.get("/export")
    assert r.mimetype == "text/csv"
    assert "attendance_report.csv" in r.headers["Content-Disposition"]
    rows = list(csv.reader(io.StringIO(r.data.decode())))
    assert rows[0] == ["Name", "Roll No", "Date", "Time", "Status", "Marked By"]
    assert rows[1][:2] == ["Asha Rao", "PES1"] and rows[1][4] == "Present"


def test_csv_export_empty_has_header_only(admin):
    rows = list(csv.reader(io.StringIO(admin.get("/export").data.decode())))
    assert len(rows) == 1
