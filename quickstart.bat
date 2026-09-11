@echo off
REM NEXUS-R Quick Start Script for Windows

echo.
echo 🚀 NEXUS-R Quick Start
echo =======================
echo.

echo Checking prerequisites...

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Python not found. Please install Python 3.11+
    exit /b 1
)

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Node.js not found. Please install Node.js 18+
    exit /b 1
)

where psql >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ PostgreSQL not found. Please install PostgreSQL 14+
    exit /b 1
)

echo ✅ Prerequisites check passed
echo.

REM Backend setup
echo 📦 Setting up backend...
cd backend

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -q -r requirements.txt

if not exist ".env" (
    echo Creating .env file...
    copy .env.example .env
    echo ⚠️  Please edit backend\.env with your credentials and API keys
    pause
)

echo Running migrations...
alembic upgrade head

echo Seeding demo data...
python scripts\seed_demo_data.py

echo ✅ Backend setup complete
cd ..

REM Frontend setup
echo.
echo 📦 Setting up frontend...
cd frontend

if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
)

if not exist ".env.local" (
    copy .env.local.example .env.local
)

echo ✅ Frontend setup complete
cd ..

echo.
echo 🎉 Setup complete!
echo.
echo To start the application:
echo.
echo Terminal 1 (Backend):
echo   cd backend
echo   venv\Scripts\activate
echo   uvicorn app.main:app --reload
echo.
echo Terminal 2 (Frontend):
echo   cd frontend
echo   npm run dev
echo.
echo Then open http://localhost:3000
echo.
pause
