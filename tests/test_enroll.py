from conftest import login


def test_enroll_creates_student_and_login(admin, mod):
    r = admin.post("/enroll", data={"name": "Asha Rao", "roll_no": "PES1"}, follow_redirects=True)
    assert b"Enrolled Asha Rao" in r.data
    c = mod.get_db()
    assert c.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 1
    assert c.execute("SELECT role FROM users WHERE username='PES1'").fetchone()[0] == "Student"


def test_duplicate_roll_rejected(admin, mod):
    admin.post("/enroll", data={"name": "Asha", "roll_no": "PES1"})
    r = admin.post("/enroll", data={"name": "Other", "roll_no": "PES1"}, follow_redirects=True)
    assert b"already" in r.data
    assert mod.get_db().execute("SELECT COUNT(*) FROM students").fetchone()[0] == 1


def test_roll_colliding_with_staff_username_rejected(admin):
    r = admin.post("/enroll", data={"name": "X", "roll_no": "boss"}, follow_redirects=True)
    assert b"Admin/Faculty username" in r.data


def test_zero_samples_reports_error(admin, mod, monkeypatch):
    monkeypatch.setattr(mod, "capture_face_samples", lambda s, n: 0)
    r = admin.post("/enroll", data={"name": "Asha", "roll_no": "PES1"}, follow_redirects=True)
    assert b"No face captured" in r.data


def test_missing_webcam_error_is_shown(admin, mod, monkeypatch):
    def boom(s, n):
        raise RuntimeError("Could not access the webcam.")
    monkeypatch.setattr(mod, "capture_face_samples", boom)
    r = admin.post("/enroll", data={"name": "Asha", "roll_no": "PES1"}, follow_redirects=True)
    assert b"Could not access the webcam" in r.data


def test_reenroll_adds_samples_and_retrains(with_students, mod, monkeypatch):
    calls = []
    monkeypatch.setattr(mod, "train_model", lambda: calls.append(1) or True)
    r = with_students.post("/enroll/1/more", follow_redirects=True)
    assert b"Added 30 more samples for Asha Rao" in r.data and calls
    assert mod.get_db().execute("SELECT COUNT(*) FROM students").fetchone()[0] == 3


def test_reenroll_unknown_student(admin):
    assert b"not enrolled" in admin.post("/enroll/99/more", follow_redirects=True).data


def test_capture_appends_instead_of_overwriting(mod, tmp_path, monkeypatch):
    """Real capture_face_samples with a fake camera: numbering must continue."""
    import os
    import numpy as np
    from conftest import REAL_CAPTURE
    ds = tmp_path / "ds"
    folder = ds / "1_Asha"
    folder.mkdir(parents=True)
    for i in (1, 2, 3):
        (folder / f"{i}.jpg").write_bytes(b"")

    class Cam:
        def isOpened(self): return True
        def read(self): return True, np.zeros((100, 100, 3), np.uint8)
        def release(self): pass

    class Det:
        def detectMultiScale(self, *a, **k): return [(0, 0, 50, 50)]

    monkeypatch.setattr(mod, "DATASET_DIR", str(ds))
    monkeypatch.setattr(mod, "SAMPLES_PER_STUDENT", 2)
    monkeypatch.setattr(mod, "get_face_detector", lambda: Det())
    monkeypatch.setattr(mod.cv2, "VideoCapture", lambda i: Cam())
    monkeypatch.setattr(mod.cv2, "imshow", lambda *a: None)
    monkeypatch.setattr(mod.cv2, "waitKey", lambda *a: 0)
    monkeypatch.setattr(mod.cv2, "destroyAllWindows", lambda: None)
    assert REAL_CAPTURE(1, "Asha") == 2
    assert sorted(os.listdir(folder)) == ["1.jpg", "2.jpg", "3.jpg", "4.jpg", "5.jpg"]


def test_student_cannot_enroll(with_students):
    with_students.get("/logout")
    login(with_students, "PES1", "PES1")
    r = with_students.post("/enroll", data={"name": "Z", "roll_no": "Z1"})
    assert r.status_code in (302, 403)
    with_students.get("/logout")
    login(with_students, "boss", "secret1")
    assert b"Z1" not in with_students.get("/enroll").data


def test_unenrolled_student_cannot_login(with_students, mod):
    mod.get_db().execute("DELETE FROM students WHERE roll_no='PES2'").connection.commit()
    with_students.get("/logout")
    assert b"not enrolled" in login(with_students, "PES2", "PES2").data
