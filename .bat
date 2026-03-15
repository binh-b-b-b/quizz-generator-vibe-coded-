@echo off
cd /d D:\AAA\quizz_generator
call venv\Scripts\activate
start http://localhost:8000
uvicorn main:app