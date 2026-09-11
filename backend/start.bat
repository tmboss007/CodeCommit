@echo off
cd /d "C:\MIT Pune'\REACT\backend"
call venv\Scripts\activate.bat
python -m uvicorn app.main:app --reload
