import cv2
import numpy as np

def calculate_greenness(image):
    """NDVI-like approximation for greenness score"""
    image = image.astype("float32")
    B, G, R = cv2.split(image)
    greenness = (2 * G - R - B) / (2 * G + R + B + 1e-6)
    greenness = np.clip(greenness, -1, 1)
    return greenness

def calculate_health_score(greenness_map):
    avg_greenness = np.mean(greenness_map)
    if avg_greenness < -0.2:
        return 0  # Very poor (dead/brown)
    elif avg_greenness < 0:
        return 3  # Poor (mushy/muddy)
    elif avg_greenness < 0.2:
        return 5  # Moderate (stressed)
    elif avg_greenness < 0.5:
        return 7  # Good
    else:
        return 10  # Excellent
