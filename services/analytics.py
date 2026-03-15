from services.history import load_history
from collections import defaultdict


def get_summary(user_id: str) -> dict:
    """
    Overall stats for a user:
    - total quizzes taken
    - average score percentage
    - best topic (highest avg score)
    - worst topic (lowest avg score)
    """
    records = load_history(user_id)
    if not records:
        return {"total": 0, "avg_score": 0, "best_topic": None, "worst_topic": None}

    total = len(records)
    avg_score = round(sum(r["percentage"] for r in records) / total)

    topic_scores = defaultdict(list)
    for r in records:
        topic_scores[r["topic"]].append(r["percentage"])

    topic_avgs = {t: round(sum(s) / len(s)) for t, s in topic_scores.items()}
    best_topic  = max(topic_avgs, key=topic_avgs.get) if topic_avgs else None
    worst_topic = min(topic_avgs, key=topic_avgs.get) if topic_avgs else None

    return {
        "total": total,
        "avg_score": avg_score,
        "best_topic": best_topic,
        "worst_topic": worst_topic,
    }


def get_score_over_time(user_id: str) -> list:
    """
    Returns list of {date, percentage} sorted by date.
    Used to draw a line chart of progress over time.
    """
    records = load_history(user_id)
    return [
        {"date": r["date"][:10], "percentage": r["percentage"], "topic": r["topic"]}
        for r in reversed(records)   # oldest first for chart
    ]


def get_topic_breakdown(user_id: str) -> list:
    """
    Returns list of {topic, avg_score, count} for bar chart.
    """
    records = load_history(user_id)
    topic_data = defaultdict(list)
    for r in records:
        topic_data[r["topic"]].append(r["percentage"])

    return [
        {
            "topic": topic,
            "avg_score": round(sum(scores) / len(scores)),
            "count": len(scores),
        }
        for topic, scores in topic_data.items()
    ]


def get_weak_topics(user_id: str) -> list:
    """
    Returns topics where average score is below 60%.
    """
    breakdown = get_topic_breakdown(user_id)
    return [t for t in breakdown if t["avg_score"] < 60]