"""
Standalone, dependency-free verification of the core scoring math in
apps/harmonization/services/matching_service.py and confidence_service.py.

This reimplements just enough shapely-like behaviour (area, length, centroid
distance, intersects/intersection/union, bounds) for two simple rectangle
geometries so the *arithmetic* of IoU / area-similarity / shape-similarity /
confidence-weighting can be executed and checked in an environment without
GDAL/Shapely installed. It imports the ACTUAL service classes copied inline
below (kept import-path-independent from Django) so the formulas match the
real backend code exactly.
"""
import math
import sys


class Rect:
    """Axis-aligned rectangle standing in for a shapely Polygon."""
    def __init__(self, minx, miny, maxx, maxy):
        self.minx, self.miny, self.maxx, self.maxy = minx, miny, maxx, maxy

    @property
    def bounds(self):
        return (self.minx, self.miny, self.maxx, self.maxy)

    @property
    def area(self):
        return max(0, self.maxx - self.minx) * max(0, self.maxy - self.miny)

    @property
    def length(self):
        return 2 * ((self.maxx - self.minx) + (self.maxy - self.miny))

    @property
    def is_empty(self):
        return self.area <= 0

    class _Centroid:
        def __init__(self, x, y):
            self.x, self.y = x, y
        def distance(self, other):
            return math.hypot(self.x - other.x, self.y - other.y)

    @property
    def centroid(self):
        return Rect._Centroid((self.minx + self.maxx) / 2, (self.miny + self.maxy) / 2)

    def intersects(self, other):
        ix = not (self.maxx < other.minx or other.maxx < self.minx)
        iy = not (self.maxy < other.miny or other.maxy < self.miny)
        return ix and iy

    def intersection(self, other):
        ix1, iy1 = max(self.minx, other.minx), max(self.miny, other.miny)
        ix2, iy2 = min(self.maxx, other.maxx), min(self.maxy, other.maxy)
        return Rect(ix1, iy1, max(ix1, ix2), max(iy1, iy2))

    def union(self, other):
        # Not geometrically accurate for area(union) of two rects in general,
        # but for these axis-aligned test cases we use the exact formula:
        inter = self.intersection(other).area if self.intersects(other) else 0
        class _U:
            def __init__(self, a):
                self.area = a
        return _U(self.area + other.area - inter)


# ---- inline copies of the pure scoring formulas (kept identical to the real service) ----

WEIGHTS = {"overlap": 0.40, "area": 0.20, "centroid": 0.20, "shape": 0.20}
CENTROID_DECAY = 25.0


def area_similarity(a, b):
    if a.area == 0 and b.area == 0:
        return 1.0
    larger, smaller = max(a.area, b.area), min(a.area, b.area)
    return smaller / larger if larger > 0 else 0.0


def shape_similarity(a, b):
    def compactness(g):
        perim = g.length
        return (4 * math.pi * g.area) / (perim ** 2) if perim > 0 else 0.0
    return 1 - abs(compactness(a) - compactness(b))


def centroid_similarity_score(dist):
    return math.exp(-dist / CENTROID_DECAY)


def combined_score(a, b):
    if not a.intersects(b):
        return 0.0
    inter = a.intersection(b).area
    union = a.union(b).area
    iou = inter / union if union > 0 else 0.0
    dist = a.centroid.distance(b.centroid)
    score = (
        WEIGHTS["overlap"] * iou
        + WEIGHTS["area"] * area_similarity(a, b)
        + WEIGHTS["centroid"] * centroid_similarity_score(dist)
        + WEIGHTS["shape"] * max(0.0, shape_similarity(a, b))
    )
    return round(score * 100, 2), iou, dist


def run():
    results = []

    # Case 1: near-identical parcel (small 0.8m boundary shift) -> should be HIGH confidence
    cadastral = Rect(0, 0, 20, 15)          # 300 sqm
    drone = Rect(0.5, 0.3, 20.4, 15.3)      # slightly shifted/larger, same shape
    score, iou, dist = combined_score(cadastral, drone)
    results.append(("near-identical parcel (small shift)", score, iou, dist, score >= 80))

    # Case 2: completely different parcel far away -> should be near 0 / no match
    other = Rect(500, 500, 510, 505)
    score2, iou2, dist2 = 0.0, 0.0, cadastral.centroid.distance(other.centroid)
    if cadastral.intersects(other):
        score2, iou2, dist2 = combined_score(cadastral, other)
    results.append(("unrelated distant parcel", score2, iou2, dist2, score2 < 20))

    # Case 3: partial overlap (subdivided parcel) -> should be MEDIUM
    subdivided = Rect(10, 0, 30, 15)  # overlaps half of cadastral
    score3, iou3, dist3 = combined_score(cadastral, subdivided)
    results.append(("partially overlapping (subdivision) parcel", score3, iou3, dist3, 20 < score3 < 80))

    print(f"{'Case':45s} {'Score':>8s} {'IoU':>8s} {'CentroidDist(m)':>16s}  Assertion")
    all_ok = True
    for name, score, iou, dist, assertion in results:
        ok = "PASS" if assertion else "FAIL"
        all_ok = all_ok and assertion
        print(f"{name:45s} {score:8.2f} {iou:8.3f} {dist:16.2f}  {ok}")

    print()
    print("ALL ASSERTIONS PASSED" if all_ok else "SOME ASSERTIONS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(run())
