"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# ============================================
# AUTH SCHEMAS
# ============================================

class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user_id: int
    username: str
    full_name: Optional[str] = None
    is_teacher: bool = False
    is_student: bool = False


class TokenData(BaseModel):
    user_id: Optional[int] = None


# ============================================
# USER SCHEMAS
# ============================================

class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# COURSE SCHEMAS
# ============================================

class CourseBase(BaseModel):
    title: str
    description: Optional[str] = None
    category_id: int


class CourseCreate(CourseBase):
    organization_id: int


class CourseAvailableResponse(BaseModel):
    id: int
    title: str
    short_description: Optional[str] = None
    difficulty_level: Optional[str] = None
    credits: Optional[int] = None

    class Config:
        from_attributes = True


class CourseResponse(CourseBase):
    id: int
    slug: str
    status: str
    difficulty_level: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class CourseProgressDetailResponse(BaseModel):
    course_id: int
    title: str
    teacher_name: Optional[str] = None
    progress_percentage: float
    lessons_completed: int
    total_lessons: int
    average_grade: Optional[float] = None
    letter_grade: Optional[str] = None


# ============================================
# MODULE & LESSON SCHEMAS
# ============================================

class LessonBase(BaseModel):
    title: str
    description: Optional[str] = None
    content_type: Optional[str] = None
    duration_minutes: Optional[int] = None


class LessonDetailResponse(BaseModel):
    id: int
    title: str
    content_type: Optional[str] = None
    content_data: Optional[dict] = None
    duration_minutes: Optional[int] = None
    is_completed: bool = False

    class Config:
        from_attributes = True


class LessonResponse(LessonBase):
    id: int
    module_id: int
    sequence_number: int
    is_mandatory: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# ENROLLMENT SCHEMAS
# ============================================

class EnrollmentRequest(BaseModel):
    course_id: int


class EnrollmentResponse(BaseModel):
    id: int
    course_id: int
    user_id: int
    role: str
    status: str
    progress_percentage: float
    enrolled_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# ASSIGNMENT SCHEMAS
# ============================================

class AssignmentBase(BaseModel):
    title: str
    description: Optional[str] = None
    points_possible: float = 100

class AssignmentCreate(AssignmentBase):
    lesson_id: int
    course_id: int
    instructions: Optional[str] = None
    assignment_type: Optional[str] = None
    due_date: Optional[datetime] = None
    allow_late_submission: bool = False
    late_penalty_percentage: float = 0


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    assignment_type: Optional[str] = None
    points_possible: Optional[float] = None
    due_date: Optional[datetime] = None
    allow_late_submission: Optional[bool] = None
    late_penalty_percentage: Optional[float] = None

class AssignmentResponse(AssignmentBase):
    id: int
    lesson_id: int
    course_id: int
    instructions: Optional[str] = None
    assignment_type: Optional[str] = None
    due_date: Optional[datetime] = None
    allow_late_submission: bool
    late_penalty_percentage: float
    created_by: int

    class Config:
        from_attributes = True

class AssignmentDueResponse(BaseModel):
    id: int
    title: str
    course_id: int
    course_title: str
    due_date: Optional[datetime] = None
    points_possible: float
    status: str

class SubmissionRequest(BaseModel):
    assignment_id: int
    content: str
    submission_type: Optional[str] = "text"

class SubmissionResponse(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    submission_type: Optional[str] = None
    status: str
    is_late: bool
    submitted_at: datetime

    class Config:
        from_attributes = True

class SubmissionWithGradeResponse(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    submission_type: Optional[str] = None
    content: str
    status: str
    is_late: bool
    submitted_at: datetime
    points_earned: Optional[float] = None
    feedback: Optional[str] = None

    class Config:
        from_attributes = True

class GradeRequest(BaseModel):
    submission_id: int
    points_earned: float
    feedback: Optional[str] = None

class GradeResponse(BaseModel):
    id: int
    submission_id: int
    points_earned: float
    percentage_earned: float
    feedback: Optional[str] = None
    grader_id: int
    graded_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ============================================
# DASHBOARD SCHEMAS
# ============================================

class CourseProgressResponse(BaseModel):
    id: int
    title: str
    progress: float
    role: str
    status: str
    teacher_name: Optional[str] = None


class DashboardResponse(BaseModel):
    user_id: int
    username: str
    full_name: Optional[str]
    courses: List[CourseProgressResponse]


# ============================================
# CHATBOT SCHEMAS
# ============================================

class ChatMessageRequest(BaseModel):
    message: str
    course_id: Optional[int] = None
    lesson_id: Optional[int] = None


class ChatMessageResponse(BaseModel):
    id: Optional[int] = None
    message: str
    response: str
    timestamp: datetime


# ============================================
# PROGRESS SCHEMAS
# ============================================

class ProgressResponse(BaseModel):
    user_id: int
    course_id: int
    completion_percentage: float
    time_spent_seconds: int
    last_activity: Optional[datetime] = None


class SkillAssessmentResponse(BaseModel):
    skill_name: str
    mastery_level: float
    timestamp: datetime

class StudentProgressResponse(BaseModel):
    user_id: int
    username: str
    full_name: Optional[str] = None
    progress_percentage: float

class StudentSummaryResponse(BaseModel):
    username: str
    full_name: Optional[str] = None
    active_courses: int
    pending_assignments: int
    assignments_due_this_week: int
    overall_progress: float

class StudentProgressSummaryResponse(BaseModel):
    average_grade: Optional[float] = None
    assignments_completed: int
    courses: list[CourseProgressDetailResponse]

# ============================================
# ERROR SCHEMAS
# ============================================

class ErrorResponse(BaseModel):
    detail: str
    status_code: int