@echo off
rem Explainer Studio: the review page and the editing page (http://localhost:8770).
rem Double-click to start, keep the window open while you review, close it when you are done.
rem Optional: open-review-pages.bat <port>
rem
rem Which Python: the studio's own .venv when it starts from a double-click. A .venv made from inside the Claude
rem desktop app can point at a Python that only Claude can see (part of AppData is hidden from other programs);
rem then a plain Python 3.12 (py -3.12, or python on PATH) runs the pages with the .venv's packages added.
setlocal
chcp 65001 >nul
set "STUDIO=%~dp0"
if "%STUDIO:~-1%"=="\" set "STUDIO=%STUDIO:~0,-1%"
set "PORT=8770"
if not "%~1"=="" set "PORT=%~1"
set "PYTHONIOENCODING=utf-8"
title Explainer Studio pages - keep this window open

if not exist "%STUDIO%\scripts\gs_review.py" (
  echo This file must sit in the studio folder, next to scripts\ and studio.toml.
  goto stop
)
cd /d "%STUDIO%\scripts"

set "PY="
set "MODE=venv"
"%STUDIO%\.venv\Scripts\python.exe" -c "import sys" >nul 2>&1 && set "PY=%STUDIO%\.venv\Scripts\python.exe"
if defined PY goto run

set "MODE=plain"
py -3.12 -c "import sys" >nul 2>&1 && set "PY=py -3.12"
if defined PY goto run
python -c "import sys; sys.exit(sys.version_info[:2] != (3, 12))" >nul 2>&1 && set "PY=python"
if defined PY goto run

echo No Python that starts outside Claude was found.
echo Ask Claude: "the review pages launcher finds no Python" (setup can install a plain Python 3.12 for it).
goto stop

:run
if not defined STUDIO_NO_BROWSER start "" /b cmd /c "timeout /t 4 >nul & start http://localhost:%PORT%"
if "%MODE%"=="venv" (
  "%PY%" gs_review.py %PORT%
) else (
  set "PYTHONPATH=%STUDIO%\.venv\Lib\site-packages"
  %PY% -c "import os, runpy, site, sys; s = os.environ['STUDIO']; site.addsitedir(os.path.join(s, '.venv', 'Lib', 'site-packages')); sys.path.insert(0, os.path.join(s, 'scripts')); sys.argv = [os.path.join(s, 'scripts', 'gs_review.py'), os.environ['PORT']]; runpy.run_path(sys.argv[0], run_name='__main__')"
)

:stop
echo.
echo The pages have stopped. If there is an error above, copy it to Claude. Press any key to close.
pause >nul
