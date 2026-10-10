@echo off
cd /d "%~dp0"
echo.
echo   S.I.M.O.N.  ::  installing
echo.
python -m venv .venv || goto :error
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install -r requirements.txt || goto :error
echo.
where ollama >nul 2>nul && ollama pull gemma4:e4b-it-qat
echo.
echo   Done. Double-click "Start Simon.bat" to launch.
pause
exit /b 0

:error
echo.
echo   Installation failed. Make sure Python 3.10+ is installed and on PATH.
pause
exit /b 1
