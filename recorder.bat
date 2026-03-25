@echo off
REM WhisperX Recorder — GUI microphone recorder with auto-transcription

call :main
pause
exit /b

:main
setlocal

set SCRIPT_DIR=%~dp0

if exist "%SCRIPT_DIR%config.bat" (
    call "%SCRIPT_DIR%config.bat"
) else (
    echo ERROR: config.bat not found. Copy config.bat.example to config.bat and fill in your values.
    endlocal
    exit /b 1
)

if not exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found at .venv\Scripts\python.exe
    echo Run setup to install dependencies first.
    endlocal
    exit /b 1
)

if defined FFMPEG_BIN set PATH=%FFMPEG_BIN%;%PATH%

"%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%recorder.py"

endlocal
exit /b %ERRORLEVEL%
