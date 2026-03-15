import fitz                          # pymupdf
from docx import Document
from docx.oxml.ns import qn
from models.schemas import Question, QuestionType
from io import BytesIO


def extract_bold_runs(paragraph) -> list[str]:
    """Return list of bold text runs in a paragraph."""
    return [run.text for run in paragraph.runs if run.bold and run.text.strip()]


def extract_italic_runs(paragraph) -> list[str]:
    """Return list of italic text runs in a paragraph."""
    return [run.text for run in paragraph.runs if run.italic and run.text.strip()]


def is_answer_paragraph(paragraph) -> tuple[bool, list[str]]:
    """
    Check if a paragraph contains formatted (bold/italic) answer text.
    Returns (is_answer, list_of_answer_texts)
    """
    bold = extract_bold_runs(paragraph)
    italic = extract_italic_runs(paragraph)
    answers = bold or italic
    return bool(answers), answers


def build_questions_from_paragraphs(paragraphs: list) -> list[Question]:
    """
    Parse paragraphs into Question objects.

    Expected document format:
        Question text (plain)
        Wrong option (plain)
        Correct option (bold or italic)     ← single answer
        Another correct option (bold)       ← makes it multi-answer

    Logic:
        - Walk through paragraphs
        - When we hit a plain paragraph after collecting options = new question starts
        - Bold/italic paragraphs in the options block = correct answers
        - Plain paragraphs in the options block = wrong answers
    """
    questions = []
    current_question = None
    current_options = []
    current_correct_indices = []

    def flush():
        """Save current question if we have one."""
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

    for para in paragraphs:
        text = para.text.strip()
        if not text:
            continue

        is_answer, answer_texts = is_answer_paragraph(para)

        if is_answer:
            # This is a correct answer option
            idx = len(current_options)
            current_options.append(answer_texts[0] if answer_texts else text)
            current_correct_indices.append(idx)
        else:
            # Plain text — either a question or a wrong answer option
            # Heuristic: if it ends with ? it's a question, otherwise it's an option
            if text.endswith("?") or (current_question is None and not current_options):
                flush()
                current_question = text
            else:
                current_options.append(text)

    flush()  # Save last question
    return questions


def parse_docx(file_bytes: bytes) -> list[Question]:
    """Parse a .docx file and extract questions."""
    doc = Document(BytesIO(file_bytes))
    return build_questions_from_paragraphs(doc.paragraphs)


def parse_pdf(file_bytes: bytes) -> list[Question]:
    """
    Parse a PDF file and extract questions.
    PDFs lose formatting info (bold/italic), so we use ** and * markers
    as a convention for correct answers in PDF documents.

    Convention:
        Plain text = question or wrong option
        **bold text** = correct answer
        *italic text* = correct answer
    """
    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    lines = []
    for page in pdf:
        text = page.get_text()
        for line in text.splitlines():
            lines.append(line.strip())

    # Build fake paragraph-like objects from lines
    class FakePara:
        def __init__(self, text, is_answer):
            self.text = text
            self._is_answer = is_answer
            self.runs = [self]
            self.bold = is_answer
            self.italic = False

    paras = []
    for line in lines:
        if not line:
            continue
        if line.startswith("**") and line.endswith("**"):
            paras.append(FakePara(line[2:-2], True))
        elif line.startswith("*") and line.endswith("*"):
            paras.append(FakePara(line[1:-1], True))
        else:
            paras.append(FakePara(line, False))

    return build_questions_from_paragraphs(paras)


def build_questions_from_doc(file_bytes: bytes, filename: str) -> list[Question]:
    """Entry point — detects file type and routes to correct parser."""
    if filename.endswith(".docx"):
        return parse_docx(file_bytes)
    elif filename.endswith(".pdf"):
        return parse_pdf(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {filename}")