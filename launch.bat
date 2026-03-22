@echo off
echo ========================================
echo  RIA Monitor — Local Development Start
echo ========================================
echo.
echo Starting Python API on port 8000...
start "RIA API" cmd /k "cd /d %~dp0api && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo Starting React frontend on port 3000...
start "RIA Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Two windows opened:
echo   API:      http://localhost:8000
echo   Frontend: http://localhost:3000
echo.
pause
