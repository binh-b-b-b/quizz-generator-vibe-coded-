import re
import fitz                          # pymupdf
from docx import Document
from models.schemas import Question, QuestionType
from io import BytesIO


# ── Helpers ───────────────────────────────────────────

def is_question_text(text: str) -> bool:
    """
    Nhận dạng đoạn văn là câu hỏi nếu:
    - Bắt đầu bằng "Câu X." hoặc "Question X."
    - Hoặc bắt đầu bằng số thứ tự "1.", "2."
    - Hoặc kết thúc bằng "?"
    """
    t = text.lower().strip()
    patterns = [
        r"^câu\s*\d+",           # Câu 1, Câu 2...
        r"^question\s*\d+",      # Question 1, Question 2...
        r"^\d+[\.\)]\s+\S",      # 1. text hoặc 1) text
        r"\?$",                   # kết thúc bằng ?
    ]
    return any(re.search(p, t) for p in patterns)


def split_paragraph_into_virtual(para) -> list:
    full_text = para.text.strip()
    if not full_text:
        return []

    # QUAN TRỌNG: Kiểm tra toàn bộ paragraph trước
    # Nếu cả đoạn là câu hỏi → trả về 1 entry duy nhất, bỏ qua bold bên trong
    # Điều này fix lỗi khi câu hỏi có chữ in đậm bên trong như:
    # "Câu 24: Trong C, tên mảng M được hiểu là gì?"
    if is_question_text(full_text):
        return [{'text': full_text, 'bold': False, 'italic': False}]

    # Không phải câu hỏi → tách theo từng run
    result = []
    for run in para.runs:
        text = run.text.strip()
        if not text:
            continue
        result.append({
            'text': text,
            'bold': bool(run.bold),
            'italic': bool(run.italic),
        })

    if len(result) <= 1:
        return result

    # Kiểm tra xem có run nào là câu hỏi mới bị gộp vào không (bug cũ câu 5→6)
    has_question_run = any(is_question_text(r['text']) for r in result)
    if has_question_run:
        return result
    else:
        combined_text = " ".join(r['text'] for r in result)
        return [{'text': combined_text, 'bold': result[0]['bold'], 'italic': result[0]['italic']}]


def build_questions_from_virtual(virtuals: list) -> list:
    """
    Nhận list các virtual paragraphs (dict với text/bold/italic)
    và xây dựng danh sách Question.

    Logic:
    - is_question_text(text) = True → câu hỏi mới
    - bold hoặc italic → đáp án đúng
    - còn lại → đáp án sai
    """
    questions = []
    current_question = None
    current_options = []
    current_correct_indices = []

    def flush():
        nonlocal current_question, current_options, current_correct_indices
        if current_question and current_options:
            is_multi = len(current_correct_indices) > 1
            questions.append(Question(
                id=len(questions),
                question=current_question,
                type=QuestionType.multiple_choice,
                options=current_options[:],
                correct_answers=current_correct_indices[:],
                is_multi=is_multi,
                explanation="",
            ))
        current_question = None
        current_options = []
        current_correct_indices = []

    for v in virtuals:
        text = v['text']
        is_bold   = v['bold']
        is_italic = v['italic']

        if not text:
            continue

        if is_question_text(text):
            # Câu hỏi mới — lưu câu cũ trước
            flush()
            current_question = text

        elif (is_bold or is_italic) and current_question is not None:
            # Đáp án đúng
            idx = len(current_options)
            current_options.append(text)
            current_correct_indices.append(idx)

        elif current_question is not None:
            # Đáp án sai
            current_options.append(text)

        # Nếu current_question là None và không phải câu hỏi → bỏ qua (text rác)

    flush()
    return questions


# ── DOCX parser ───────────────────────────────────────

def parse_docx(file_bytes: bytes) -> list:
    doc = Document(BytesIO(file_bytes))

    virtuals = []
    for para in doc.paragraphs:
        if not para.text.strip():
            continue
        virtuals.extend(split_paragraph_into_virtual(para))

    return build_questions_from_virtual(virtuals)


# ── PDF parser ────────────────────────────────────────

def parse_pdf(file_bytes: bytes) -> list:
    """
    PDF mất thông tin bold/italic nên dùng ký hiệu:
    **text** = đáp án đúng
    *text*   = đáp án đúng
    """
    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    virtuals = []

    for page in pdf:
        for line in page.get_text().splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("**") and line.endswith("**"):
                virtuals.append({'text': line[2:-2], 'bold': True, 'italic': False})
            elif line.startswith("*") and line.endswith("*"):
                virtuals.append({'text': line[1:-1], 'bold': False, 'italic': True})
            else:
                virtuals.append({'text': line, 'bold': False, 'italic': False})

    return build_questions_from_virtual(virtuals)


# ── Entry point ───────────────────────────────────────

def build_questions_from_doc(file_bytes: bytes, filename: str) -> list:
    if filename.endswith(".docx"):
        return parse_docx(file_bytes)
    elif filename.endswith(".pdf"):
        return parse_pdf(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {filename}")