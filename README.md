# QuizGen — Python / FastAPI

AI-powered quiz generator with document upload, history, analytics, and export.

## Setup

```bash
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY and a random JWT_SECRET

# 4. Run the server
uvicorn main:app --reload
```

Open http://localhost:8000

## Document format (for From Document mode)

### .docx files
- Plain text = question or wrong answer
- **Bold text** = correct answer
- Multiple bold answers on consecutive lines = multi-answer question

### .pdf files
- Plain text = question or wrong answer
- `**text**` = correct answer (wrap in double asterisks)
- `*text*` = correct answer (wrap in single asterisks)

## Project structure

```
main.py                  FastAPI app, mounts routers + static files
requirements.txt         Python dependencies
.env                     API key + JWT secret

routers/
  auth.py                /auth/register, /auth/login, /auth/me
  quiz.py                /quiz/generate, /quiz/from-document, /quiz/share/{token}
  history.py             /history/ CRUD + export endpoints
  analytics.py           /analytics/ summary, scores, topics, weak-topics

services/
  claude.py              Builds prompts, calls Anthropic API, parses response
  document.py            Parses .docx and .pdf files into question objects
  history.py             Reads/writes history.json
  auth.py                JWT tokens, password hashing, user management
  analytics.py           Computes stats from history records
  export.py              Generates PDF and DOCX result summaries
  share.py               Encodes/decodes quiz config as base64 URL token

models/
  schemas.py             Pydantic models for all request/response shapes

static/
  index.html             Single-page app HTML
  style.css              All styles
  app.js                 All frontend logic
```