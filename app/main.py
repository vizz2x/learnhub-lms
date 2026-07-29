"""
LearnHub LMS 2.0 - Main FastAPI Application
Week 2: Database-connected backend
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import jwt
import os
from dotenv import load_dotenv
import hashlib

from .database import get_db, engine
from .models import Base, User, Course, Enrollment, Lesson, Module, LessonProgress, Assignment, Submission, Grade, UserBadge, Badge, Streak, UserPoints
from .schemas import (
    LoginRequest, LoginResponse,
    CourseProgressResponse, DashboardResponse,
    EnrollmentRequest, EnrollmentResponse,
    CourseAvailableResponse, LessonDetailResponse,
    StudentProgressResponse, AssignmentDueResponse, AssignmentUpdate,
    StudentSummaryResponse, StudentProgressSummaryResponse,
    CourseProgressDetailResponse
)
from .gamification import award_points, check_and_award_badges, get_total_points, update_streak
from app.routers import assignments
from app.progress import recalculate_course_progress
from app.permissions import require_enrolled_student, require_course_teacher

load_dotenv()

app = FastAPI(
    title="LearnHub LMS",
    description="Learning Management System with AI Tutoring",
    version="0.2.0"
)

app.include_router(assignments.router)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# ============================================
# UTILITY FUNCTIONS
# ============================================

def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    return hash_password(plain_password) == hashed_password


def create_access_token(user_id: int, expires_delta: timedelta = None) -> str:
    """Create JWT token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    
    to_encode = {"sub": user_id, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> int:
    """Verify JWT token and return user_id"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        return int(user_id)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )

def get_current_user(token: str = None, db: Session = Depends(get_db)) -> User:
    """Get current user from token"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token required"
        )
    
    user_id = verify_token(token)
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

# ============================================
# HEALTH CHECK
# ============================================

@app.get("/")
def read_root():
    """Health check endpoint"""
    return {
        "message": "LearnHub API is running",
        "status": "ok",
        "version": "0.2.0"
    }


@app.get("/health")
def health_check():
    """Health check with database"""
    try:
        # Try to connect to database
        from .database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


# ============================================
# AUTHENTICATION ENDPOINTS
# ============================================

from .schemas import ProfileUpdate

@app.put("/auth/profile")
def update_profile(request: ProfileUpdate, token: str = None, db: Session = Depends(get_db)):
    user = get_current_user(token, db)

    if request.full_name is not None:
        user.full_name = request.full_name

    if request.current_password and request.new_password:
        if not verify_password(request.current_password, user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        user.password_hash = hash_password(request.new_password)

    db.commit()
    return {"message": "Profile updated successfully"}


@app.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password
    
    Returns JWT token for authenticated requests
    """
    
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create token
    access_token = create_access_token(user.id)

    is_teacher = db.query(Course).filter(Course.created_by == user.id).first() is not None
    is_student = not is_teacher  # Everyone who isn't a teacher is a student
    
    return LoginResponse(
        token=access_token,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        is_teacher=is_teacher,
        is_student=is_student
    )


@app.post("/auth/signup")
def signup(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Sign up new user
    
    Creates new user account
    """
    
    # Check if user exists
    existing_user = db.query(User).filter(
        (User.email == request.email) | 
        (User.username == request.email.split("@")[0])
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )
    
    # Create new user
    new_user = User(
        username=request.email.split("@")[0],
        email=request.email,
        password_hash=hash_password(request.password),
        status="active"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create token
    access_token = create_access_token(new_user.id)
    
    return LoginResponse(
        token=access_token,
        user_id=new_user.id,
        username=new_user.username
    )


# ============================================
# COURSE ENDPOINTS
# ============================================

@app.get("/teacher/courses")
def get_teacher_courses(token: str = None, db: Session = Depends(get_db)):
    """
    Get courses created by the logged-in teacher
    """
    user = get_current_user(token, db)

    courses = db.query(Course).filter(Course.created_by == user.id).all()

    return {
        "courses": [
            {"id": c.id, "title": c.title, "status": c.status}
            for c in courses
        ]
    }

@app.get("/courses")
def get_courses(token: str = None, db: Session = Depends(get_db)):
    """
    Get all courses for logged-in user
    
    Returns courses user is enrolled in
    """
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token required"
        )
    
    # Decode token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get enrollments
    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == user.id,
        Enrollment.status == "active"
    ).all()
    
    # Get course details
    courses = []
    for enrollment in enrollments:
        course = db.query(Course).filter(Course.id == enrollment.course_id).first()
        if course:
            courses.append(CourseProgressResponse(
                id=course.id,
                title=course.title,
                progress=float(enrollment.progress_percentage),
                role=enrollment.role,
                status=enrollment.status
            ))
    
    return {"courses": courses, "count": len(courses)}


@app.post("/courses/{course_id}/enroll", response_model=EnrollmentResponse)
def enroll_course(course_id: int, token: str = None, db: Session = Depends(get_db)):
    """
    Enroll student in a course
    
    Adds user to course with student role
    """
    
    user = get_current_user(token, db)
    
    # Check if already enrolled
    existing = db.query(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.user_id == user.id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already enrolled in this course"
        )
    
    # Check if course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Create enrollment
    enrollment = Enrollment(
        course_id=course_id,
        user_id=user.id,
        role="student",
        status="active"
    )
    
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    
    return EnrollmentResponse(
        id=enrollment.id,
        course_id=enrollment.course_id,
        user_id=enrollment.user_id,
        role=enrollment.role,
        status=enrollment.status,
        progress_percentage=float(enrollment.progress_percentage),
        enrolled_at=enrollment.enrolled_at
    )

@app.get("/courses/available", response_model=list[CourseAvailableResponse])
def get_available_courses(token: str = None, db: Session = Depends(get_db)):
    """
    Get published courses the student is NOT yet enrolled in
    """
    user = get_current_user(token, db)

    enrolled_course_ids = db.query(Enrollment.course_id).filter(
        Enrollment.user_id == user.id
    ).subquery()

    courses = db.query(Course).filter(
        Course.status == "published",
        ~Course.id.in_(enrolled_course_ids)
    ).all()

    return courses

@app.get("/courses/{course_id}")
def get_course_details(course_id: int, token: str = None, db: Session = Depends(get_db)):
    """
    Get course details with modules and lessons
    """
    
    user = get_current_user(token, db)

    # Get course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Check enrollment OR course ownership — either grants access
    enrollment = db.query(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.user_id == user.id
    ).first()

    is_teacher = course.created_by == user.id

    if not enrollment and not is_teacher:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enrolled in this course"
        )
    
    # Get modules and lessons
    modules = db.query(Module).filter(Module.course_id == course_id).all()
    
    modules_data = []
    for module in modules:
        lessons = db.query(Lesson).filter(Lesson.module_id == module.id).all()
        lessons_data = [
            {
                "id": lesson.id,
                "title": lesson.title,
                "sequence": lesson.sequence_number,
                "is_mandatory": lesson.is_mandatory
            }
            for lesson in lessons
        ]
        
        modules_data.append({
            "id": module.id,
            "title": module.title,
            "sequence": module.sequence_number,
            "lessons": lessons_data
        })
    
    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "status": course.status,
        "modules": modules_data,
        "progress": float(enrollment.progress_percentage) if enrollment else None
    }


@app.get("/lessons/{lesson_id}", response_model=LessonDetailResponse)
def get_lesson_detail(lesson_id: int, token: str = None, db: Session = Depends(get_db)):
    """
    Get full content for a single lesson
    """
    user = get_current_user(token, db)

    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    

    enrollment = db.query(Enrollment).filter(
        Enrollment.course_id == lesson.course_id,
        Enrollment.user_id == user.id
    ).first()

    course = db.query(Course).filter(Course.id == lesson.course_id).first()
    is_teacher = course and course.created_by == user.id

    if not enrollment and not is_teacher:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enrolled in this course"
        )

    progress = db.query(LessonProgress).filter(
        LessonProgress.lesson_id == lesson_id,
        LessonProgress.student_id == user.id
    ).first()

    return LessonDetailResponse(
        id=lesson.id,
        title=lesson.title,
        content_type=lesson.content_type,
        content_data=lesson.content_data,
        duration_minutes=lesson.duration_minutes,
        is_completed=progress.is_completed if progress else False
    )


@app.post("/lessons/{lesson_id}/complete")
def complete_lesson(lesson_id: int, token: str = None, db: Session = Depends(get_db)):
    """
    Mark a lesson as complete for the logged-in student, and recalculate
    that course's overall progress percentage.
    """
    user = get_current_user(token, db)

    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    progress = db.query(LessonProgress).filter(
        LessonProgress.lesson_id == lesson_id,
        LessonProgress.student_id == user.id
    ).first()

    now = datetime.utcnow()
    if progress:
        progress.is_completed = True
        progress.completed_at = now
    else:
        progress = LessonProgress(
            lesson_id=lesson_id,
            student_id=user.id,
            started_at=now,
            completed_at=now,
            is_completed=True
        )
        db.add(progress)

    db.commit()

# Gamification
    award_points(db, user.id, lesson.course_id, 10, 'lesson_complete')

    # Check course completion
    from .progress import recalculate_course_progress
    enrollment = db.query(Enrollment).filter(
        Enrollment.course_id == lesson.course_id,
        Enrollment.user_id == user.id
    ).first()
    if enrollment and float(enrollment.progress_percentage) == 100:
        award_points(db, user.id, lesson.course_id, 100, 'course_complete')
        check_and_award_badges(db, user.id, lesson.course_id, 'course_complete')

    new_percentage = recalculate_course_progress(db, lesson.course_id, user.id)

    newly_earned = check_and_award_badges(db, user.id, lesson.course_id, 'lesson_complete')

    return {
        "lesson_id": lesson_id,
        "is_completed": True,
        "course_progress_percentage": new_percentage,
        "badges_earned": [
            {"name": b.name, "description": b.description, "icon": b.icon}
            for b in newly_earned
        ] if newly_earned else []
    }


@app.get("/courses/{course_id}/students", response_model=list[StudentProgressResponse])
def get_course_students(course_id: int, token: str = None, db: Session = Depends(get_db)):
    """
    Get every enrolled student's progress in this course — teacher only.
    """
    user = get_current_user(token, db)
    require_course_teacher(db, course_id, user.id)

    enrollments = db.query(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.role == "student"
    ).all()

    results = []
    for enrollment in enrollments:
        student = db.query(User).filter(User.id == enrollment.user_id).first()
        if student:
            results.append(StudentProgressResponse(
                user_id=student.id,
                username=student.username,
                full_name=student.full_name,
                progress_percentage=float(enrollment.progress_percentage)
            ))

    return results

@app.get("/courses/{course_id}/leaderboard")
def get_course_leaderboard(course_id: int, token: str = None, db: Session = Depends(get_db)):
    """Top 10 students by points in a course."""
    get_current_user(token, db)

    enrollments = db.query(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.role == "student"
    ).all()

    leaderboard = []
    for enrollment in enrollments:
        points = db.query(UserPoints).filter(
            UserPoints.user_id == enrollment.user_id,
            UserPoints.course_id == course_id
        ).all()
        total = sum(p.points_earned for p in points)

        student = db.query(User).filter(User.id == enrollment.user_id).first()
        if student:
            leaderboard.append({
                "user_id": student.id,
                "username": student.full_name or student.username,
                "points": total,
                "progress": float(enrollment.progress_percentage)
            })

    leaderboard.sort(key=lambda x: x["points"], reverse=True)
    return leaderboard[:10]


# ============================================
# DASHBOARD ENDPOINT
# ============================================

@app.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(token: str = None, db: Session = Depends(get_db)):
    """
    Get student dashboard with progress and courses
    """
    
    user = get_current_user(token, db)
    
    # Get enrollments
    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == user.id,
        Enrollment.status == "active"
    ).all()
    
    # Build course list
    courses = []
    for enrollment in enrollments:
        course = db.query(Course).filter(Course.id == enrollment.course_id).first()
        if course:
            teacher = db.query(User).filter(User.id == course.created_by).first()
            teacher_name = (teacher.full_name or teacher.username) if teacher else None

            courses.append(CourseProgressResponse(
                id=course.id,
                title=course.title,
                progress=float(enrollment.progress_percentage),
                role=enrollment.role,
                status=enrollment.status,
                teacher_name=teacher_name
            ))
    return DashboardResponse(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        courses=courses
    )


@app.get("/student/notifications")
def get_notifications(token: str = None, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    notifications = []

    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == user.id,
        Enrollment.status == "active"
    ).all()

    enrolled_course_ids = [e.course_id for e in enrollments]

    # Grade notifications — real data
    for enrollment in enrollments:
        course = db.query(Course).filter(Course.id == enrollment.course_id).first()
        if not course:
            continue
        assignments = db.query(Assignment).filter(
            Assignment.course_id == enrollment.course_id
        ).all()
        for assignment in assignments:
            submission = db.query(Submission).filter(
                Submission.assignment_id == assignment.id,
                Submission.student_id == user.id
            ).first()
            if submission and submission.status == "graded":
                grade = db.query(Grade).filter(
                    Grade.submission_id == submission.id
                ).first()
                if grade:
                    notifications.append({
                        "id": f"grade-{submission.id}",
                        "type": "grade",
                        "title": f"Assignment graded: {assignment.title}",
                        "body": f"You scored {grade.points_earned}/{assignment.points_possible} in {course.title}",
                        "timestamp": grade.graded_at,
                        "read": False
                    })

    # New course notifications — real data
    # Show published courses created in the last 30 days that student isn't enrolled in
    from datetime import timezone
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    new_courses = db.query(Course).filter(
        Course.status == "published",
        Course.id.notin_(enrolled_course_ids),
        Course.created_at >= thirty_days_ago
    ).all()

    for course in new_courses:
        teacher = db.query(User).filter(User.id == course.created_by).first()
        teacher_name = (teacher.full_name or teacher.username) if teacher else "Your teacher"
        notifications.append({
            "id": f"course-{course.id}",
            "type": "course",
            "title": f"New course available: {course.title}",
            "body": f"{teacher_name} just added a new course you can enroll in.",
            "timestamp": course.created_at,
            "read": False
        })

    # Recommendation notifications — placeholder, real algorithm after pilot
    if len(enrolled_course_ids) > 0:
        available = db.query(Course).filter(
            Course.status == "published",
            Course.id.notin_(enrolled_course_ids)
        ).limit(2).all()

        for course in available:
            notifications.append({
                "id": f"rec-{course.id}",
                "type": "recommendation",
                "title": f"Recommended for you: {course.title}",
                "body": "Based on your learning activity, we think you'd enjoy this course.",
                "timestamp": None,
                "read": False
            })

    notifications.sort(
        key=lambda x: (x["timestamp"] is None, x["timestamp"] if x["timestamp"] else ""),
        reverse=True
    )
    return notifications

# ============================================
# ASSIGNMENT ENDPOINTS
# (handled by app/routers/assignments.py, included above)
# ============================================


# ============================================
# CHATBOT ENDPOINT
# ============================================

class ChatbotRequest(BaseModel):
    message: str
    course_id: int
    lesson_id: Optional[int] = None

@app.post("/chatbot/ask")
def ask_chatbot(
    request: ChatbotRequest,
    token: str = None,
    db: Session = Depends(get_db)
):
    """
    Ask chatbot a question about a specific course/lesson
    
    Returns personalized response based on lesson context
    """
    
    # Validate token and get user
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token required"
        )
    
    user_id = verify_token(token)
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get course
    course = db.query(Course).filter(Course.id == request.course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Get lesson (if provided)
    lesson_context = ""
    if request.lesson_id:
        lesson = db.query(Lesson).filter(Lesson.id == request.lesson_id).first()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found"
            )
        
        # Extract lesson content, branching by type
        if lesson.content_data:
            lesson_title = lesson.content_data.get("title", lesson.title)

            if lesson.content_type == "video":
                video_url = lesson.content_data.get("video_url", "")
                video_summary = lesson.content_data.get("summary", "")
                if video_summary:
                    lesson_context = f"\n\nLesson: {lesson_title}\nThis is a video lesson.\nSummary: {video_summary}\nVideo link: {video_url}"
                else:
                    lesson_context = f"\n\nLesson: {lesson_title}\nThis is a video lesson ({video_url}). No transcript or summary is available, so answer using general subject knowledge and mention you don't have the video's specific content to reference."
            else:
                lesson_summary = lesson.content_data.get("summary", "")
                lesson_body = lesson.content_data.get("body", "")
                lesson_context = f"\n\nLesson: {lesson_title}\nSummary: {lesson_summary}\n\nContent:\n{lesson_body}"
        else:
            lesson_context = f"\n\nLesson: {lesson.title}"
    
    # Build context for Claude
    context = f"You are a helpful tutor for {course.title}.{lesson_context}\n\nStudent question: {request.message}"
    
    # MOCK RESPONSE (replace with real Claude API later)
    mock_response = f"Based on the {course.title} material, here's my response to your question about '{request.message}': "
    
    if "algebra" in request.message.lower():
        mock_response += "Algebra involves using variables and equations to solve problems. Make sure to follow the order of operations (PEMDAS) and isolate your variable step by step."
    elif "geometry" in request.message.lower():
        mock_response += "Geometry studies shapes and spatial relationships. Remember that angles in a triangle always sum to 180 degrees, and properties of shapes help us understand the world around us."
    else:
        mock_response += "That's a great question! Think about what you've learned in the lesson and try to apply those concepts to your question. Don't hesitate to ask for clarification if you need it."
    
    return {
        "question": request.message,
        "response": mock_response,
        "course": course.title,
        "timestamp": datetime.utcnow()
    }

# ============================================
# PROGRESS ENDPOINTS
# ============================================

@app.get("/progress/{course_id}")
def get_progress(course_id: int, token: str = None, db: Session = Depends(get_db)):
    """
    Get student progress in a course
    """
    
    user = get_current_user(token, db)
    
    # Get enrollment
    enrollment = db.query(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.user_id == user.id
    ).first()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enrolled in this course"
        )
    
    # Get lesson progress
    lessons = db.query(LessonProgress).filter(
        LessonProgress.student_id == user.id
    ).all()
    
    lesson_data = [
        {
            "lesson_id": lp.lesson_id,
            "completed": lp.is_completed,
            "time_spent": lp.time_spent_seconds,
            "completed_at": lp.completed_at
        }
        for lp in lessons
    ]
    
    return {
        "user_id": user.id,
        "course_id": course_id,
        "progress": float(enrollment.progress_percentage),
        "lessons_completed": sum(1 for lp in lessons if lp.is_completed),
        "total_lessons": len(lesson_data),
        "lesson_details": lesson_data
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

@app.get("/student/summary", response_model=StudentSummaryResponse)
def get_student_summary(token: str = None, db: Session = Depends(get_db)):
    """
    Dashboard summary — active courses, pending assignments,
    due this week, overall average progress.
    """
    user = get_current_user(token, db)

    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == user.id,
        Enrollment.status == "active"
    ).all()

    active_courses = len(enrollments)

    now = datetime.utcnow()
    week_from_now = now + timedelta(days=7)

    pending = 0
    due_this_week = 0

    for enrollment in enrollments:
        course_assignments = db.query(Assignment).filter(
            Assignment.course_id == enrollment.course_id
        ).all()

        for assignment in course_assignments:
            existing_submission = db.query(Submission).filter(
                Submission.assignment_id == assignment.id,
                Submission.student_id == user.id
            ).first()

            if not existing_submission:
                pending += 1
                if assignment.due_date and now <= assignment.due_date <= week_from_now:
                    due_this_week += 1

    overall_progress = 0.0
    if enrollments:
        overall_progress = round(
            sum(float(e.progress_percentage) for e in enrollments) / len(enrollments), 2
        )

    return StudentSummaryResponse(
        username=user.username,
        full_name=user.full_name,
        active_courses=active_courses,
        pending_assignments=pending,
        assignments_due_this_week=due_this_week,
        overall_progress=overall_progress
    )


@app.get("/student/assignments", response_model=list[AssignmentDueResponse])
def get_student_assignments(token: str = None, db: Session = Depends(get_db)):
    """
    All assignments across enrolled courses with submission status.
    """
    user = get_current_user(token, db)

    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == user.id,
        Enrollment.status == "active"
    ).all()

    results = []
    for enrollment in enrollments:
        course = db.query(Course).filter(Course.id == enrollment.course_id).first()
        if not course:
            continue

        course_assignments = db.query(Assignment).filter(
            Assignment.course_id == enrollment.course_id
        ).all()

        for assignment in course_assignments:
            submission = db.query(Submission).filter(
                Submission.assignment_id == assignment.id,
                Submission.student_id == user.id
            ).first()

            if submission:
                status = submission.status
            else:
                status = "not started"

            results.append(AssignmentDueResponse(
                id=assignment.id,
                title=assignment.title,
		course_id=course.id,
                course_title=course.title,
                due_date=assignment.due_date,
                points_possible=float(assignment.points_possible),
                status=status
            ))

    results.sort(key=lambda x: (x.due_date is None, x.due_date))
    return results


def get_letter_grade(percentage: float) -> str:
    if percentage >= 70:
        return "A"
    elif percentage >= 60:
        return "B"
    elif percentage >= 50:
        return "C"
    elif percentage >= 45:
        return "D"
    elif percentage >= 40:
        return "E"
    else:
        return "F"


@app.get("/student/progress", response_model=StudentProgressSummaryResponse)
def get_student_progress(token: str = None, db: Session = Depends(get_db)):
    """
    Full progress summary — average grade, completed assignments,
    per-course breakdown with lesson counts and letter grades.
    """
    user = get_current_user(token, db)

    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == user.id,
        Enrollment.status == "active"
    ).all()

    all_grades = []
    assignments_completed = 0
    courses = []

    for enrollment in enrollments:
        course = db.query(Course).filter(Course.id == enrollment.course_id).first()
        if not course:
            continue

        teacher = db.query(User).filter(User.id == course.created_by).first()
        teacher_name = (teacher.full_name or teacher.username) if teacher else None

        total_lessons = db.query(Lesson).filter(
            Lesson.course_id == enrollment.course_id,
            Lesson.is_mandatory == True
        ).count()

        lessons_completed = db.query(LessonProgress).join(
            Lesson, LessonProgress.lesson_id == Lesson.id
        ).filter(
            Lesson.course_id == enrollment.course_id,
            LessonProgress.student_id == user.id,
            LessonProgress.is_completed == True
        ).count()

        course_assignments = db.query(Assignment).filter(
            Assignment.course_id == enrollment.course_id
        ).all()

        course_grades = []
        for assignment in course_assignments:
            submission = db.query(Submission).filter(
                Submission.assignment_id == assignment.id,
                Submission.student_id == user.id
            ).first()

            if submission and submission.status == "graded":
                grade = db.query(Grade).filter(
                    Grade.submission_id == submission.id
                ).first()
                if grade and grade.percentage_earned:
                    course_grades.append(float(grade.percentage_earned))
                    all_grades.append(float(grade.percentage_earned))
                    assignments_completed += 1

        course_avg = round(sum(course_grades) / len(course_grades), 2) if course_grades else None
        letter = get_letter_grade(course_avg) if course_avg is not None else None

        courses.append(CourseProgressDetailResponse(
            course_id=course.id,
            title=course.title,
            teacher_name=teacher_name,
            progress_percentage=float(enrollment.progress_percentage),
            lessons_completed=lessons_completed,
            total_lessons=total_lessons,
            average_grade=course_avg,
            letter_grade=letter
        ))

    overall_avg = round(sum(all_grades) / len(all_grades), 2) if all_grades else None

    return StudentProgressSummaryResponse(
        average_grade=overall_avg,
        assignments_completed=assignments_completed,
        courses=courses
    )


@app.get("/student/gamification")
def get_gamification_summary(token: str = None, db: Session = Depends(get_db)):
    """Points, badges, streak for the logged-in student."""
    user = get_current_user(token, db)

    total_points = get_total_points(db, user.id)

    streak = db.query(Streak).filter(Streak.user_id == user.id).first()
    current_streak = streak.current_streak if streak else 0
    longest_streak = streak.longest_streak if streak else 0

    user_badges = db.query(UserBadge).filter(UserBadge.user_id == user.id).all()
    badges = []
    for ub in user_badges:
        badge = db.query(Badge).filter(Badge.id == ub.badge_id).first()
        if badge:
            badges.append({
                "id": badge.id,
                "name": badge.name,
                "description": badge.description,
                "icon": badge.icon,
                "earned_at": ub.earned_at
            })

    return {
        "total_points": total_points,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "badges": badges,
        "badge_count": len(badges)
    }


# ============================================
# TEACHER ASSIGNMENTS ENDPOINTS
# ============================================

@app.get("/teacher/pending-grades")
def get_pending_grades(token: str = None, db: Session = Depends(get_db)):
    """
    All ungraded submissions across all teacher's courses
    """
    user = get_current_user(token, db)

    teacher_courses = db.query(Course).filter(
        Course.created_by == user.id
    ).all()

    results = []
    for course in teacher_courses:
        assignments = db.query(Assignment).filter(
            Assignment.course_id == course.id
        ).all()
        for assignment in assignments:
            ungraded = db.query(Submission).filter(
                Submission.assignment_id == assignment.id,
                Submission.status == "submitted"
            ).all()
            for sub in ungraded:
                student = db.query(User).filter(User.id == sub.student_id).first()
                results.append({
                    "submission_id": sub.id,
                    "assignment_id": assignment.id,
                    "assignment_title": assignment.title,
                    "course_id": course.id,
                    "course_title": course.title,
                    "student_name": student.username if student else "Unknown",
                    "submitted_at": sub.submitted_at,
                    "points_possible": float(assignment.points_possible)
                })

    results.sort(key=lambda x: x["submitted_at"])
    return results