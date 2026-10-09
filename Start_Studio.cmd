@echo off
setlocal EnableExtensions
rem ===========================================================================
rem  Start the Claude video agent studio.
rem    1. ComfyUI: if nothing serves port 8188, start it with ComfyUI.bat (it activates its own venv)
rem       and wait until its API answers.
rem    2. Chrome: start it if it is not running (the Claude in Chrome extension must be signed in).
rem    3. Put http://127.0.0.1:8188 on the clipboard for the studio tab.
rem    4. DaVinci Resolve (optional, only needed for finishing): start it, then you open a STUDIO_ project
rem       and run Workspace > Scripts > resolve_bridge yourself.
rem    5. Start Claude Code in this folder as the Producer, with Chrome.
rem  The studio's own Python venv (.venv) needs no activation: the studio calls .venv\Scripts\python.exe.
rem  Run:  Start_Studio.cmd           (or double-click)
rem        Start_Studio.cmd /dryrun   (only shows what it would do)
rem  This file is for the user. The studio's guard hook blocks agents from running it.
rem ===========================================================================

set "REPO=%~dp0"
if "%REPO:~-1%"=="\" set "REPO=%REPO:~0,-1%"
set "COMFY_BAT=C:\Users\david\Desktop\ComfyUI.bat"
set "RESOLVE_EXE=C:\DavinciResolve\Resolve.exe"
set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"
set "STUDIO_URL=http://127.0.0.1:8188"
set "DRY="
if /i "%~1"=="/dryrun" set "DRY=1"

set "CLAUDE=claude"
where claude >nul 2>&1
if errorlevel 1 set "CLAUDE=%USERPROFILE%\.local\bin\claude.exe"

echo.
echo  Claude video agent studio  (%REPO%)
if defined DRY echo  DRY RUN: nothing will be started.
echo.

rem --- studio venv ------------------------------------------------------------
if exist "%REPO%\.venv\Scripts\python.exe" (
    echo [ok]   Studio venv found.
) else (
    echo [warn] Studio venv missing. Create it with:
    echo        "C:\Program Files\Python312\python.exe" -m venv "%REPO%\.venv"
    echo        "%REPO%\.venv\Scripts\python.exe" -m pip install -r "%REPO%\requirements.txt"
)

rem --- 1. ComfyUI ---------------------------------------------------------------
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8188 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
if not errorlevel 1 (
    echo [ok]   ComfyUI is already running on port 8188.
) else (
    if not exist "%COMFY_BAT%" (
        echo [warn] ComfyUI is not running and %COMFY_BAT% was not found.
    ) else if defined DRY (
        echo [dry]  Would start ComfyUI: explorer.exe "%COMFY_BAT%"  and wait up to 3 min for its API.
    ) else (
        echo [..]   Starting ComfyUI with ComfyUI.bat, waiting up to 3 minutes for its API ...
        explorer.exe "%COMFY_BAT%"
        powershell -NoProfile -Command "$d=(Get-Date).AddSeconds(180); while((Get-Date) -lt $d){ try { Invoke-RestMethod '%STUDIO_URL%/api/system_stats' -TimeoutSec 3 | Out-Null; exit 0 } catch { Start-Sleep 3 } }; exit 1"
        if errorlevel 1 (echo [warn] ComfyUI did not answer within 3 minutes; check its console window.) else (echo [ok]   ComfyUI answers.)
    )
)

rem --- 2. Chrome ----------------------------------------------------------------
tasklist /fi "imagename eq chrome.exe" 2>nul | find /i "chrome.exe" >nul
if not errorlevel 1 (
    echo [ok]   Chrome is running.
) else if defined DRY (
    echo [dry]  Would start Chrome: "%CHROME_EXE%"
) else (
    if exist "%CHROME_EXE%" (start "" "%CHROME_EXE%") else (start "" chrome)
    echo [ok]   Chrome started.
)

rem --- 3. Studio tab address on the clipboard -----------------------------------
if defined DRY (
    echo [dry]  Would copy %STUDIO_URL% to the clipboard.
) else (
    <nul set /p "=%STUDIO_URL%" | clip
    echo [ok]   %STUDIO_URL% is on the clipboard.
)

rem --- 4. DaVinci Resolve (optional) --------------------------------------------
set "WANT_RESOLVE=N"
if defined DRY (
    echo [dry]  Would ask whether to start DaVinci Resolve - default No after 10 s.
) else (
    choice /c YN /t 10 /d N /m "Start DaVinci Resolve too (only needed for finishing)"
    if not errorlevel 2 set "WANT_RESOLVE=Y"
)
if /i "%WANT_RESOLVE%"=="Y" (
    tasklist /fi "imagename eq Resolve.exe" 2>nul | find /i "Resolve.exe" >nul
    if not errorlevel 1 (
        echo [ok]   Resolve is already running.
    ) else (
        start "" "%RESOLVE_EXE%"
        echo [ok]   Resolve started.
    )
    echo        In Resolve: create or open a project named STUDIO_^<CODE^> - never an existing project -
    echo        then run Workspace ^> Scripts ^> resolve_bridge once.
)

rem --- 5. Claude Code as the Producer -------------------------------------------
echo.
echo  Studio tab: when the studio asks for it, click the new tab in Claude's tab group in Chrome,
echo  press Ctrl+L, Ctrl+V, Enter. Opening the address any other way doesn't work: ComfyUI refuses
echo  pages the extension opens, and the extension can only use tabs in its own group.
echo.
if defined DRY (
    echo [dry]  Would run in %REPO%:  "%CLAUDE%" --agent producer --chrome
    exit /b 0
)
cd /d "%REPO%"
"%CLAUDE%" --agent producer --chrome
endlocal
