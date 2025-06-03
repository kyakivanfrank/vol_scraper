@echo off
setlocal enabledelayedexpansion

:: === Settings ===
set "PROJECT_ROOT_DIR=%~dp0smart_vol_scraper"
set "ENV_DIR=%PROJECT_ROOT_DIR%\playwright_env"
set "SRC_DIR=%PROJECT_ROOT_DIR%\src"
set "ZIP_FILE=%TEMP%\vol_scraper.zip"
set "TEMP_EXTRACT_DIR=%TEMP%\vol_scraper_extract"

:: === Step 1: Create project root if missing ===
if not exist "%PROJECT_ROOT_DIR%" (
    echo Creating project root folder "%PROJECT_ROOT_DIR%"
    mkdir "%PROJECT_ROOT_DIR%"
) else (
    echo Project root folder exists.
)

:: === Step 2: Create virtual environment if missing ===
if not exist "%ENV_DIR%\Scripts\python.exe" (
    echo Creating Python virtual environment in "%ENV_DIR%"...
    python -m venv "%ENV_DIR%"
) else (
    echo Virtual environment already exists.
)

:: === Step 3: Activate virtual environment and install Playwright if missing ===
pushd "%PROJECT_ROOT_DIR%"
call "%ENV_DIR%\Scripts\activate.bat"

:: Check if Playwright installed
python -c "import playwright" 2>nul
if errorlevel 1 (
    echo Installing Playwright and dependencies...
    pip install -q playwright
    playwright install
) else (
    echo Playwright already installed.
)

:: === Step 4: Download & extract repo if src folder missing or empty ===
if exist "%SRC_DIR%\*" (
    echo Src folder exists and is not empty. Skipping download.
) else (
    echo Downloading vol_scraper repo ZIP...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/kyakivanfrank/vol_scraper/archive/refs/heads/main.zip' -OutFile '%ZIP_FILE%'"

    if exist "%TEMP_EXTRACT_DIR%" rmdir /s /q "%TEMP_EXTRACT_DIR%"
    mkdir "%TEMP_EXTRACT_DIR%"

    echo Extracting ZIP...
    powershell -Command "Expand-Archive -LiteralPath '%ZIP_FILE%' -DestinationPath '%TEMP_EXTRACT_DIR%' -Force"

    if not exist "%SRC_DIR%" mkdir "%SRC_DIR%"

    for /d %%D in ("%TEMP_EXTRACT_DIR%\*") do (
        echo Moving repo files to src folder...
        move "%%D\*" "%SRC_DIR%\"
    )

    rmdir /s /q "%TEMP_EXTRACT_DIR%"
    del "%ZIP_FILE%"

    echo Repo downloaded and extracted to src folder.
)

:: === Step 5: Run the python script ===
echo Running playwright_scraper.py...
python "%SRC_DIR%\playwright_scraper.py"

:: === Cleanup ===
popd
deactivate

echo Done.
pause
endlocal
