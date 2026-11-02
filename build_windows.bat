@echo off
REM ============================================================
REM  PrintView3D - build the Windows program (PrintView3D.exe)
REM  Requires Python 3.12-3.14 from python.org (3.12 recommended).
REM  Result: dist\PrintView3D\PrintView3D.exe
REM ============================================================
setlocal
cd /d "%~dp0"

REM Pick a supported Python explicitly instead of whatever is newest on this PC.
REM 3.12 is the oldest: the exact library versions the releases are built with
REM (requirements-build-lock.txt, e.g. NumPy 2.5) need it. 3.14 is the newest:
REM the 3D engine (VTK) has no version for 3.15 yet.
set "PY="
for %%V in (3.12 3.13 3.14) do (
    if not defined PY (
        py -%%V -c "import sys" >nul 2>nul && set "PY=py -%%V"
    )
)
if not defined PY (
    echo [ERROR] No supported Python version was found.
    echo         Building PrintView3D needs Python 3.12 to 3.14 ^(3.12 recommended^).
    echo         Older versions such as 3.11 are too old for the libraries it is built with,
    echo         newer versions such as 3.15 are not supported yet by the VTK 3D engine.
    echo         Install Python 3.12 from https://www.python.org/downloads/
    echo         It can be installed next to your existing Python - both keep working.
    pause
    exit /b 1
)
echo Using Python: %PY%

echo [1/4] Creating virtual environment (.venv) ...
REM A .venv made earlier by an unsupported Python (or one that was uninstalled since)
REM would make step 2 fail, so make a new one.
if exist ".venv" (
    ".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if (3,12) <= sys.version_info[:2] <= (3,14) else 1)" >nul 2>nul
    if errorlevel 1 (
        echo       The existing .venv uses an unsupported Python - making a new one.
        rmdir /s /q ".venv"
        if exist ".venv" (
            echo [ERROR] Could not delete the old .venv folder. Close programs using it and try again.
            goto :fail
        )
    )
)
if not exist ".venv\Scripts\python.exe" (
    %PY% -m venv .venv || goto :fail
)

echo [2/4] Installing dependencies (first time takes a few minutes) ...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt -r requirements-build.txt -c requirements-build-lock.txt || goto :fail

echo [3/4] Building translations and running tests ...
".venv\Scripts\python.exe" tools\i18n.py compile || goto :fail
".venv\Scripts\python.exe" tests\make_samples.py >nul
".venv\Scripts\python.exe" -m pytest -q tests || goto :fail

echo [4/4] Building PrintView3D.exe ...
".venv\Scripts\pyinstaller.exe" --noconfirm --clean printview3d.spec || goto :fail

REM Optional: the installer, if Inno Setup 6 is installed (https://jrsoftware.org/isinfo.php)
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" goto :noinstaller
for /f "tokens=2 delims==" %%v in ('findstr /b "__version__" src\printview3d\__init__.py') do set "APPVER=%%~v"
set "APPVER=%APPVER: =%"
set "APPVER=%APPVER:"=%"
echo [+] Building the File Explorer thumbnails (needs Visual Studio C++ Build Tools) ...
pushd packaging\windows\thumbnails
call build.bat %APPVER%
if errorlevel 1 ( popd & echo Thumbnails need the Visual Studio C++ Build Tools; installer skipped. & goto :noinstaller )
popd
echo [+] Building the installer ...
"%ISCC%" /Q "/DAppVersion=%APPVER%" packaging\windows\PrintView3D.iss || goto :fail
:noinstaller

echo.
echo ============================================================
echo  Done!  dist\PrintView3D\PrintView3D.exe
if exist "dist\PrintView3D-Setup.exe" echo  Installer: dist\PrintView3D-Setup.exe
echo  Run install_windows.bat (or the installer) to install it for your user account.
echo ============================================================
pause
exit /b 0

:fail
echo.
echo [ERROR] Build failed - see the messages above.
pause
exit /b 1
