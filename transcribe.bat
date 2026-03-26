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
    endlocal
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

REM ── Read current model ────────────────────────────────────────────────────────
for /f %%M in ('"%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%get_model.py"') do set SELECTED_MODEL=%%M

REM ── Model selection menu ──────────────────────────────────────────────────────
echo   Select model:
if "%SELECTED_MODEL%"=="large-v3-turbo" (
    echo     1^) Fast   -- large-v3-turbo  ^(recommended^)  [current]
) else (
    echo     1^) Fast   -- large-v3-turbo  ^(recommended^)
)
if "%SELECTED_MODEL%"=="large-v3" (
    echo     2^) Best   -- large-v3         ^(max accuracy^)  [current]
) else (
    echo     2^) Best   -- large-v3         ^(max accuracy^)
)
if "%SELECTED_MODEL%"=="medium" (
    echo     3^) Light  -- medium            ^(low-end hardware^)  [current]
) else (
    echo     3^) Light  -- medium            ^(low-end hardware^)
)
echo.

set CHOICE_ATTEMPT=0
:prompt_model
set MODEL_CHOICE=
set /p MODEL_CHOICE=  Enter 1-3 (or press Enter to keep current):

if "%MODEL_CHOICE%"==""      goto :model_selected
if "%MODEL_CHOICE%"=="1" ( set SELECTED_MODEL=large-v3-turbo & goto :save_model )
if "%MODEL_CHOICE%"=="2" ( set SELECTED_MODEL=large-v3       & goto :save_model )
if "%MODEL_CHOICE%"=="3" ( set SELECTED_MODEL=medium         & goto :save_model )

set /a CHOICE_ATTEMPT+=1
if %CHOICE_ATTEMPT% EQU 1 goto :prompt_model
echo   Invalid input. Using current model: %SELECTED_MODEL%
goto :model_selected

:save_model
"%SCRIPT_DIR%.venv\Scripts\python.exe" -c "from settings import load_settings, save_settings; s=load_settings(); s['model']='%SELECTED_MODEL%'; save_settings(s)"

:model_selected
echo.
echo Input file : %~1
echo Output dir : %~dp1
echo Model      : %SELECTED_MODEL%
echo.

set INPUT_FILE=%~1
set NUM_SPEAKERS=%~2

if "%NUM_SPEAKERS%"=="" (
    echo Auto-detecting number of speakers...
    echo.
    "%SCRIPT_DIR%.venv\Scripts\python.exe" -m whisperx "%INPUT_FILE%" ^
        --model %SELECTED_MODEL% ^
        --device cuda ^
        --compute_type float16 ^
        --diarize ^
        --output_dir "%~dp1" ^
        --output_format txt
) else (
    echo Using fixed speaker count: %NUM_SPEAKERS%
    echo.
    "%SCRIPT_DIR%.venv\Scripts\python.exe" -m whisperx "%INPUT_FILE%" ^
        --model %SELECTED_MODEL% ^
        --device cuda ^
        --compute_type float16 ^
        --diarize ^
        --min_speakers %NUM_SPEAKERS% ^
        --max_speakers %NUM_SPEAKERS% ^
        --output_dir "%~dp1" ^
        --output_format txt
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
