from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request
from models.schemas import QuizConfig, Question
from services.claude import generate_questions
from services.document import build_questions_from_doc
from services.share import decode_share_link
from services.auth import get_current_user

router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.post("/generate", response_model=list[Question])
def generate(config: QuizConfig, user=Depends(get_current_user)):
    """
    Generate quiz questions using Claude AI.
    Requires a valid JWT token (user must be logged in).
    """
    return generate_questions(
        topic=config.topic,
        difficulty=config.difficulty,
        count=config.count,
        q_type=config.type,
    )


@router.post("/from-document", response_model=list[Question])
async def from_document(file: UploadFile = File(...), user=Depends(get_current_user)):
    """
    Upload a .pdf or .docx file and extract questions from it.
    Bold or italic text in the document = correct answers.
    """
    if not file.filename.endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only .pdf and .docx files are supported")

    file_bytes = await file.read()
    questions = build_questions_from_doc(file_bytes, file.filename)

    if not questions:
        raise HTTPException(status_code=422, detail="No questions found in the document. Check your formatting.")

    return questions


@router.get("/share/{token}", response_model=dict)
def load_shared_quiz(token: str):
    """
    Decode a share token back into a quiz config.
    Called on page load if ?quiz= is in the URL.
    """
    try:
        config = decode_share_link(token)
        return config
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid or expired share link")