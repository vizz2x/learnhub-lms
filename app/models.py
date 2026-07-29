"""
SQLAlchemy models - Simplified for Python 3.13 compatibility
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, Numeric, ForeignKey, JSON, Date
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

# Core Users
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True)
    email = Column(String(255), unique=True)
    password_hash = Column(String(255))
    full_name = Column(String(255))
    status = Column(String(20), default="active")
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

# Organizations
class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    slug = Column(String(100))
    is_active = Column(Boolean, default=True)

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    name = Column(String(255))

# Courses & Content
class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    title = Column(String(255))
    slug = Column(String(100))
    description = Column(Text)
    status = Column(String(20), default="draft")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

class Module(Base):
    __tablename__ = "modules"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    title = Column(String(255))
    sequence_number = Column(Integer)

class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True)
    module_id = Column(Integer, ForeignKey("modules.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    title = Column(String(255))
    content_data = Column(JSON)
    content_type = Column(String(50))
    duration_minutes = Column(Integer)
    sequence_number = Column(Integer)
    is_mandatory = Column(Boolean, default=True)
    is_visible = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))

# Enrollment
class Enrollment(Base):
    __tablename__ = "enrollments"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String(50))
    status = Column(String(20), default="active")
    progress_percentage = Column(Numeric(5,2), default=0)
    enrolled_at = Column(DateTime, default=datetime.utcnow)

class EnrollmentMethod(Base):
    __tablename__ = "enrollment_methods"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"))

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    name = Column(String(255))
    created_by = Column(Integer, ForeignKey("users.id"))

class GroupMember(Base):
    __tablename__ = "group_members"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    user_id = Column(Integer, ForeignKey("users.id"))

# Permissions & Roles
class Capability(Base):
    __tablename__ = "capabilities"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

class RoleCapability(Base):
    __tablename__ = "role_capabilities"
    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"))
    capability_id = Column(Integer, ForeignKey("capabilities.id"))

class Context(Base):
    __tablename__ = "contexts"
    id = Column(Integer, primary_key=True)
    context_type = Column(String(50))

class RoleAssignment(Base):
    __tablename__ = "role_assignments"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role_id = Column(Integer, ForeignKey("roles.id"))
    context_id = Column(Integer, ForeignKey("contexts.id"))

# Assignments & Grades
class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    title = Column(String(255))
    points_possible = Column(Numeric(5,2))
    description = Column(Text)
    instructions = Column(Text)
    assignment_type = Column(String(50))
    due_date = Column(DateTime)
    allow_late_submission = Column(Boolean, default=False)
    late_penalty_percentage = Column(Numeric(5,2), default=0)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"))
    student_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    submission_type = Column(String(20))
    submitted_at = Column(DateTime, default=datetime.utcnow)
    is_late = Column(Boolean, default=False)
    status = Column(String(20))

class Grade(Base):
    __tablename__ = "grades"
    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"))
    points_earned = Column(Numeric(5,2))
    percentage_earned = Column(Numeric(5,2))
    grader_id = Column(Integer, ForeignKey("users.id"))
    feedback = Column(Text)
    graded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Quizzes
class Quiz(Base):
    __tablename__ = "quizzes"
    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    title = Column(String(255))
    created_by = Column(Integer, ForeignKey("users.id"))

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    id = Column(Integer, primary_key=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id = Column(Integer, primary_key=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))
    student_id = Column(Integer, ForeignKey("users.id"))

# Progress & Analytics
class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    student_id = Column(Integer, ForeignKey("users.id"))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    is_completed = Column(Boolean, default=False)
    time_spent_seconds = Column(Integer, default=0)

class StudentProgress(Base):
    __tablename__ = "student_progress"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    completion_percentage = Column(Numeric(5,2))

class SkillAssessment(Base):
    __tablename__ = "skill_assessments"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    skill_name = Column(String(255))

# Gamification
class UserPoints(Base):
    __tablename__ = "user_points"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    points_earned = Column(Integer, default=0)
    reason = Column(String(100), nullable=True)
    earned_at = Column(DateTime, default=datetime.utcnow)


class UserBadge(Base):
    __tablename__ = "user_badges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    badge_id = Column(Integer, ForeignKey("badges.id"))
    earned_at = Column(DateTime, default=datetime.utcnow)


class Badge(Base):
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    description = Column(Text, nullable=True)
    icon = Column(String(10), default="🏅")
    criteria = Column(String(100), nullable=True)

class Streak(Base):
    __tablename__ = "streaks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_activity_date = Column(Date, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)

# Communication
class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    action = Column(String(100))

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    recipient_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(255))

# Parent Access
class ParentAccount(Base):
    __tablename__ = "parent_accounts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

class ParentStudentLink(Base):
    __tablename__ = "parent_student_links"
    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey("parent_accounts.id"))
    student_id = Column(Integer, ForeignKey("users.id"))

# AI & Content
class AIGeneratedContent(Base):
    __tablename__ = "ai_generated_content"
    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    content = Column(Text)

class GeneratedQuiz(Base):
    __tablename__ = "generated_quizzes"
    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))

# Settings & Audit
class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    setting_key = Column(String(255))

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(20))