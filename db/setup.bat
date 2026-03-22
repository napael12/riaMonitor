@echo off
SET PSQL="C:\Program Files\PostgreSQL\18\bin\psql.exe"
SET PGHOST=127.0.0.1
SET PGPORT=5432
SET PGUSER=postgres

SET /P PGPASSWORD="Enter postgres superuser password: "
SET PGPASSWORD=%PGPASSWORD%

echo.
echo [1/2] Creating user, database, and granting permissions...
%PSQL% -h %PGHOST% -p %PGPORT% -U %PGUSER% -f "%~dp0setup.sql"
IF ERRORLEVEL 1 (
  echo ERROR: setup.sql failed.
  pause
  exit /b 1
)

echo.
echo [2/2] Installing schema (tables and indexes)...
%PSQL% -h %PGHOST% -p %PGPORT% -U ria -d ria -f "%~dp0init.sql"
IF ERRORLEVEL 1 (
  echo ERROR: init.sql failed.
  pause
  exit /b 1
)

echo.
echo Database setup complete!
pause
