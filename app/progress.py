from sqlalchemy.orm import Session
from .models import Lesson, LessonProgress, Assignment, Submission, Grade, Enrollment


def recalculate_course_progress(db: Session, course_id: int, student_id: int):
    """
    Recalculates and saves a student's progress percentage for a course,
    based on completed mandatory lessons plus graded assignments.
    """
    total_mandatory_lessons = db.query(Lesson).filter(
        Lesson.course_id == course_id,
        Lesson.is_mandatory == True
    ).count()

    completed_lessons = db.query(LessonProgress).join(
        Lesson, LessonProgress.lesson_id == Lesson.id
    ).filter(
        Lesson.course_id == course_id,
        Lesson.is_mandatory == True,
        LessonProgress.student_id == student_id,
        LessonProgress.is_completed == True
    ).count()

    total_assignments = db.query(Assignment).filter(
        Assignment.course_id == course_id
    ).count()

    graded_assignments = db.query(Submission).join(
        Assignment, Submission.assignment_id == Assignment.id
    ).join(
        Grade, Grade.submission_id == Submission.id
    ).filter(
        Assignment.course_id == course_id,
        Submission.student_id == student_id
    ).count()

    total_items = total_mandatory_lessons + total_assignments
    completed_items = completed_lessons + graded_assignments

    new_percentage = round((completed_items / total_items * 100), 2) if total_items > 0 else 0

    enrollment = db.query(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.user_id == student_id
    ).first()

    if enrollment:
        enrollment.progress_percentage = new_percentage
        db.commit()

    return new_percentage