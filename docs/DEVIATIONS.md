# Deviations from the Submitted Documents

**Project:** Face Recognition-Based Smart Attendance Management System with Analytics and Reporting (Project ID 20)
**Subject:** UE24CS341A, Software Engineering mini-project
**Team:** 39 (SE GROUP)
**Members:** Mithun S (PES2UG24AM208), Bharath H G (PES2UG24AM197), Varun C H (PES2UG24AM180), Yashwant Aditya Varma (PES2UG24AM190)
**Prepared by:** Mithun S

This file records every place where the final product differs from the submitted SRS,
High-Level Architecture, SW Design, Validation Spec and Test Plan, and why. The changes
were found while building and manually testing the app with a real webcam.

---

## A. Functional deviations

| # | Documents said | Final app does | Reason | Affects |
|---|---|---|---|---|
| D1 | Login accounts are seeded (`admin/admin123`, `faculty/faculty123`). | No built-in accounts. On first run every page redirects to `/setup`, where the first Admin chooses their own username and password. | Default passwords are a security risk. | Auth requirements (REQ-AU), US-01, Test Plan AU rows |
| D2 | Admin/Faculty accounts exist from the start. | More Admin/Faculty accounts are created from the login page ("Create new user"), which requires an existing Admin's username and password. | Stops strangers making themselves staff. | REQ-AU, US-01 |
| D3 | A student has a login once created. | Only **currently enrolled** students can log in (username = roll number, password = roll number). A roll number that matches an Admin/Faculty username cannot be enrolled. | Keeps student and staff accounts from colliding. | REQ-AU, AU Test Plan rows |
| D4 | About 30 face samples are captured per enrollment. | **100 samples per session.** "Add more samples" captures another 100 on top, so a re-enrolled student has 200. | More samples at different angles improve recognition. | REQ-EN, EN-01, EN-07, US-04, US-07 |
| D5 | Samples are captured as fast as frames arrive. | One sample every 0.18 s (about 18 s for 100 samples), with on-screen prompts (look straight, left, right, up, down). | Rapid capture produced near-identical images, with no time to change head position. | REQ-EN, US-04 |
| D6 | No capture timeout beyond a manual stop. | Enrollment stops after **10 seconds with no face visible**. The timer resets whenever a face is seen. | Prevents the camera window hanging when the lens is covered or nobody is there. | REQ-EN, EN-04 |
| D7 | A failed capture might still leave the student in the list. | A failed enrollment (no webcam, or fewer than 3 samples) **removes** the student, their new login and any images. The same roll number can be enrolled again straight away. | Before the fix, a failed attempt left a student with no face data. | REQ-EN, EN-04, US-04, US-05 |
| D8 | The review screen lists **every** enrolled student, and faculty can also tick students the camera missed. | The review screen lists **only students the camera recognised**. Faculty can untick wrong ones (saved as Absent, with their username as the override). **A student the camera missed cannot be added on that screen.** | Requested change: a shorter, clearer list for large classes. | REQ-OV, US-10, US-11, OV Test Plan rows |
| D9 | Saving writes a row for every enrolled student. | Saving writes rows only for the students on the review screen. Students who were not recognised have no row for that day and count as absent on the dashboard. | Follows from D8. | REQ-OV, REQ-AN, US-12 |
| D10 | "Add more samples" is described as a re-enroll action (REQ-EN-4). | Implemented as an **Add more samples** button next to each enrolled student (`/enroll/<id>/more`). | Gives US-07 a real UI. | REQ-EN-4, US-07, EN-07 |

## A2. SRS requirements not (fully) implemented

Found while building the traceability matrix (SRS Appendix C). The matrix marks these Partial or Not implemented.

| # | SRS requirement | Final app | Reason |
|---|---|---|---|
| D15 | REQ-EN-3: store a face encoding vector, not the raw image. | The app stores the cropped face images in `dataset/` (never committed to GitHub) and trains an LBPH model file from them. | LBPH needs the images to retrain the model after each enrollment. |
| D16 | REQ-AT-2, AT-4, AN-1, RP-1: sections, section selection, date ranges, captured-frame reference. | There is no "section" concept. Attendance stores the date and time only. The dashboard and CSV cover all records, with no date-range filter. | Kept the scope small for a mini-project. |
| D17 | REQ-AN-2: chart of attendance trends over time. | The dashboard shows a percentage bar per student, not a trend chart. | Not built. |
| D18 | REQ-RP-2, RP-3: PDF export, and a report header with section, date range and generation time. | Only CSV export exists, with a column-header row. | Not built. |
| D19 | REQ-AU-4: Admin can deactivate users and reset passwords. | Admin-authorised account creation exists, and student logins are created on enrollment. There is no deactivate or password reset. | Not built. |
| D20 | SRS 6.4: fall back to manual attendance entry if the camera is unavailable. | A clear error is shown instead. There is no manual attendance entry screen. | Not built. |
| D21 | SW Design names a function `recognize_and_mark()`. | The code has `scan_faces()` (recognition), `attendance_review()` and `attendance_save()` (review and saving). | The design was written before the review step was split out. |

## B. Defects found in testing and fixed

| # | Defect | Fix |
|---|---|---|
| B1 | After saving attendance, the "Marked present today" list, the Home counter and the Dashboard percentage counted Absent rows as Present. | All three now count only rows with status `Present`. A regression test covers it. |
| B2 | OpenCV 5 could not load its bundled Haar cascade (`detectMultiScale ... !empty()`). | The cascade file is bundled in `data/`, and a clear error is raised if it fails to load. |

## C. Non-functional / process deviations

| # | Documents said | Final project | Reason |
|---|---|---|---|
| D11 | Not specified. | Debug mode is **off** by default (`FLASK_DEBUG=1` turns it on) and the secret key can come from the `SECRET_KEY` environment variable. | The CI security scan (bandit) flagged debug mode and a hard-coded key. |
| D12 | Work shared across the 4-member team, with a second person reviewing pull requests. | Development, testing and documentation were carried out by one member (Mithun S). Pull requests were reviewed by the author, as no second reviewer was available. | Teammates did not contribute code to the repository. |
| D13 | Jira for the backlog. | GitHub Projects and Issues (17 stories). | Agreed with the course approach. No separate Jira needed. |
| D14 | Test Plan: 55 cases. | 43 automated pytest tests run on every push and pull request through GitHub Actions. The webcam-dependent cases are executed manually. | The camera cannot be used in CI, so those tests mock it. |

## D. Known limitations (not fixed)

- **LBPH has no real "unknown" class.** With very few enrolled people the recogniser can label a stranger as an enrolled student. The confidence threshold (`CONFIDENCE_THRESHOLD`, default 70) can be lowered, for example to 50, to be stricter.
- **A recognised student cannot be added on the review screen** (see D8).
- **Student passwords equal their roll number** and there is no self-service change. This is acceptable for a class demo and is not for real use.
- **Recognition quality depends on lighting and camera quality.**
- **The app must run on a machine with a webcam.** It does not work on a remote server.

## E. Documents to update or annotate

| Document | What to note |
|---|---|
| SRS | D1–D10 (auth, enrollment, override behaviour); D15–D20 (requirements not fully implemented) |
| SW Design / Validation Spec | D4–D9 (capture and review behaviour) |
| Test Plan | EN-01, EN-04, EN-07 (sample count, rollback, timeout); AT and OV rows that mention listing or ticking all students |
| Jira Backlog | US-01 (first-run setup instead of seeded accounts); US-10 (recognised-only review) |

*To be explained at the final demo.*
