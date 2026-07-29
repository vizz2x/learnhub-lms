from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.auth import verify_token
from app.permissions import require_course_teacher, require_enrolled_student
from app.models import Assignment, Submission, Grade, Course
from app.schemas import (
    AssignmentCreate, AssignmentUpdate, AssignmentResponse,
    SubmissionRequest, SubmissionResponse, SubmissionWithGradeResponse,
    GradeRequest, GradeResponse
)
from app.progress import recalculate_course_progress
router = APIRouter()


@router.post("/assignments/create", response_model=AssignmentResponse)
def create_assignment(request: AssignmentCreate, token: str = None, db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    user_id = verify_token(token)

    course = db.query(Course).filter(Course.id == request.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    require_course_teacher(db, request.course_id, user_id)
    new_assignment = Assignment(
        lesson_id=request.lesson_id,
        course_id=request.course_id,
        title=request.title,
        description=request.description,
        instructions=request.instructions,
        assignment_type=request.assignment_type,
        points_possible=request.points_possible,
        due_date=request.due_date,
        allow_late_submission=request.allow_late_submission,
        late_penalty_percentage=request.late_penalty_percentage,
        created_by=user_id
    )
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)
    return new_assignment


@router.put("/assignments/{assignment_id}", response_model=AssignmentResponse)
def update_assignment(assignment_id: int, request: AssignmentUpdate, token: str = None, db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    user_id = verify_token(token)

    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    require_course_teacher(db, assignment.course_id, user_id)

    if request.title is not None:
        assignment.title = request.title
    if request.description is not None:
        assignment.description = request.description
    if request.instructions is not None:
        assignment.instructions = request.instructions
    if request.assignment_type is not None:
        assignment.assignment_type = request.assignment_type
    if request.points_possible is not None:
        assignment.points_possible = request.points_possible
    if request.due_date is not None:
        assignment.due_date = request.due_date
    if request.allow_late_submission is not None:
        assignment.allow_late_submission = request.allow_late_submission
    if request.late_penalty_percentage is not None:
        assignment.late_penalty_percentage = request.late_penalty_percentage

    db.commit()
    db.refresh(assignment)
    return assignment

@router.get("/assignments/course/{course_id}", response_model=list[AssignmentResponse])
def list_course_assignments(course_id: int, token: str = None, db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    verify_token(token)
    return db.query(Assignment).filter(Assignment.course_id == course_id).all()


@router.get("/assignments/{assignment_id}", response_model=AssignmentResponse)
def get_assignment(assignment_id: int, token: str = None, db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    user_id = verify_token(token)
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    require_enrolled_student(db, assignment.course_id, user_id)

    return assignment


@router.post("/submissions/create", response_model=SubmissionResponse)
def create_submission(request: SubmissionRequest, token: str = None, db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    user_id = verify_token(token)

    assignment = db.query(Assignment).filter(Assignment.id == request.assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    now = datetime.utcnow()
    is_late = False
    if assignment.due_date and now > assignment.due_date:
        if not assignment.allow_late_submission:
            raise HTTPException(status_code=400, detail="Submission window closed for this assignment")
        is_late = True

    existing = db.query(Submission).filter(
        Submission.assignment_id == request.assignment_id,
        Submission.student_id == user_id
    ).first()
    
    if existing and existing.status == "graded":
        raise HTTPException(
            status_code=400,
            detail="This assignment has already been graded and cannot be resubmitted."
        )

    if existing:
        existing.content = request.content
        existing.submission_type = request.submission_type
        existing.submitted_at = now
        existing.is_late = is_late
        existing.status = "submitted"
        db.commit()
        db.refresh(existing)
        return existing

    new_submission = Submission(
        assignment_id=request.assignment_id,
        student_id=user_id,
        content=request.content,
        submission_type=request.submission_type,
        submitted_at=now,
        is_late=is_late,
        status="submitted"
    )
    db.add(new_submission)
    db.commit()
# Gamification
    from app.gamification import award_points, check_and_award_badges
    award_points(db, user_id, assignment.course_id, 20, 'submission')
    check_and_award_badges(db, user_id, assignment.course_id, 'submission')
    db.refresh(new_submission)
    return new_submission


@router.get("/submissions/{submission_id}", response_model=SubmissionResponse)
def get_submission(submission_id: int, token: str = None, db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    grader_id = verify_token(token)
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    assignment = db.query(Assignment).filter(Assignment.id == submission.assignment_id).first()
    require_course_teacher(db, assignment.course_id, grader_id)
    return submission

@router.get("/assignments/{assignment_id}/submissions", response_model=list[SubmissionWithGradeResponse])
def list_assignment_submissions(assignment_id: int, token: str = None, db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    verify_token(token)

    submissions = db.query(Submission).filter(Submission.assignment_id == assignment_id).all()

    results = []
    for sub in submissions:
        grade = db.query(Grade).filter(Grade.submission_id == sub.id).first()
        results.append(SubmissionWithGradeResponse(
            id=sub.id,
            assignment_id=sub.assignment_id,
            student_id=sub.student_id,
            submission_type=sub.submission_type,
	    content=sub.content,
            status=sub.status,
            is_late=sub.is_late,
            submitted_at=sub.submitted_at,
            points_earned=float(grade.points_earned) if grade else None,
            feedback=grade.feedback if grade else None
        ))

    return results

@router.get("/assignments/{assignment_id}/my-submission", response_model=SubmissionWithGradeResponse)
def get_my_submission(assignment_id: int, token: str = None, db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    user_id = verify_token(token)

    submission = db.query(Submission).filter(
        Submission.assignment_id == assignment_id,
        Submission.student_id == user_id
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="No submission found")

    grade = db.query(Grade).filter(Grade.submission_id == submission.id).first()

    return SubmissionWithGradeResponse(
        id=submission.id,
        assignment_id=submission.assignment_id,
        student_id=submission.student_id,
        submission_type=submission.submission_type,
        content=submission.content,
        status=submission.status,
        is_late=submission.is_late,
        submitted_at=submission.submitted_at,
        points_earned=float(grade.points_earned) if grade else None,
        feedback=grade.feedback if grade else None
    )

@router.post("/grades/create", response_model=GradeResponse)
def create_grade(request: GradeRequest, token: str = None, db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    grader_id = verify_token(token)

    submission = db.query(Submission).filter(Submission.id == request.submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    assignment = db.query(Assignment).filter(Assignment.id == submission.assignment_id).first()
    require_course_teacher(db, assignment.course_id, grader_id)

    percentage_earned = round((request.points_earned / float(assignment.points_possible)) * 100, 2)

    existing_grade = db.query(Grade).filter(Grade.submission_id == request.submission_id).first()
    now = datetime.utcnow()
    if existing_grade:
        existing_grade.points_earned = request.points_earned
        existing_grade.percentage_earned = percentage_earned
        existing_grade.feedback = request.feedback
        existing_grade.grader_id = grader_id
        existing_grade.graded_at = now
        existing_grade.updated_at = now
        db.commit()
        db.refresh(existing_grade)
        result = existing_grade
    else:
        result = Grade(
            submission_id=request.submission_id,
            points_earned=request.points_earned,
            percentage_earned=percentage_earned,
            feedback=request.feedback,
            grader_id=grader_id,
            graded_at=now
        )
        db.add(result)
        db.commit()
        db.refresh(result)

    submission.status = "graded"
    db.commit()

    assignment_for_course = db.query(Assignment).filter(Assignment.id == submission.assignment_id).first()
    recalculate_course_progress(db, assignment_for_course.course_id, submission.student_id)
# Gamification — bonus points for good grades
    from app.gamification import award_points, check_and_award_badges
    if percentage_earned >= 70:
        bonus = 50 if percentage_earned == 100 else 30 if percentage_earned >= 80 else 15
        award_points(db, submission.student_id, assignment_for_course.course_id, bonus, f'grade_bonus_{int(percentage_earned)}')
    check_and_award_badges(db, submission.student_id, assignment_for_course.course_id, 'grade')

    return result