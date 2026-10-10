import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_module  # noqa: E402

REAL_CAPTURE = app_module.capture_face_samples


@pytest.fixture()
def mod(tmp_path, monkeypatch):
    """The app module wired to a throw-away DB/dataset, with webcam + model
    training mocked out (CI machines have no camera)."""
    monkeypatch.setattr(app_module, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(app_module, "DATASET_DIR", str(tmp_path / "dataset"))
    monkeypatch.setattr(app_module, "TRAINER_PATH", str(tmp_path / "trainer.yml"))
    os.makedirs(app_module.DATASET_DIR, exist_ok=True)
    monkeypatch.setattr(app_module, "capture_face_samples", lambda sid, name: 30)
    monkeypatch.setattr(app_module, "train_model", lambda: True)
    app_module.app.config["TESTING"] = True
    app_module.init_db()
    return app_module


@pytest.fixture()
def client(mod):
    return mod.app.test_client()


def make_admin(client, user="boss", pw="secret1"):
    client.post("/setup", data={"username": user, "password": pw, "confirm": pw})


def login(client, user, pw):
    return client.post("/login", data={"username": user, "password": pw}, follow_redirects=True)


@pytest.fixture()
def admin(client):
    make_admin(client)
    login(client, "boss", "secret1")
    return client


@pytest.fixture()
def with_students(admin):
    for name, roll in (("Asha Rao", "PES1"), ("Bala K", "PES2"), ("Chitra S", "PES3")):
        admin.post("/enroll", data={"name": name, "roll_no": roll})
    return admin
