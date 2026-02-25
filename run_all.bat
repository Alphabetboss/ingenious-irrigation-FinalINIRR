@echo off
setlocal enableextensions

REM Run camera server, irrigation API, and dashboard in separate windows

REM Project root is the parent of this script directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
pushd "%PROJECT_ROOT%"

REM If a local YOLOv8 .pt exists, export II_YOLO_WEIGHTS so irrigation_api uses it
if exist "models\yolov8n.pt" (
  set "II_YOLO_WEIGHTS=%CD%\models\yolov8n.pt"
  echo II_YOLO_WEIGHTS=%II_YOLO_WEIGHTS%
) else (
  echo Warning: models\yolov8n.pt not found. irrigation_api will use HSV fallback.
)

echo Starting camera_server.py ...
start "camera_server" /MIN cmd /c python camera_server.py

timeout /t 1 >nul 2>&1

echo Starting irrigation_api.py ...
start "irrigation_api" /MIN cmd /c python irrigation_api.py

timeout /t 1 >nul 2>&1

echo Starting ingenious_irrigation_dashboard.py ...
start "dashboard" /MIN cmd /c python ingenious_irrigation_dashboard.py

echo All services launched.
popd
endlocal
exit /b 0
