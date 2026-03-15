from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from routers import auth, quiz, history, analytics

app = FastAPI(title="QuizGen", version="1.0.0")

# ── Routers ──────────────────────────────────────────
app.include_router(auth.router)
app.include_router(quiz.router)
app.include_router(history.router)
app.include_router(analytics.router)

# ── Static files (frontend) ──────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_frontend():
    """Serve the main HTML page for all non-API routes."""
    return FileResponse("static/index.html")


# ── Run directly with: uvicorn main:app --reload ─────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)