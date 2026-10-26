@echo off
set "PATH=C:\src\flutter\bin;C:\src\mingit\cmd;%PATH%"
echo ========================================================
echo   Launching CAMPUS-EYE Cross-Platform Flutter App
echo ========================================================
if "%~1"=="" (
    flutter run -d edge
) else (
    flutter run %*
)
