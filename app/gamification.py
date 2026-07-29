from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from .models import UserPoints, Badge, UserBadge, LessonProgress, Submission, Grade, Enrollment, Streak

def award_points(db: Session, user_id: int, course_id: int, points: int, reason: str):
    """Award points to a student and save the record."""
    entry = UserPoints(
        user_id=user_id,
        course_id=course_id,
        points_earned=points,
        reason=reason,
        earned_at=datetime.utcnow()
    )
    db.add(entry)
    db.commit()

def get_total_points(db: Session, user_id: int) -> int:
    """Get total points across all courses."""
    result = db.query(UserPoints).filter(UserPoints.user_id == user_id).all()
    return sum(r.points_earned for r in result)

def award_badge_if_not_earned(db: Session, user_id: int, criteria: str):
    """Award a badge by criteria string if not already earned."""
    badge = db.query(Badge).filter(Badge.criteria == criteria).first()
    if not badge:
        return None

    already_earned = db.query(UserBadge).filter(
        UserBadge.user_id == user_id,
        UserBadge.badge_id == badge.id
    ).first()

    if already_earned:
        return None

    new_badge = UserBadge(
        user_id=user_id,
        badge_id=badge.id,
        earned_at=datetime.utcnow()
    )
    db.add(new_badge)
    db.commit()
    return badge

def update_streak(db: Session, user_id: int):
    """Update streak on activity. Returns current streak count."""
    today = date.today()

    streak = db.query(Streak).filter(Streak.user_id == user_id).first()

    if not streak:
        streak = Streak(
            user_id=user_id,
            current_streak=1,
            longest_streak=1,
            last_activity_date=today,
            updated_at=datetime.utcnow()
        )
        db.add(streak)
        db.commit()
        return 1

    if streak.last_activity_date == today:
        return streak.current_streak

    yesterday = today - timedelta(days=1)

    if streak.last_activity_date == yesterday:
        streak.current_streak += 1
    else:
        streak.current_streak = 1

    if streak.current_streak > streak.longest_streak:
        streak.longest_streak = streak.current_streak

    streak.last_activity_date = today
    streak.updated_at = datetime.utcnow()
    db.commit()
    return streak.current_streak

def check_and_award_badges(db: Session, user_id: int, course_id: int, trigger: str, db_session=None):
    """
    Check all badge criteria and award any newly earned badges.
    trigger: 'lesson_complete' | 'submission' | 'grade' | 'course_complete'
    Returns list of newly earned badges.
    """
    newly_earned = []

    if trigger == 'lesson_complete':
        completed = db.query(LessonProgress).filter(
            LessonProgress.student_id == user_id,
            LessonProgress.is_completed == True
        ).count()

        if completed == 1:
            b = award_badge_if_not_earned(db, user_id, 'first_lesson')
            if b: newly_earned.append(b)

        if completed >= 5:
            b = award_badge_if_not_earned(db, user_id, 'lessons_5')
            if b: newly_earned.append(b)

        if completed >= 10:
            b = award_badge_if_not_earned(db, user_id, 'lessons_10')
            if b: newly_earned.append(b)

    if trigger == 'submission':
        submissions = db.query(Submission).filter(
            Submission.student_id == user_id
        ).count()

        if submissions == 1:
            b = award_badge_if_not_earned(db, user_id, 'first_submission')
            if b: newly_earned.append(b)

    if trigger == 'grade':
        grade = db.query(Grade).join(Submission).filter(
            Submission.student_id == user_id
        ).order_by(Grade.graded_at.desc()).first()

        if grade:
            if float(grade.percentage_earned) == 100:
                b = award_badge_if_not_earned(db, user_id, 'perfect_score')
                if b: newly_earned.append(b)

            if float(grade.percentage_earned) >= 70:
                b = award_badge_if_not_earned(db, user_id, 'grade_a')
                if b: newly_earned.append(b)

    if trigger == 'course_complete':
        b = award_badge_if_not_earned(db, user_id, 'course_complete')
        if b: newly_earned.append(b)

    streak_count = update_streak(db, user_id)
    if streak_count >= 3:
        b = award_badge_if_not_earned(db, user_id, 'streak_3')
        if b: newly_earned.append(b)
    if streak_count >= 7:
        b = award_badge_if_not_earned(db, user_id, 'streak_7')
        if b: newly_earned.append(b)

    return newly_earned