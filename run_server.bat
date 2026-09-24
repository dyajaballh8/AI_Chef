@echo off
echo ===================================================
echo Starting Chef AI Assistant 🍳
echo ===================================================
cd backend
python -m uvicorn app.main:app --reload --port 8001
pause
