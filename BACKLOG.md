# Product Backlog — Smart Attendance Management System (Project ID 20)

This backlog mirrors the WBS in the Project Plan Document. Each story below is meant
to become one GitHub Issue, added to a GitHub Projects board with columns
**To Do / In Progress / Done**. Labels suggested per story (`feature:*`, `priority:*`).

How to turn this into real GitHub Issues: see the two options at the bottom of this file.

---

## Epic: Authentication & Roles

### US-01 — First-run Admin setup and login
**As an** Admin or Faculty member, **I want** to create the first Admin account on first run and log in securely
**so that** there are no default passwords and only authorized staff can access the system.
- Acceptance criteria:
  - [ ] With no Admin in the database, every page redirects to `/setup`
  - [ ] Admin created via `/setup` can log in; wrong password is rejected with a clear message
  - [ ] More Admin/Faculty accounts can be created only with an existing Admin's credentials
- Story points: 2 | Priority: High | Linked: REQ-AU-1, REQ-AU-2 | Labels: `feature:auth`, `priority:high`

### US-02 — Role-based route protection
**As an** Admin, **I want** Enroll/Attendance/Export restricted to Admin and Faculty only
**so that** Students cannot modify or export attendance data.
- Acceptance criteria:
  - [ ] Student role redirected with a permission-denied message on those routes
  - [ ] Admin/Faculty can access them normally
- Story points: 3 | Priority: High | Linked: REQ-AU-3 | Labels: `feature:auth`, `priority:high`

### US-03 — Auto-created Student logins
**As a** Student, **I want** a login automatically created when I'm enrolled
**so that** I can check my own attendance without a separate signup step.
- Acceptance criteria:
  - [ ] Enrolling a student creates a linked `Student`-role user (username = roll number)
  - [ ] Only currently enrolled students can log in
- Story points: 2 | Priority: Medium | Linked: REQ-AU-4 | Labels: `feature:auth`

---

## Epic: Student Enrollment

### US-04 — Capture face samples
**As** Faculty, **I want** to capture ~30 reference face images for a new student
**so that** the system can later recognize them.
- Acceptance criteria:
  - [ ] At least 3 samples captured before enrollment is considered successful
  - [ ] Frames with 0 or 2+ faces are not saved as samples
- Story points: 5 | Priority: High | Linked: REQ-EN-1, REQ-EN-2 | Labels: `feature:enrollment`, `priority:high`

### US-05 — Reject duplicate roll numbers
**As** Faculty, **I want** duplicate roll numbers rejected
**so that** we don't get two student records for the same person.
- Acceptance criteria:
  - [ ] Enrolling an existing roll number shows a clear error, no camera opens
- Story points: 1 | Priority: Medium | Labels: `feature:enrollment`

### US-06 — Retrain model on enroll
**As** Faculty, **I want** the recognition model retrained after every enrollment
**so that** new students are recognizable immediately.
- Acceptance criteria:
  - [ ] `trainer.yml` updates after each successful enrollment
- Story points: 3 | Priority: High | Linked: REQ-EN-3 | Labels: `feature:enrollment`, `priority:high`

### US-07 — Re-enroll an existing student
**As** Faculty, **I want** to add more face samples to an already-enrolled student
**so that** recognition improves over time (different lighting, angles, etc.).
- Acceptance criteria:
  - [ ] Re-running enrollment for an existing student supplements their images and retrains
- Story points: 2 | Priority: Low | Linked: REQ-EN-4 | Labels: `feature:enrollment`

---

## Epic: Attendance Capture

### US-08 — Live face recognition for attendance
**As** Faculty, **I want** the camera to recognize enrolled students during a session
**so that** I don't have to call roll manually.
- Acceptance criteria:
  - [ ] Enrolled students in frame are matched against the trained model
  - [ ] Unenrolled faces are labeled "Unknown", not force-matched
- Story points: 5 | Priority: High | Linked: REQ-AT-1..3, REQ-AT-5 | Labels: `feature:attendance`, `priority:high`

### US-09 — Session timing safety cap
**As** Faculty, **I want** the capture session to stop automatically after 30 seconds
**so that** a forgotten camera window doesn't block the app indefinitely.
- Acceptance criteria:
  - [ ] Session auto-stops at 30s if 'q' isn't pressed first
- Story points: 1 | Priority: Medium | Labels: `feature:attendance`

---

## Epic: Manual Override

### US-10 — Review screen before saving
**As** Faculty, **I want** to see and correct the camera's attendance result before it's saved
**so that** recognition mistakes don't become permanent records.
- Acceptance criteria:
  - [ ] Capture does NOT write to the database directly
  - [ ] A checklist screen shows the camera's result per student, editable
- Story points: 5 | Priority: High | Linked: REQ-OV-1 | Labels: `feature:override`, `priority:high`

### US-11 — Audit trail for overrides
**As an** Admin, **I want** to know who changed an attendance result and that it differed from the camera
**so that** I can trust the record and investigate disputes.
- Acceptance criteria:
  - [ ] Unchanged entries are stored as `marked_by = 'auto'`
  - [ ] Changed entries store the faculty username instead
- Story points: 2 | Priority: Medium | Linked: REQ-OV-2 | Labels: `feature:override`

### US-12 — Same-day re-save updates, not duplicates
**As** Faculty, **I want** re-saving attendance for the same day to update the existing record
**so that** we never get duplicate rows for one student on one day.
- Acceptance criteria:
  - [ ] Second save for the same student+date overwrites the first, doesn't duplicate
- Story points: 2 | Priority: Medium | Labels: `feature:override`

---

## Epic: Analytics Dashboard

### US-13 — Attendance percentage per student
**As** Faculty, **I want** to see each student's attendance % at a glance
**so that** I can identify who's falling behind.
- Acceptance criteria:
  - [ ] % computed as present/total sessions, rounded correctly
  - [ ] Students below 75% are visually flagged
- Story points: 3 | Priority: High | Linked: REQ-AN-1, REQ-AN-3 | Labels: `feature:analytics`, `priority:high`

### US-14 — Student sees only their own record
**As a** Student, **I want** to see only my own attendance, not my classmates'
**so that** my classmates' data stays private from me.
- Acceptance criteria:
  - [ ] Student-role dashboard filters to their linked roll number only
- Story points: 2 | Priority: High | Linked: REQ-AN-4 | Labels: `feature:analytics`, `priority:high`

---

## Epic: Reports

### US-15 — CSV export
**As** Faculty, **I want** to export the full attendance history as a CSV
**so that** I can submit records to the department or analyze them further.
- Acceptance criteria:
  - [ ] CSV includes Name, Roll No, Date, Time, Status, Marked By
  - [ ] Correct filename on download
- Story points: 2 | Priority: Medium | Linked: REQ-RP-1..3 | Labels: `feature:reports`

---

## Epic: Project Infrastructure (shared, not tied to one feature)

### US-16 — CI pipeline runs tests on every push
**As a** team, **we want** GitHub Actions to run our test suite automatically
**so that** broken code is caught before it's merged.
- Story points: 2 | Priority: Medium | Labels: `infra`

### US-17 — Code review required before merge
**As a** team, **we want** every pull request reviewed by a teammate
**so that** we catch mistakes and everyone understands the whole codebase.
- Story points: 1 | Priority: Medium | Labels: `infra`

---

## Turning this into GitHub Issues

**Option A — Manual (simplest):** For each story above, click *Issues → New issue* in
your repo, paste the title and body, add the suggested labels, and drag it onto your
Projects board's "To Do" column.

**Option B — Fast, via GitHub CLI** (if you have `gh` installed and run `gh auth login`
once): save each story as a one-line command and run them in your terminal, e.g.:

```bash
gh issue create --title "US-01: First-run Admin setup and login" \
  --body "As an Admin or Faculty member, I want a working login by creating the first Admin on first run. Acceptance: no Admin -> redirected to /setup; wrong password rejected." \
  --label "feature:auth,priority:high"
```

Repeat per story (or ask your AI assistant to generate all 17 commands for you to paste
in one go once your labels are created).
