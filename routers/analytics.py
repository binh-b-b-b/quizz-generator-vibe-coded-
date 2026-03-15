from fastapi import APIRouter, Depends
from services.analytics import get_summary, get_score_over_time, get_topic_breakdown, get_weak_topics
from services.auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def summary(user=Depends(get_current_user)):
    """Overall stats: total quizzes, avg score, best/worst topic."""
    return get_summary(user["id"])


@router.get("/scores")
def scores(user=Depends(get_current_user)):
    """Score history over time — used for line chart."""
    return get_score_over_time(user["id"])


@router.get("/topics")
def topics(user=Depends(get_current_user)):
    """Per-topic average scores — used for bar chart."""
    return get_topic_breakdown(user["id"])


@router.get("/weak-topics")
def weak_topics(user=Depends(get_current_user)):
    """Topics where average score is below 60%."""
    return get_weak_topics(user["id"])