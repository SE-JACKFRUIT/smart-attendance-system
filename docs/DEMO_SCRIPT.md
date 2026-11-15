# Final Demo Script (about 5 minutes)

Before you start: delete `attendance.db`, `dataset/*`, `trainer/*` (keep `.gitkeep`), run `python app.py`, open http://127.0.0.1:5000. Good light, face the camera.

| # | Do | Say |
|---|---|---|
| 1 | Open the site. It redirects to `/setup`. Create Admin. | "No default passwords. The first Admin is created on first run (deviation D1)." |
| 2 | Log in. Go to Enroll. Add yourself (roll no, name). Follow the on-screen prompts. | "100 samples, one every 0.18 s, with head-pose prompts. Haar cascade finds the face, LBPH learns it." |
| 3 | (Optional) Cover the camera during an enrollment. | "10 s with no face stops it and rolls the student back (D6, D7)." |
| 4 | Click Add more samples. | "Another 100 appended, 200 total, model retrained." |
| 5 | Take Attendance. Show your face, press `q`. | "Recognised faces are held in the session, nothing is written yet." |
| 6 | Review screen. Untick one, save. | "Only recognised students are listed. Unticked becomes Absent, marked_by is the faculty username. Ticked is 'auto'." |
| 7 | Save again the same day. | "Upsert: no duplicates (US-12)." |
| 8 | Dashboard, then Export CSV. | "Present-only counts, percentage per student, CSV report." |
| 9 | Log out, log in as student (roll / roll). | "RBAC: student sees only their own record." |
| 10 | Show GitHub: issues, board, PRs, green CI, `docs/DEVIATIONS.md`. | "17 stories, PR flow, 44 tests on every push, deviations documented." |

## Likely questions
- Haar vs LBPH? Haar cascade detects where a face is; LBPH recognises whose face it is.
- Why does lower confidence mean a better match? LBPH returns a distance. Below `CONFIDENCE_THRESHOLD` (70) counts as a match.
- Unknown faces? LBPH has no real unknown class; a strict threshold is the mitigation (known limitation).
- Why tests mock the webcam? CI has no camera. 13 webcam tests were run manually and recorded in the Test Plan.
- What does CI do? Installs headless OpenCV, runs pytest and bandit on every push and PR.
- RBAC? Decorators on routes check the session role (Admin, Faculty, Student).
- Not implemented? See SRS Appendix C and `DEVIATIONS.md` D15 to D21 (date filters, trend chart, PDF export, etc.).
- Team? Be honest about who contributed code.
