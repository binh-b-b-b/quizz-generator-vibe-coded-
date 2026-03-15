from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from models.schemas import QuizResult
from services.history import save_result, load_history, delete_record, clear_history, get_record
from services.export import export_pdf, export_docx
from services.auth import get_current_user

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/")
def get_history(user=Depends(get_current_user)):
    """Return all quiz records for the logged-in user."""
    return load_history(user["id"])


@router.post("/save")
def save(result: QuizResult, user=Depends(get_current_user)):
    """Save a completed quiz result."""
    return save_result(result.model_dump(), user["id"])


@router.delete("/{record_id}")
def delete(record_id: str, user=Depends(get_current_user)):
    """Delete one quiz record by ID."""
    deleted = delete_record(record_id, user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"deleted": True}


@router.delete("/")
def clear(user=Depends(get_current_user)):
    """Delete all quiz records for the logged-in user."""
    clear_history(user["id"])
    return {"cleared": True}


@router.get("/{record_id}/export/pdf")
def export_as_pdf(record_id: str, user=Depends(get_current_user)):
    """Download a quiz result as a PDF file."""
    record = get_record(record_id, user["id"])
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    pdf_bytes = export_pdf(record)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=quiz_{record_id[:8]}.pdf"}
    )


@router.get("/{record_id}/export/docx")
def export_as_docx(record_id: str, user=Depends(get_current_user)):
    """Download a quiz result as a .docx file."""
    record = get_record(record_id, user["id"])
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    docx_bytes = export_docx(record)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=quiz_{record_id[:8]}.docx"}
    )