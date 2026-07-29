# LearnHub LMS — Session Recap
**Date:** 20 June 2026
**Sessions covered:** Everything since the last recap (16/06/26)

---

## 1. What Was Built

### 1.1 Backend — New Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/assignments/create` | POST | Teacher creates a new assignment |
| `/assignments/course/{course_id}` | GET | List all assignments for a course |
| `/assignments/{assignment_id}` | GET | Fetch a single assignment |
| `/assignments/{assignment_id}/submissions` | GET | Teacher views all submissions + grade status |
| `/assignments/{assignment_id}/my-submission` | GET | Student views their own submission + grade |
| `/submissions/create` | POST | Student submits an assignment |
| `/submissions/{submission_id}` | GET | Fetch a single submission |
| `/grades/create` | POST | Teacher grades a submission |
| `/courses/available` | GET | Students browse courses they can enroll in |
| `/lessons/{lesson_id}` | GET | Fetch full lesson content (text or video) |
| `/lessons/{lesson_id}/complete` | POST | Student marks a lesson as complete |
| `/teacher/courses` | GET | Teacher sees courses they created |
| `/courses/{course_id}/students` | GET | Teacher views per-student progress |

### 1.2 Backend — New Files

- **`app/auth.py`** — Decoupled from `main.py`. Holds `hash_password`, `verify_password`, `create_access_token`, `verify_token`. Prevents circular import when routers need auth.
- **`app/routers/assignments.py`** — Full assignment/submission/grade router. All six endpoints live here, separate from `main.py`.
- **`app/permissions.py`** — Two shared permission helpers used by both `main.py` and the router:
  - `require_course_teacher(db, course_id, user_id)` — raises 403 unless user created the course
  - `require_enrolled_student(db, course_id, user_id)` — raises 403 unless user is enrolled
- **`app/progress.py`** — `recalculate_course_progress(db, course_id, student_id)` — single source of truth for progress math. Called by both `complete_lesson` and `create_grade` so the calculation never drifts between the two write paths.

### 1.3 Backend — Schema Changes

**`schemas.py` additions:**

```python
class AssignmentCreate(AssignmentBase)
class AssignmentResponse(AssignmentBase)
class SubmissionRequest(BaseModel)
class SubmissionResponse(BaseModel)
class SubmissionWithGradeResponse(BaseModel)  # includes content, points_earned, feedback
class GradeRequest(BaseModel)
class GradeResponse(BaseModel)
class CourseAvailableResponse(BaseModel)
class LessonDetailResponse(BaseModel)  # includes is_completed
class StudentProgressResponse(BaseModel)  # user_id, username, full_name, progress_percentage
class CourseProgressResponse(BaseModel)  # extended with teacher_name
```

**`LoginResponse`** extended with `is_teacher: bool` and `is_student: bool` — computed at login from real database relationships, not user-supplied input.

### 1.4 Backend — Model Fixes

Fields added to existing ORM models that were in the real schema but missing from the Python classes:

| Model | Fields Added |
|---|---|
| `Lesson` | `sequence_number`, `is_mandatory`, `is_visible`, `duration_minutes`, `content_type` |
| `Assignment` | `description`, `instructions`, `assignment_type`, `due_date`, `allow_late_submission`, `late_penalty_percentage`, `created_at`, `updated_at` |
| `Submission` | `submission_type`, `is_late` |
| `Grade` | `percentage_earned`, `feedback`, `graded_at`, `created_at`, `updated_at` |
| `LessonProgress` | `started_at`, `completed_at` |

### 1.5 Backend — Bug Fixes

**Duplicate `app = FastAPI()` instance** — `main.py` had two separate `FastAPI()` calls. The router was attached to the first instance, which was immediately overwritten by the second. Every route defined with `@app.post/get` after the second `app = FastAPI()` worked fine; the assignment router was silently orphaned. Fixed by removing the first instance and wiring `include_router` directly after the single real `app`.

**`get_course_details` enrollment-only check** — Teachers (course creators) were blocked from viewing their own courses because `get_course_details` required an `Enrollment` row. Fixed: now checks `Enrollment` OR `Course.created_by == user.id`. Same fix applied to `get_lesson_detail`.

**Stray `require_enrolled_student` in `get_lesson_detail`** — After the enrollment-or-teacher fix was added, a leftover `require_enrolled_student` call earlier in the same function was still rejecting teachers before the new check ever ran. Removed.

**SQLAlchemy version conflict** — Reinstalling requirements after a system restart pulled in SQLAlchemy 2.0, which conflicts with Python 3.13. Pinned back to `sqlalchemy==1.4.46` in `requirements.txt`.

**Zombie backend process** — After a system restart, an old `uvicorn` process continued holding port 8000. New restart attempts started a subprocess but didn't terminate the original. Fixed by identifying the PID via `netstat -ano | findstr :8000` and killing it with `taskkill /PID {pid} /F`.

### 1.6 Security Fixes

**Post-grade resubmission loophole** — Students could re-submit an already-graded assignment, silently replacing their answer while the original grade (for a different answer) remained attached. Fixed in `create_submission`:

```python
if existing and existing.status == "graded":
    raise HTTPException(status_code=400,
        detail="This assignment has already been graded and cannot be resubmitted.")
```

**Student grading exploit** — `create_grade` was missing a `require_course_teacher` check. A student could call `POST /grades/create` directly and assign themselves marks. Confirmed live by a student successfully overwriting a real grade during testing. Fixed: `require_course_teacher(db, assignment.course_id, grader_id)` now runs immediately after the submission and assignment are fetched, before any grade logic executes.

**Permission checks added across the router:**

| Endpoint | Check Added |
|---|---|
| `POST /assignments/create` | `require_course_teacher` |
| `POST /submissions/create` | `require_enrolled_student` |
| `POST /grades/create` | `require_course_teacher` |
| `GET /assignments/{id}` | `require_enrolled_student` |
| `GET /submissions/{id}` | `require_course_teacher` |
| `POST /lessons/{id}/complete` | `require_enrolled_student` |

---

## 2. Frontend — New Files

All files live in `learnhub-frontend/src/`.

| File | Purpose |
|---|---|
| `api.js` | Shared `apiFetch` wrapper — catches 401s globally, alerts user, reloads to login |
| `Dashboard.jsx` | Student dashboard — enrolled courses with progress ticks and teacher name |
| `CourseBrowse.jsx` | Browse and enroll in available courses |
| `CourseDetail.jsx` | Course overview with module/lesson tree; three-panel layout when inside a lesson |
| `LessonViewer.jsx` | Renders text or video lesson content; "Mark as Complete" button |
| `TeacherLessonViewer.jsx` | Same as LessonViewer but for teachers — no completion button |
| `AssignmentList.jsx` | Student assignment list; shows own submission and grade after grading |
| `ChatbotWidget.jsx` | Persistent AI Tutor sidebar — always open inside lesson view |
| `TeacherDashboard.jsx` | Teacher's course list, routes into TeacherCourseDetail |
| `TeacherCourseDetail.jsx` | Teacher course overview — lesson browser, manage assignments, view student progress |
| `TeacherAssignments.jsx` | Assignment list + submission queue + grading navigation |
| `TeacherStudentProgress.jsx` | Per-student progress list for a course |
| `GradingForm.jsx` | Grade entry — shows question, student's actual answer, points and feedback fields |
| `CreateAssignmentForm.jsx` | Teacher creates a new assignment — lesson picker dropdown, due date, late submission toggle |
| `ProgressTicks.jsx` | Reusable progress component — 10 tick marks, gold-filled per 10% completed |

---

## 3. Frontend — Key Logic Patterns

### Role-based routing (App.jsx)
Login calls `/auth/login`, which now returns `is_teacher` and `is_student` computed from real data. `App.jsx` routes automatically:
- Teacher only → `TeacherDashboard`
- Student only → `Dashboard`
- Both → explicit choice screen
- Neither → defaults to `Dashboard`

The radio button toggle was removed entirely.

### Token expiry handling (api.js)
Every authenticated fetch goes through `apiFetch`. On a `401` response, it fires an alert and calls `window.location.reload()`. Since the token only lives in React memory (never in localStorage), a reload wipes the session cleanly and lands back on the login form with zero extra code.

### Progress calculation (app/progress.py)
Progress combines two signals: completed mandatory lessons + graded assignments. Called from two places — `complete_lesson` and `create_grade` — via one shared function so the math is never duplicated. Decision: progress counts when an assignment is **graded**, not merely submitted, to avoid inflating percentages based on effort alone. Trade-off acknowledged: progress can stall if a teacher's grading queue backs up.

### Stale data re-fetch pattern
Every screen that can be navigated away from and returned to calls its own named fetch function rather than nesting it inside `useEffect`. That function is called again on return (`handleBackToDashboard`, `handleAssignmentCreated`, `handleBackFromGrading`) so data always reflects the latest state without a full page reload.

### Three-panel lesson layout
Triggered only when `activeLessonId` is set in `CourseDetail`. All three panels render simultaneously:
- Left: module/lesson nav tree with active lesson highlighted
- Center: `LessonViewer` with `hideBackButton={true}` (navigation handled by left panel)
- Right: `ChatbotWidget` — always expanded, no toggle

---

## 4. Design System

### Palette

| Token | Hex | Usage |
|---|---|---|
| `--ink` | `#1B2A4A` | Headings, borders, primary UI elements |
| `--green` | `#1F5C3F` | Default spine color (enrolled/complete) |
| `--paper` | `#FAF7F0` | Page background |
| `--gold` | `#E8A33D` | Buttons, CTA, available/needs-action spine |
| `--gold-dark` | `#C77F1F` | Button hover, filled tick marks |
| `--red-pen` | `#B23A2E` | Errors, teacher corrections (used sparingly) |
| `--charcoal` | `#2B2B2B` | Body text |
| `--line` | `#D8D2C2` | Borders, empty tick marks |

### Typography

| Token | Font | Usage |
|---|---|---|
| `--font-display` | Fraunces (serif) | All headings |
| `--font-body` | Inter | Body copy, form fields |
| `--font-label` | IBM Plex Mono | Labels, metadata, button text, grades |

### Notebook Card System (`.nb-card`)

Every list item in the app uses the same card structure:

```
┌──┬──────────────────────────────────┐
│██│  Course / Assignment / Student   │
│██│  METADATA LINE                   │
└──┴──────────────────────────────────┘
```

Spine color carries status:
- Green (`.nb-card__spine`) — enrolled course, complete
- Gold (`.nb-card__spine--gold`) — available course, pending assignment, ungraded submission
- Ink (`.nb-card__spine--ink`) — teacher navigation items, student roster

### Page-flip Animation

Two classes with opposing rotation axes:
- `.page-forward` — hinges from left edge (`transform-origin: left center`), `rotateY(-85deg → 0)` — used when drilling into a screen
- `.page-back` — hinges from right edge (`transform-origin: right center`), `rotateY(85deg → 0)` — used when returning to a previous screen

Opacity snaps to `1` at `15%` of the animation so the full rotation arc is visible, not obscured by a slow fade.

### ProgressTicks Component

Ten tick marks per course regardless of actual item count. Each tick represents 10% of total progress. Gold-filled for completed percentage, faint outline for remaining. Percentage label rendered in monospace beside the ticks. Used on: student dashboard course cards, teacher student-progress view.

---

## 5. Deferred Items (Known, Scoped)

| Item | Why Deferred |
|---|---|
| Backend role enforcement (full RBAC) | Current check (created_by + Enrollment) is correct for single school. Full role_assignments/capabilities tables become worth building at 3–4 schools with different staff structures. |
| Organisation-scoping (multi-school) | Same logic, wider query boundary. One additional check per permission function when second school is signed. |
| Quizzes | Confirmed not a launch blocker by product decision. Complex stateful flow (start → answer → submit → auto-grade) best built after pilot validated. |
| Course authoring UI | Deliberate concierge model for pilot — content loaded via SQL INSERT. Self-serve authoring deferred until manually loading content stops scaling (approx. school 3–4). |
| Token expiry — no logout button for nested screens | Token lasts 7 days. `apiFetch` handles expired tokens globally. Logout only visible on top-level dashboard screens. Sufficient for pilot. |
| `GET /assignments/{assignment_id}` — untested endpoint | Built, correct, never exercised by any current screen. Low risk — identical logic to list endpoint. |
| Real-time chatbot (Claude API) | Currently a mock response generator. Phase 2 item once pilot validates the concept. |
| Progress when teacher grades backlog | Progress stalls until teacher grades. Known trade-off of "graded-only" decision. Monitor in pilot. |

---

## 6. Data Decisions Made This Session

**Assignment due-date enforcement:** Submissions past `due_date` are rejected with a `400` unless `allow_late_submission = true` on the assignment. Late submissions are flagged `is_late = true`. Late penalty percentage is stored but NOT auto-applied — teacher sees the `is_late` flag and enters points manually. Rationale: auto-deduction without testing real teacher expectations risks penalising students unfairly.

**Course progress = lessons + graded assignments:** Not lesson-only, not submitted-only. Graded-only chosen deliberately. Progress never auto-increments from the teacher side — only student actions (lesson complete) and teacher actions (grade) move it.

**Video hosting:** No self-hosted video. YouTube unlisted links stored in `content_data.video_url`. The chatbot handles `content_type == "video"` gracefully — uses `summary` field for context if available, falls back to a generic response noting it can't access the video content directly.

**Teacher name on dashboard cards:** Fetched from `Course.created_by → User.full_name || User.username`. Falls back to username if `full_name` is null (common in test accounts).

---

## 7. File Index (Current State)

### Backend (`Learning Management System/app/`)

```
app/
├── main.py              — FastAPI app, auth endpoints, course/lesson/progress endpoints
├── auth.py              — Token and password utilities
├── permissions.py       — require_course_teacher, require_enrolled_student
├── progress.py          — recalculate_course_progress
├── models.py            — SQLAlchemy ORM models (all 35 tables)
├── schemas.py           — Pydantic request/response models
├── database.py          — SessionLocal, engine, get_db
└── routers/
    └── assignments.py   — Assignment, submission, grade endpoints
```

### Frontend (`learnhub-frontend/src/`)

```
src/
├── main.jsx                    — Entry point
├── App.jsx                     — Login form + role-based routing
├── api.js                      — apiFetch wrapper (401 handling + base URL)
├── index.css                   — Full design system (tokens, typography, cards, animation)
├── ProgressTicks.jsx           — Reusable tick-mark progress component
│
├── Dashboard.jsx               — Student dashboard
├── CourseBrowse.jsx            — Available courses + enroll
├── CourseDetail.jsx            — Course overview + 3-panel lesson layout
├── LessonViewer.jsx            — Text/video lesson + Mark Complete
├── AssignmentList.jsx          — Student assignments + own submission/grade view
├── ChatbotWidget.jsx           — Persistent AI Tutor sidebar
│
├── TeacherDashboard.jsx        — Teacher's course list
├── TeacherCourseDetail.jsx     — Teacher course overview (lessons + assignments + progress)
├── TeacherLessonViewer.jsx     — Lesson viewer for teachers (no completion button)
├── TeacherAssignments.jsx      — Assignment list + submission queue
├── TeacherStudentProgress.jsx  — Per-student progress roster
├── GradingForm.jsx             — Grade entry with question + student answer visible
└── CreateAssignmentForm.jsx    — New assignment form with lesson picker
```

---

## 8. Environment

- **Backend:** Python 3.13, FastAPI, SQLAlchemy 1.4.46 (pinned — 2.0 conflicts with Python 3.13), PostgreSQL 18, `learnhub` database
- **Frontend:** Node 24, npm 11, React + Vite, no external UI library
- **Dev servers:** `python -m uvicorn app.main:app --reload` (port 8000), `npm run dev` (port 5173)
- **Project paths:**
  - Backend: `C:\Users\eakoj\OneDrive\Desktop\Learning Management System\`
  - Frontend: `C:\Users\eakoj\OneDrive\Desktop\learnhub-frontend\`
  - Venv: `learnhub_env` inside the backend folder

---

## 9. Next Session

Immediate priorities, in order:

1. **Three-panel layout video fix** — responsive `iframe` (56.25% padding-bottom trick) replacing fixed `width="560"`. Same fix needed in both `LessonViewer.jsx` and `TeacherLessonViewer.jsx`.
2. **Remaining screens needing page-flip class** — `CourseBrowse`, `AssignmentList`, `TeacherAssignments`, `TeacherStudentProgress`, `GradingForm`, `CreateAssignmentForm`, `LessonViewer`, `TeacherLessonViewer` — outer `<div>` needs `className="page-forward"` or `className="page-back"` as appropriate.
3. **Notebook card for lesson list in CourseDetail** — lessons inside `CourseDetail` and `TeacherCourseDetail` still render as plain `<button>` elements, not `.nb-card` components.
4. **Login page design** — untouched so far. Needs the notebook-cover visual identity applied: a "label" block for the title, the exercise-book metaphor carried through to the very first screen a user sees.
5. **Pilot school preparation** — load real curriculum via concierge SQL (course → modules → lessons), enroll real student accounts, brief the teacher on the grading flow.
