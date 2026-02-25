import cv2
import numpy as np
from utils import calculate_greenness, calculate_health_score
import os

def run_health_analysis(image_path):
    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ Failed to load image: {image_path}")
        return

    img_resized = cv2.resize(img, (640, 640))
    greenness_map = calculate_greenness(img_resized)
    score = calculate_health_score(greenness_map)

    print(f"🌿 Hydration Health Score (0–10): {score:.2f}")

    # Optional: visualize
    heatmap = (greenness_map + 1) / 2  # normalize -1 to 1 → 0 to 1
    heatmap = np.uint8(heatmap * 255)
    heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)

    overlay = cv2.addWeighted(img_resized, 0.6, heatmap, 0.4, 0)
    cv2.imshow("Health Detection", overlay)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    image_file = "test_images/lawn_01.jpg"
    run_health_analysis(image_file)
