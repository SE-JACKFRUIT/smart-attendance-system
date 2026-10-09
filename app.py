"""
Smart Attendance Management System (demo build)
Project ID 20 - Face Recognition Based Smart Attendance Management System
with Analytics and Reporting.

How it works:
  1. Log in (Admin/Faculty/Student - see ACCOUNTS:
  * There are NO built-in accounts. On the very first run (no Admin exists)
    every page redirects to /setup, where you choose your own Admin
    username and password.
  * More Admin/Faculty accounts can be made from the login page via
    "Create new user" - this needs an existing Admin's username+password to
    authorize it, so strangers can't make themselves staff.
  * Students cannot self-register. Enrolling a student creates their login:
    username = roll number, password = roll number. Only enrolled students
    can log in.

This is a beginner-friendly OpenCV (Haar cascade + LBPH) implementation -
no dlib/cmake build tools required, just `pip install -r requirements.txt`.
Must be run on a machine with a webcam attached (your own laptop, not a
cloud/remote server).
"""

import os
import csv
import sqlite3
from functools import wraps
from datetime import date, datetime
from io import StringIO

import cv2
import numpy as np
from flask import (Flask, render_template, request, redirect,
                    url_for, flash, Response, session)
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "attendance.db")
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
TRAINER_PATH = os.path.join(BASE_DIR, "trainer", "trainer.yml")
CASCADE_PATH = os.path.join(BASE_DIR, "data", "haarcascade_frontalface_default.xml")
CONFIDENCE_THRESHOLD = 70   # LBPH: LOWER is a better match. Tune if needed.
SAMPLES_PER_STUDENT = 30
MAX_SESSION_SECONDS = 30    # safety cap so the camera window can't hang forever
LOW_ATTENDANCE_THRESHOLD = 75

os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(os.path.dirname(TRAINER_PATH), exist_ok=True)

app = Flask(__name__)
app.secret_key = "jackfruit-mini-project-demo"  # fine for a class demo only


# ---------------------------------------------------------------- database
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS students (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        roll_no TEXT UNIQUE NOT NULL,
                        enrolled_on TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS attendance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id INTEGER NOT NULL,
                        att_date TEXT NOT NULL,
                        att_time TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'Present',
                        marked_by TEXT NOT NULL DEFAULT 'auto',
                        UNIQUE(student_id, att_date),
                        FOREIGN KEY(student_id) REFERENCES students(id))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL CHECK(role IN ('Admin','Faculty','Student')),
                        linked_roll_no TEXT)""")
    conn.commit()

    # One-time cleanup: delete the old built-in demo accounts (admin/admin123,
    # faculty/faculty123) from existing databases - but only if they still
    # have those default passwords, so a real account is never touched.
    for uname, default_pw in (("admin", "admin123"), ("faculty", "faculty123")):
        row = conn.execute("SELECT id, password_hash FROM users WHERE username = ? AND role IN ('Admin','Faculty')",
                           (uname,)).fetchone()
        if row and check_password_hash(row["password_hash"], default_pw):
            conn.execute("DELETE FROM users WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------- auth helpers
def admin_exists():
    conn = get_db()
    n = conn.execute("SELECT COUNT(*) c FROM users WHERE role = 'Admin'").fetchone()["c"]
    conn.close()
    return n > 0


@app.before_request
def force_first_admin_setup():
    """Until an Admin exists, everything redirects to the setup page."""
    if request.endpoint in ("setup", "static"):
        return None
    if not admin_exists():
        return redirect(url_for("setup"))
    return None


def start_session(user):
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    session["linked_roll_no"] = user["linked_roll_no"]


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("You do not have permission to view that page.", "danger")
                return redirect(url_for("index"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


# ---------------------------------------------------------------- face pipeline
def get_face_detector():
    """Loads the bundled Haar cascade and fails loudly (with a clear message)
    if it didn't load, instead of a cryptic assertion error later on."""
    detector = cv2.CascadeClassifier(CASCADE_PATH)
    if detector.empty():
        raise RuntimeError(
            f"Could not load the face-detection model from {CASCADE_PATH}. "
            "Make sure the data/haarcascade_frontalface_default.xml file exists "
            "in your project folder.")
    return detector


def capture_face_samples(student_id, name):
    """Opens the webcam, grabs SAMPLES_PER_STUDENT cropped face images."""
    detector = get_face_detector()
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        raise RuntimeError("Could not access the webcam. Is one connected and free?")

    folder = os.path.join(DATASET_DIR, f"{student_id}_{name}")
    os.makedirs(folder, exist_ok=True)

    count = 0
    while count < SAMPLES_PER_STUDENT:
        ok, frame = cam.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
        for (x, y, w, h) in faces:
            count += 1
            face_img = cv2.resize(gray[y:y + h, x:x + w], (200, 200))
            cv2.imwrite(os.path.join(folder, f"{count}.jpg"), face_img)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 200, 0), 2)
            break  # one face per frame is enough while enrolling
        cv2.putText(frame, f"Captured {count}/{SAMPLES_PER_STUDENT} - press q to stop",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 0), 2)
        cv2.imshow("Enrolling face - press q to stop early", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()
    return count


def train_model():
    """Retrains the LBPH recognizer on every image currently in dataset/."""
    detector_faces, labels = [], []
    for folder in os.listdir(DATASET_DIR):
        folder_path = os.path.join(DATASET_DIR, folder)
        if not os.path.isdir(folder_path):
            continue
        student_id = int(folder.split("_")[0])
        for filename in os.listdir(folder_path):
            img_path = os.path.join(folder_path, filename)
            gray = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if gray is None:
                continue
            detector_faces.append(gray)
            labels.append(student_id)

    if not detector_faces:
        return False

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(detector_faces, np.array(labels))
    recognizer.save(TRAINER_PATH)
    return True


def scan_faces():
    """Opens the webcam, recognizes faces live, and returns a dict of
    {student_id: True/False} for every enrolled student WITHOUT writing
    anything to the database. Saving is a separate, explicit step so
    faculty can review/override the result first (REQ-OV-1..3)."""
    if not os.path.exists(TRAINER_PATH):
        raise RuntimeError("No trained model yet - enroll at least one student first.")

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(TRAINER_PATH)
    detector = get_face_detector()

    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        raise RuntimeError("Could not access the webcam. Is one connected and free?")

    conn = get_db()
    students = {row["id"]: row["name"] for row in conn.execute("SELECT id, name FROM students")}
    conn.close()

    recognized = set()
    start = cv2.getTickCount()
    freq = cv2.getTickFrequency()
    while True:
        ok, frame = cam.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
        for (x, y, w, h) in faces:
            face_img = cv2.resize(gray[y:y + h, x:x + w], (200, 200))
            label, confidence = recognizer.predict(face_img)
            if confidence < CONFIDENCE_THRESHOLD and label in students:
                name, color = students[label], (0, 200, 0)
                recognized.add(label)
            else:
                name, color = "Unknown", (0, 0, 200)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, color, 2)
        cv2.putText(frame, "Press q to stop", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.imshow("Taking attendance - press q to stop", frame)

        elapsed = (cv2.getTickCount() - start) / freq
        if (cv2.waitKey(1) & 0xFF == ord('q')) or elapsed > MAX_SESSION_SECONDS:
            break

    cam.release()
    cv2.destroyAllWindows()
    # Every enrolled student gets an explicit True/False - absent-by-default
    # for anyone not recognized, rather than just omitting them.
    return {sid: (sid in recognized) for sid in students}


# --------------------------------------------------------------------- auth routes
@app.route("/setup", methods=["GET", "POST"])
def setup():
    """First-run page: create the first Admin. Locked once any Admin exists."""
    if admin_exists():
        return redirect(url_for("login"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if not username or not password:
            flash("Enter a username and a password.", "danger")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        else:
            conn = get_db()
            try:
                conn.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'Admin')",
                             (username, generate_password_hash(password)))
                conn.commit()
            except sqlite3.IntegrityError:
                conn.close()
                flash("That username is already taken (it may belong to a student's roll number).", "danger")
                return redirect(url_for("setup"))
            conn.close()
            flash("Admin account created. Please log in.", "success")
            return redirect(url_for("login"))
        return redirect(url_for("setup"))
    return render_template("setup.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """'Create new user' - makes an Admin or Faculty account. Needs an existing
    Admin's credentials as authorization. Students are NOT created here; they
    get their account when enrolled."""
    if request.method == "POST":
        auth_user = request.form.get("auth_username", "").strip()
        auth_pass = request.form.get("auth_password", "")
        role = request.form.get("role", "Faculty")
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        conn = get_db()
        admin = conn.execute("SELECT * FROM users WHERE username = ? AND role = 'Admin'",
                             (auth_user,)).fetchone()
        if not admin or not check_password_hash(admin["password_hash"], auth_pass):
            conn.close()
            flash("Authorizing admin username or password is wrong.", "danger")
            return redirect(url_for("register"))
        if role not in ("Admin", "Faculty"):
            conn.close()
            flash("Choose Admin or Faculty. Students are created by enrolling them.", "danger")
            return redirect(url_for("register"))
        if not username or not password:
            flash("Enter a username and a password.", "danger")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        elif conn.execute("SELECT 1 FROM students WHERE roll_no = ?", (username,)).fetchone():
            flash("That username matches a student's roll number - choose another.", "danger")
        else:
            try:
                conn.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                             (username, generate_password_hash(password), role))
                conn.commit()
                conn.close()
                flash(f"{role} account '{username}' created. You can log in now.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That username is already taken.", "danger")
        conn.close()
        return redirect(url_for("register"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        enrolled = True
        if user and user["role"] == "Student":
            # Only students who are currently enrolled may log in.
            enrolled = conn.execute("SELECT 1 FROM students WHERE roll_no = ?",
                                    (user["linked_roll_no"],)).fetchone() is not None
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            if not enrolled:
                flash("You are not enrolled. Please contact your faculty.", "danger")
                return redirect(url_for("login"))
            start_session(user)
            flash(f"Welcome, {username} ({user['role']}).", "success")
            return redirect(url_for("index"))
        flash("Invalid username or password.", "danger")
        return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("login"))


# --------------------------------------------------------------------- main routes
@app.route("/")
@login_required
def index():
    conn = get_db()
    total_students = conn.execute("SELECT COUNT(*) c FROM students").fetchone()["c"]
    total_sessions = conn.execute("SELECT COUNT(DISTINCT att_date) c FROM attendance").fetchone()["c"]
    today_present = conn.execute(
        "SELECT COUNT(*) c FROM attendance WHERE att_date = ?", (date.today().isoformat(),)
    ).fetchone()["c"]
    conn.close()
    return render_template("index.html", total_students=total_students,
                            total_sessions=total_sessions, today_present=today_present)


@app.route("/enroll", methods=["GET", "POST"])
@role_required("Admin", "Faculty")
def enroll():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        roll_no = request.form.get("roll_no", "").strip()
        if not name or not roll_no:
            flash("Enter both name and roll number.", "danger")
            return redirect(url_for("enroll"))

        conn = get_db()
        if conn.execute("SELECT 1 FROM users WHERE username = ? AND role != 'Student'", (roll_no,)).fetchone():
            conn.close()
            flash(f"'{roll_no}' is already used as an Admin/Faculty username - use a different roll number.", "danger")
            return redirect(url_for("enroll"))
        try:
            cur = conn.execute(
                "INSERT INTO students (name, roll_no, enrolled_on) VALUES (?, ?, ?)",
                (name, roll_no, date.today().isoformat()))
            # Give the student their own login too (username/password = roll
            # number by default - a real deployment should force a change).
            conn.execute(
                "INSERT OR IGNORE INTO users (username, password_hash, role, linked_roll_no) VALUES (?, ?, 'Student', ?)",
                (roll_no, generate_password_hash(roll_no), roll_no))
            conn.commit()
            student_id = cur.lastrowid
        except sqlite3.IntegrityError:
            conn.close()
            flash(f"Roll number '{roll_no}' is already enrolled.", "danger")
            return redirect(url_for("enroll"))
        conn.close()

        try:
            captured = capture_face_samples(student_id, name.replace(" ", ""))
            if captured == 0:
                flash("No face captured - try again with better lighting.", "danger")
            else:
                train_model()
                flash(f"Enrolled {name} ({captured} face samples captured and model retrained). "
                      f"Their login is username '{roll_no}', password '{roll_no}'.", "success")
        except RuntimeError as e:
            flash(str(e), "danger")
        return redirect(url_for("enroll"))

    conn = get_db()
    students = conn.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("enroll.html", students=students)


@app.route("/attendance", methods=["GET", "POST"])
@role_required("Admin", "Faculty")
def attendance():
    if request.method == "POST":
        try:
            results = scan_faces()
            if not results:
                flash("No students are enrolled yet.", "danger")
                return redirect(url_for("attendance"))
            # Stash the scan result (student_id -> bool) in the session so
            # the review screen can show it without re-scanning.
            session["pending_attendance"] = {str(k): v for k, v in results.items()}
            return redirect(url_for("attendance_review"))
        except RuntimeError as e:
            flash(str(e), "danger")
            return redirect(url_for("attendance"))

    conn = get_db()
    today_rows = conn.execute("""SELECT s.name, s.roll_no, a.att_time, a.marked_by FROM attendance a
                                  JOIN students s ON s.id = a.student_id
                                  WHERE a.att_date = ? ORDER BY a.att_time""",
                              (date.today().isoformat(),)).fetchall()
    conn.close()
    return render_template("attendance.html", today_rows=today_rows, today=date.today().isoformat())


@app.route("/attendance/review", methods=["GET"])
@role_required("Admin", "Faculty")
def attendance_review():
    pending = session.get("pending_attendance")
    if pending is None:
        flash("Nothing to review - start a new attendance capture first.", "danger")
        return redirect(url_for("attendance"))

    conn = get_db()
    students = conn.execute("SELECT id, name, roll_no FROM students ORDER BY name").fetchall()
    conn.close()
    rows = [{"id": s["id"], "name": s["name"], "roll_no": s["roll_no"],
             "present": pending.get(str(s["id"]), False)} for s in students]
    return render_template("attendance_review.html", rows=rows)


@app.route("/attendance/save", methods=["POST"])
@role_required("Admin", "Faculty")
def attendance_save():
    pending = session.get("pending_attendance")
    if pending is None:
        flash("Nothing to save - start a new attendance capture first.", "danger")
        return redirect(url_for("attendance"))

    today = date.today().isoformat()
    now_time = datetime.now().strftime("%H:%M:%S")
    conn = get_db()
    changed = 0
    for student_id_str, auto_present in pending.items():
        student_id = int(student_id_str)
        final_present = request.form.get(f"present_{student_id}") == "on"
        status = "Present" if final_present else "Absent"
        marked_by = session["username"] if final_present != auto_present else "auto"
        if final_present != auto_present:
            changed += 1
        # Upsert: insert if no row yet for today, otherwise update it -
        # this is what lets faculty override an already-saved result.
        conn.execute("""INSERT INTO attendance (student_id, att_date, att_time, status, marked_by)
                         VALUES (?, ?, ?, ?, ?)
                         ON CONFLICT(student_id, att_date)
                         DO UPDATE SET status=excluded.status, att_time=excluded.att_time,
                                       marked_by=excluded.marked_by""",
                     (student_id, today, now_time, status, marked_by))
    conn.commit()
    conn.close()
    session.pop("pending_attendance", None)

    msg = "Attendance saved."
    if changed:
        msg += f" {changed} entr{'y was' if changed == 1 else 'ies were'} manually corrected."
    flash(msg, "success")
    return redirect(url_for("attendance"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    total_sessions = conn.execute("SELECT COUNT(DISTINCT att_date) c FROM attendance").fetchone()["c"]

    if session.get("role") == "Student":
        students = conn.execute("SELECT * FROM students WHERE roll_no = ?",
                                 (session.get("linked_roll_no"),)).fetchall()
    else:
        students = conn.execute("SELECT * FROM students ORDER BY name").fetchall()

    rows = []
    for s in students:
        present = conn.execute(
            "SELECT COUNT(*) c FROM attendance WHERE student_id = ?", (s["id"],)
        ).fetchone()["c"]
        pct = round((present / total_sessions) * 100) if total_sessions else 0
        rows.append({"name": s["name"], "roll_no": s["roll_no"],
                      "present": present, "total": total_sessions, "pct": pct})
    conn.close()
    return render_template("dashboard.html", rows=rows, total_sessions=total_sessions,
                            threshold=LOW_ATTENDANCE_THRESHOLD)


@app.route("/export")
@role_required("Admin", "Faculty")
def export_csv():
    conn = get_db()
    data = conn.execute("""SELECT s.name, s.roll_no, a.att_date, a.att_time, a.status, a.marked_by
                            FROM attendance a JOIN students s ON s.id = a.student_id
                            ORDER BY a.att_date, a.att_time""").fetchall()
    conn.close()

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Name", "Roll No", "Date", "Time", "Status", "Marked By"])
    for r in data:
        writer.writerow([r["name"], r["roll_no"], r["att_date"], r["att_time"], r["status"], r["marked_by"]])

    return Response(buf.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": "attachment; filename=attendance_report.csv"})


if __name__ == "__main__":
    init_db()
    app.run(debug=True)