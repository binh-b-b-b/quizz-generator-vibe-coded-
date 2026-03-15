import os
import json
import anthropic
from dotenv import load_dotenv
from models.schemas import Question, QuestionType

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def build_prompt(topic: str, difficulty: str, count: int, q_type: str) -> str:
    type_instructions = {
        "multiple-choice": f"All questions must be multiple-choice with exactly 4 options. correct_answers must be a list with one index (0-3).",
        "true-false":      f"All questions must be true/false. options must always be ['True', 'False']. correct_answers is a list with one index (0 or 1).",
        "open-ended":      f"All questions must be open-ended (no options). Include a sample_answer string. correct_answers must be an empty list [].",
        "mixed":           f"Mix multiple-choice (4 options), true/false (['True','False']), and open-ended (no options, has sample_answer). Roughly equal split.",
    }

    return f"""Generate exactly {count} quiz questions about "{topic}" at {difficulty} difficulty.

{type_instructions.get(q_type, type_instructions['mixed'])}

IMPORTANT: Some questions may have multiple correct answers. If a question has multiple correct answers:
- Set is_multi to true
- List ALL correct answer indices in correct_answers array
- This only applies to multiple-choice questions

Return ONLY a valid JSON array. No markdown, no explanation, no backticks.
Each object must have:
- "question": string
- "type": "multiple-choice" | "true-false" | "open-ended"
- "options": list of strings (omit for open-ended)
- "correct_answers": list of ints (empty list for open-ended)
- "is_multi": boolean (true if multiple correct answers)
- "sample_answer": string (open-ended only, omit otherwise)
- "explanation": string

Example multiple-choice single answer:
{{"question":"...","type":"multiple-choice","options":["A","B","C","D"],"correct_answers":[2],"is_multi":false,"explanation":"..."}}

Example multiple-choice multi answer:
{{"question":"...","type":"multiple-choice","options":["A","B","C","D"],"correct_answers":[0,2],"is_multi":true,"explanation":"..."}}

Example open-ended:
{{"question":"...","type":"open-ended","options":null,"correct_answers":[],"is_multi":false,"sample_answer":"...","explanation":"..."}}"""


def parse_response(text: str) -> list:
    clean = text.strip()
    # Strip markdown fences if Claude wraps in them
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1]
    if clean.endswith("```"):
        clean = clean.rsplit("```", 1)[0]
    return json.loads(clean.strip())


def generate_questions(topic: str, difficulty: str, count: int, q_type: str) -> list[Question]:
    prompt = build_prompt(topic, difficulty, count, q_type)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text
    data = parse_response(raw)

    questions = []
    for i, q in enumerate(data):
        questions.append(Question(
            id=i,
            question=q["question"],
            type=q["type"],
            options=q.get("options"),
            correct_answers=q.get("correct_answers", []),
            sample_answer=q.get("sample_answer"),
            explanation=q["explanation"],
            is_multi=q.get("is_multi", False),
        ))

    return questions