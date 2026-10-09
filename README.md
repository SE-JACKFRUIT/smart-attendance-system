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

Seed accounts are created automatically on first run (change these for any
real deployment - they only exist so you have something to log in with):

| Role    | Username  | Password    |
|---------|-----------|-------------|
| Admin   | admin     | admin123    |
| Faculty | faculty   | faculty123  |

Each enrolled student also gets a login: **username = their roll number,
password = their roll number**. There is no self-service password change in
this demo build.

## Flow

1. **Enroll** (Admin/Faculty only) - add a student, then look at the webcam
   window that opens (captures ~30 face samples, press `q` to stop early).
   This also creates that student's login account.
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
