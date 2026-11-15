# Unit Test Coverage Report

Tool: `pytest-cov` with branch coverage. Run on every push and pull request in CI (the `coverage.xml` is attached to each run as an artifact).

Command: `python -m pytest --cov=app --cov-branch --cov-report=term-missing`

## Result (44 tests, all passing)

| File | Statements | Missed | Branches | Partial branches | Coverage |
|---|---|---|---|---|---|
| app.py | 453 | 94 | 132 | 20 | **76%** |

## What is covered
Authentication and first-run setup, role-based access, enrollment (including rollback and the no-face timeout), attendance review and save (upsert, override audit), dashboard and per-student percentages, CSV export, student view, idle session timeout.

## What is not covered, and why
| Lines | Code | Reason |
|---|---|---|
| 232-252 | `train_model()` (LBPH training) | Needs real face images. Verified manually (Test Plan EN-05). |
| 260-307 | `scan_faces()` (live recognition loop) | Needs a webcam and a trained model. Verified manually (Test Plan AT rows). |
| 103, 150, 163-169, 177, 201, 223 and others | Defensive error paths (missing files, camera failures) | Hard to trigger without hardware. Camera errors are covered by manual test AT-08. |

The webcam-dependent parts are mocked in the automated tests and checked by the 13 manual tests recorded in `docs/Test_Plan_Document.docx`.
