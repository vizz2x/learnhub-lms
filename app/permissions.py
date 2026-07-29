from sqlalchemy.orm import Session
from fastapi import HTTPException
from .models import Course, Enrollment


def require_course_teacher(db: Session, course_id: int, user_id: int):
    """
    Raises 403 unless user_id is the creator of this course.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course.created_by != user_id:
        raise HTTPException(
            status_code=403,
            detail="Only the course's teacher can perform this action"
        )


def require_enrolled_student(db: Session, course_id: int, user_id: int):
    """
    Raises 403 unless user_id is enrolled in this course.
    """
    enrollment = db.query(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.user_id == user_id
    ).first()

    if not enrollment:
        raise HTTPException(
            status_code=403,
            detail="You must be enrolled in this course to do that"
        )