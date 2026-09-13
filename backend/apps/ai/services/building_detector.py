"""Thin, named wrapper around OpenCVFeatureExtractor for building-specific
extraction calls from the API/pipeline, keeping the AI module's public
surface organized by feature type as the problem statement requests."""
from .feature_extractor import OpenCVFeatureExtractor


class BuildingDetector:
    def __init__(self):
        self.extractor = OpenCVFeatureExtractor()

    def detect(self, dataset) -> dict:
        return self.extractor.extract(dataset)
