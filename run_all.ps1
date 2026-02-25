# Run camera server, irrigation API, and dashboard in separate windows
Param(
  [string]$Python = "python",
  [string]$ProjectRoot = "$PSScriptRoot\.."
)

Set-Location $ProjectRoot

# If a local YOLOv8 .pt exists, export II_YOLO_WEIGHTS so irrigation_api uses it
$yolopt = Join-Path $ProjectRoot "models" "yolov8n.pt"
if (Test-Path $yolopt) {
  $env:II_YOLO_WEIGHTS = (Resolve-Path $yolopt)
  Write-Host "II_YOLO_WEIGHTS=$($env:II_YOLO_WEIGHTS)"
} else {
  Write-Host "Warning: models\\yolov8n.pt not found. irrigation_api will use HSV fallback." -ForegroundColor Yellow
}

Write-Host "Starting camera_server.py ..."
Start-Process -FilePath $Python -ArgumentList "camera_server.py" -WorkingDirectory $ProjectRoot -WindowStyle Minimized

Start-Sleep -Seconds 1

Write-Host "Starting irrigation_api.py ..."
Start-Process -FilePath $Python -ArgumentList "irrigation_api.py" -WorkingDirectory $ProjectRoot -WindowStyle Minimized

Start-Sleep -Seconds 1

Write-Host "Starting ingenious_irrigation_dashboard.py ..."
Start-Process -FilePath $Python -ArgumentList "ingenious_irrigation_dashboard.py" -WorkingDirectory $ProjectRoot -WindowStyle Minimized

Write-Host "All services launched."
