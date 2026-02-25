
# PowerShell Script to Merge YOLOv8 Dataset Structure
# Place this script inside: IngeniousIrrigation/health_detection/dataset

# Set base dataset folders
$base = "$PSScriptRoot"
$merged = "$base\Merged_Dataset"

# Create required directories if they don't exist
$sets = @("train", "val", "test")
foreach ($set in $sets) {
    New-Item -ItemType Directory -Path "$merged\images\$set" -Force | Out-Null
    New-Item -ItemType Directory -Path "$merged\labels\$set" -Force | Out-Null
}

# Define dataset folders to merge from
$datasets = @("Grass_Detection", "Water_Body_Detection", "Water_Leakage_Detection")

# Merge loop
foreach ($dataset in $datasets) {
    foreach ($set in $sets) {
        $imgPath = "$base\$dataset\images\$set\*"
        $lblPath = "$base\$dataset\labels\$set\*"

        if (Test-Path "$base\$dataset\images\$set") {
            Copy-Item $imgPath -Destination "$merged\images\$set" -Force
        }
        if (Test-Path "$base\$dataset\labels\$set") {
            Copy-Item $lblPath -Destination "$merged\labels\$set" -Force
        }
    }
}

Write-Host "`n✅ Merge complete. Check the Merged_Dataset folder." -ForegroundColor Green
