@echo off
title Procurement Pro Launcher
echo ==========================================
echo   URUCHAMIANIE SYSTEMU PROCUREMENT PRO
echo ==========================================

:: 1. Uruchom Backend w nowym oknie
echo [1/3] Startowanie Backendu (FastAPI)...
start "Backend - Procurement Pro" cmd /k "python -m uvicorn app.main:app --reload"

:: 2. Uruchom Frontend w nowym oknie
echo [2/3] Startowanie Frontendu (React)...
start "Frontend - Procurement Pro" cmd /k "cd frontend && npm run dev"

:: 3. Otwórz przeglądarkę (czekamy chwilę, aż serwery wstaną)
echo [3/3] Otwieranie przegladarki...
timeout /t 5 >nul
start http://localhost:5173

echo.
echo SUKCES! Aplikacja powinna byc gotowa.
echo Mozesz zamknac to okno (serwery dzialaja w tle).
pause