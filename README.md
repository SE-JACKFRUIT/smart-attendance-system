# Smart Attendance Management System (demo)

Face Recognition Based Smart Attendance Management System with Analytics and
Reporting - Project ID 20, Jackfruit SE Mini-Project 2026.

## Setup

```
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in your browser. Run this on a machine with a
webcam attached - it will NOT work on a remote/cloud server.

## Login

There are **no built-in accounts**. On the very first run every page redirects
to `/setup`, where you choose your own Admin username and password.

* More Admin/Faculty accounts: login page -> "Create new user" (needs an
  existing Admin's username + password to authorize).
* Students cannot self-register. Enrolling a student creates their login:
  **username = roll number, password = roll number**. Only currently enrolled
  students can log in.

Sessions expire after **30 minutes of inactivity** (change with the `SESSION_IDLE_MINUTES`
environment variable, e.g. `set SESSION_IDLE_MINUTES=1` in Windows CMD before `python app.py`
to test it quickly).

## Flow

1. **Enroll** (Admin/Faculty only) - add a student, then look at the webcam
   window that opens (captures ~30 face samples, press `q` to stop early).
   This also creates that student's login account. Use **Add more samples**
   next to an enrolled student to capture extra images (different lighting/angles)
   and retrain the model.
2. **Take Attendance** (Admin/Faculty only) - opens the webcam, recognizes
   enrolled faces live (press `q` to stop), then shows a **review screen**
   where you can tick/untick anyone before saving - nothing is written to
   the database until you click Save. Any change you make there is logged
   as a manual override (visible in the "Marked by" column and the CSV
   export).
3. **Dashboard** - attendance % per student. Admin/Faculty see everyone and
   can export a CSV; a Student only sees their own record and has no export
   button.

## Tech

Flask, OpenCV (Haar cascade for detection + LBPH for recognition, via
`opencv-contrib-python`), SQLite, Werkzeug password hashing for auth.
No dlib/cmake build tools required.

## Tests & CI

```
pip install -r requirements-dev.txt
python -m pytest -v
```

Tests mock the webcam, so they run anywhere. GitHub Actions
(`.github/workflows/ci.yml`) runs the tests and a `bandit` security scan on
every push and pull request.
