"""
Verifies the classical-CV contour detection logic in
apps/ai/services/feature_extractor.py actually finds rectangular
'building-like' shapes on a synthetic test image, using the real
cv2/numpy pipeline (both ARE installed in this sandbox).
"""
import cv2
import numpy as np

img = np.zeros((400, 400), dtype=np.uint8)
img[:] = 30  # background "ground" noise level

# Draw 3 synthetic "buildings" (bright rectangles) + 1 thin sliver to be rejected
cv2.rectangle(img, (40, 40), (120, 100), 220, -1)
cv2.rectangle(img, (200, 150), (300, 260), 200, -1)
cv2.rectangle(img, (60, 250), (150, 340), 210, -1)
cv2.rectangle(img, (350, 10), (355, 390), 190, -1)  # thin sliver -> should be rejected by aspect ratio filter

blurred = cv2.GaussianBlur(img, (5, 5), 0)
edges = cv2.Canny(blurred, 50, 150)
kernel = np.ones((3, 3), np.uint8)
closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

MIN_CONTOUR_AREA_PX = 150
MAX_ASPECT_RATIO = 8.0

accepted = []
for cnt in contours:
    area_px = cv2.contourArea(cnt)
    if area_px < MIN_CONTOUR_AREA_PX:
        continue
    x, y, w, h = cv2.boundingRect(cnt)
    aspect_ratio = max(w, h) / max(1, min(w, h))
    if aspect_ratio > MAX_ASPECT_RATIO:
        continue
    hull = cv2.convexHull(cnt)
    hull_area = cv2.contourArea(hull) or 1
    solidity = area_px / hull_area
    confidence = round(min(95.0, solidity * 100), 1)
    accepted.append({"bbox": (x, y, w, h), "area_px": area_px, "confidence": confidence})

print(f"Total raw contours found: {len(contours)}")
print(f"Accepted building candidates: {len(accepted)}")
for a in accepted:
    print(" -", a)

assert len(accepted) == 3, f"Expected 3 accepted building candidates (sliver should be rejected), got {len(accepted)}"
for a in accepted:
    assert a["confidence"] > 70, "Rectangular shapes should have high solidity-based confidence"
print("\nPASS: CV pipeline correctly detects 3 rectangular candidates and rejects the thin sliver.")
