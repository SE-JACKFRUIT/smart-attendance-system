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
    assert b"NOT enrolled" in r.data
    # nothing may be left behind by a failed enrollment
    c = mod.get_db()
    assert c.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0
    assert c.execute("SELECT COUNT(*) FROM users WHERE username='PES1'").fetchone()[0] == 0
    # ...so the same roll number can be enrolled again straight away
    monkeypatch.setattr(mod, "capture_face_samples", lambda s, n: 30)
    assert b"Enrolled Asha" in admin.post("/enroll", data={"name": "Asha", "roll_no": "PES1"}, follow_redirects=True).data


def test_missing_webcam_error_is_shown(admin, mod, monkeypatch):
    def boom(s, n):
        raise RuntimeError("Could not access the webcam.")
    monkeypatch.setattr(mod, "capture_face_samples", boom)
    r = admin.post("/enroll", data={"name": "Asha", "roll_no": "PES1"}, follow_redirects=True)
    assert b"Could not access the webcam" in r.data and b"NOT enrolled" in r.data
    assert mod.get_db().execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0


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
    monkeypatch.setattr(mod, "CAPTURE_INTERVAL", 0)
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


def test_too_few_samples_counts_as_failure(admin, mod, monkeypatch):
    monkeypatch.setattr(mod, "capture_face_samples", lambda s, n: 2)  # below MIN_SAMPLES
    assert b"NOT enrolled" in admin.post("/enroll", data={"name": "A", "roll_no": "R1"}, follow_redirects=True).data


def test_capture_waits_between_samples(mod, tmp_path, monkeypatch):
    """With a 0.3s interval, a face visible on every frame must NOT produce a sample per frame."""
    import numpy as np
    from conftest import REAL_CAPTURE
    frames = {"n": 0}

    class Cam:
        def isOpened(self): return True
        def read(self):
            frames["n"] += 1
            return True, np.zeros((100, 100, 3), np.uint8)
        def release(self): pass

    class Det:
        def detectMultiScale(self, *a, **k): return [(0, 0, 50, 50)]

    clock = {"t": 0.0}

    def fake_monotonic():
        clock["t"] += 0.05  # each call advances 0.05s (~0.1s per frame)
        return clock["t"]

    monkeypatch.setattr(mod, "DATASET_DIR", str(tmp_path))
    monkeypatch.setattr(mod, "SAMPLES_PER_STUDENT", 5)
    monkeypatch.setattr(mod, "CAPTURE_INTERVAL", 0.3)
    monkeypatch.setattr(mod.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(mod, "get_face_detector", lambda: Det())
    monkeypatch.setattr(mod.cv2, "VideoCapture", lambda i: Cam())
    monkeypatch.setattr(mod.cv2, "imshow", lambda *a: None)
    monkeypatch.setattr(mod.cv2, "waitKey", lambda *a: 0)
    monkeypatch.setattr(mod.cv2, "destroyAllWindows", lambda: None)
    assert REAL_CAPTURE(1, "A") == 5
    assert frames["n"] >= 10   # far more frames were read than samples saved


def test_sample_count_and_timing_settings():
    import app
    assert app.SAMPLES_PER_STUDENT == 100
    assert 15 <= app.SAMPLES_PER_STUDENT * app.CAPTURE_INTERVAL <= 20   # 15-20 s session
    assert app.NO_FACE_TIMEOUT == 10


def _fake_capture_env(mod, monkeypatch, tmp_path, faces_visible):
    import numpy as np
    state = {"frames": 0, "t": 0.0}

    class Cam:
        def isOpened(self): return True
        def read(self):
            state["frames"] += 1
            return True, np.zeros((100, 100, 3), np.uint8)
        def release(self): pass

    class Det:
        def detectMultiScale(self, *a, **k):
            return [(0, 0, 50, 50)] if faces_visible(state) else []

    def clock():
        state["t"] += 0.05
        return state["t"]

    monkeypatch.setattr(mod, "DATASET_DIR", str(tmp_path))
    monkeypatch.setattr(mod.time, "monotonic", clock)
    monkeypatch.setattr(mod, "get_face_detector", lambda: Det())
    monkeypatch.setattr(mod.cv2, "VideoCapture", lambda i: Cam())
    monkeypatch.setattr(mod.cv2, "imshow", lambda *a: None)
    monkeypatch.setattr(mod.cv2, "waitKey", lambda *a: 0)
    monkeypatch.setattr(mod.cv2, "destroyAllWindows", lambda: None)
    return state


def test_stops_after_10_seconds_with_no_face(mod, tmp_path, monkeypatch):
    from conftest import REAL_CAPTURE
    state = _fake_capture_env(mod, monkeypatch, tmp_path, lambda st: False)
    assert REAL_CAPTURE(1, "A") == 0
    assert state["t"] < 12   # gave up at ~10 s of (fake) time, not later


def test_timeout_restarts_when_face_reappears(mod, tmp_path, monkeypatch):
    """Face visible only after ~6 s: must NOT be cut off by the 10 s timer."""
    from conftest import REAL_CAPTURE
    monkeypatch.setattr(mod, "SAMPLES_PER_STUDENT", 3)
    _fake_capture_env(mod, monkeypatch, tmp_path, lambda st: st["t"] > 6)
    assert REAL_CAPTURE(1, "A") == 3


def test_add_more_goes_on_top_of_100(mod, tmp_path, monkeypatch):
    """A student with 100 samples + one more session of 100 -> 200 files."""
    import os
    from conftest import REAL_CAPTURE
    folder = tmp_path / "1_A"
    folder.mkdir()
    for i in range(1, 101):
        (folder / f"{i}.jpg").write_bytes(b"")
    monkeypatch.setattr(mod, "CAPTURE_INTERVAL", 0)
    _fake_capture_env(mod, monkeypatch, tmp_path, lambda st: True)
    assert REAL_CAPTURE(1, "A") == 100
    assert len(os.listdir(folder)) == 200
