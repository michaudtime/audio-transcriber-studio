@echo off
REM WhisperX Transcription with Diarization
REM Drag and drop an audio/video file onto this bat to transcribe it
REM Optional: drag with a 2nd argument for number of speakers

call :main %*
echo.
echo ============================================
echo Press any key to close this window...
echo ============================================
pause > nul
exit /b

:main
setlocal

set SCRIPT_DIR=%~dp0
if exist "%SCRIPT_DIR%config.bat" (
    call "%SCRIPT_DIR%config.bat"
) else (
    echo ERROR: config.bat not found. Copy config.bat.example to config.bat and fill in your values.
    exit /b 1
)
if defined FFMPEG_BIN set PATH=%FFMPEG_BIN%;%PATH%

echo ============================================
echo  WhisperX Transcriber
echo ============================================
echo.

if "%~1"=="" (
    echo ERROR: No file provided.
    echo.
    echo Usage: Drag and drop an audio/video file onto this bat file.
    echo        Or run: transcribe.bat "C:\path\to\audio.mp3"
    echo        Or run: transcribe.bat "C:\path\to\audio.mp3" 2   (for 2 speakers)
    endlocal
    exit /b 1
)

echo Input file : %~1
echo Output dir : %~dp1
echo.

set INPUT_FILE=%~1
set NUM_SPEAKERS=%~2

if "%NUM_SPEAKERS%"=="" (
    echo Auto-detecting number of speakers...
    echo.
    "%SCRIPT_DIR%.venv\Scripts\python.exe" -m whisperx "%INPUT_FILE%" ^
        --model large-v3-turbo ^
        --device cuda ^
        --compute_type float16 ^
        --diarize ^
        --hf_token %HF_TOKEN% ^
        --output_dir "%~dp1" ^
        --output_format all
) else (
    echo Using fixed speaker count: %NUM_SPEAKERS%
    echo.
    "%SCRIPT_DIR%.venv\Scripts\python.exe" -m whisperx "%INPUT_FILE%" ^
        --model large-v3-turbo ^
        --device cuda ^
        --compute_type float16 ^
        --diarize ^
        --min_speakers %NUM_SPEAKERS% ^
        --max_speakers %NUM_SPEAKERS% ^
        --hf_token %HF_TOKEN% ^
        --output_dir "%~dp1" ^
        --output_format all
)

set EXIT_CODE=%ERRORLEVEL%
echo.
if %EXIT_CODE% NEQ 0 (
    echo ERROR: WhisperX failed with exit code %EXIT_CODE%
) else (
    echo SUCCESS! Output files saved to: %~dp1
)

endlocal
exit /b %EXIT_CODE%
