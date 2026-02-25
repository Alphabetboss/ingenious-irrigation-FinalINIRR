from ultralytics import YOLO

# Load the pretrained YOLOv8n model
model = YOLO("yolov8n.pt")

# Export the model in ONNX format
model.export(format="onnx")

print("✅ Model exported successfully in ONNX format.")
