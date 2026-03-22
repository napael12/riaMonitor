@echo off
echo ========================================
echo  RIA Monitor — First-time Setup
echo ========================================
echo.
echo Prerequisites:
echo   - Python 3.11+  (python --version)
echo   - Node.js 20+   (node --version)
echo   - PostgreSQL 16+ running locally
echo.

echo [1/4] Installing Python ETL dependencies...
cd /d %~dp0etl
pip install -r requirements.txt
if errorlevel 1 ( echo ERROR: pip install failed & pause & exit /b 1 )

echo.
echo [2/4] Installing Python API dependencies...
cd /d %~dp0api
pip install -r requirements.txt
if errorlevel 1 ( echo ERROR: pip install failed & pause & exit /b 1 )

echo.
echo [3/4] Installing frontend Node dependencies...
cd /d %~dp0frontend
npm install
if errorlevel 1 ( echo ERROR: npm install failed & pause & exit /b 1 )

echo.
echo [4/4] Initialising database (requires postgres superuser password)...
cd /d %~dp0
call db\setup.bat
if errorlevel 1 ( echo WARNING: Database setup may have failed. Check output above. )

echo.
echo Setup complete!
echo.
echo Next steps:
echo   1. Copy .env.example to .env  (already configured for local PostgreSQL)
echo   2. Run launch.bat to start the API and frontend
echo   3. Run ETL manually:  cd etl ^& python pipeline.py
echo.
pause
