from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class QuestionType(str, Enum):
    multiple_choice = "multiple-choice"
    true_false = "true-false"
    open_ended = "open-ended"
    mixed = "mixed"


# ── Quiz ────────────────────────────────────────────

class QuizConfig(BaseModel):
    topic: str
    difficulty: Difficulty
    count: int = 5
    type: QuestionType
    time_limit: Optional[int] = None        # seconds, None = no timer


class Question(BaseModel):
    id: int
    question: str
    type: QuestionType
    options: Optional[List[str]] = None     # None for open-ended
    correct_answers: List[int] = []         # list supports multi-answer
    sample_answer: Optional[str] = None     # open-ended only
    explanation: str
    is_multi: bool = False                  # True if multiple correct answers


# ── Answers & Results ───────────────────────────────

class AnswerRecord(BaseModel):
    question: str
    type: str
    user_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str


class QuizResult(BaseModel):
    topic: str
    difficulty: str
    type: str
    score: int
    total: int
    percentage: int
    time_taken: Optional[int] = None        # seconds
    answers: List[AnswerRecord]


# ── Auth ────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    username: str


# ── Share ───────────────────────────────────────────

class ShareConfig(BaseModel):
    topic: str
    difficulty: str
    count: int
    type: str
    time_limit: Optional[int] = None