import cv2
import numpy as np

def calculate_greenness_ratio(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Define green color range
    lower_green = np.array([35, 40, 40])
    upper_green = np.array([85, 255, 255])

    mask = cv2.inRange(hsv, lower_green, upper_green)

    # Calculate ratio of green pixels
    green_ratio = np.sum(mask) / (mask.shape[0] * mask.shape[1] * 255)
    return round(green_ratio, 4)

def calculate_adjusted_greenness_score(green_ratio):
    low = 0.0       # Brown/dry
    ideal = 0.5     # Perfect green
    high = 0.85     # Overwatered / overly lush

    if green_ratio < ideal:
        # Scale from -10 to 0
        return round(((green_ratio - low) / (ideal - low)) * 10 - 10, 2)
    else:
        # Scale from 0 to +10
        return round(((green_ratio - ideal) / (high - ideal)) * 10, 2)

# Open webcam
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Cannot open camera")
    exit()

print("Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    greenness_ratio = calculate_greenness_ratio(frame)
    irrigation_score = calculate_adjusted_greenness_score(greenness_ratio)

    # Display both scores on screen
    text = f"Irrigation Score: {irrigation_score} (Ratio: {greenness_ratio})"
    cv2.putText(frame, text, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.imshow('Irrigation AI - Grass Health', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
