import time
from rest_framework import views, viewsets, permissions, status
from rest_framework.response import Response
from shapely.geometry import shape, Polygon, mapping
from shapely.validation import make_valid
from django.utils import timezone

from .models import AIAnalysisRun, AIAnalysisFeature, AIPlanningRecommendation
from .serializers import AIAnalysisRequestSerializer, AIAnalysisRunSerializer
from .services.imagery_provider import ImageryProvider
from .services.land_use_classifier import LandUseClassifier
from .services.recommendation_engine import PlanningRecommendationEngine


class AIAnalyzeView(views.APIView):
    """
    POST /api/ai/analyze/
    Processes an Area of Interest (AOI):
      1. Crops/fetches georeferenced imagery for the AOI.
      2. Runs classical CV and spectral multi-class classification.
      3. Extracts georeferenced vector features (built-up, bare, agri, veg, water, road).
      4. Generates planning recommendations (agriculture & construction suitability).
      5. Persists analysis and returns complete GeoJSON and metrics.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = AIAnalysisRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        aoi_data = serializer.validated_data["aoi"]
        bounds_data = serializer.validated_data.get("bounds")

        try:
            # Parse AOI geometry to shapely Polygon
            if isinstance(aoi_data, dict):
                if aoi_data.get("type") == "Feature":
                    aoi_geom = shape(aoi_data["geometry"])
                else:
                    aoi_geom = shape(aoi_data)
            elif isinstance(aoi_data, list):
                # Coordinates ring [[lng, lat], ...]
                if len(aoi_data) > 0 and isinstance(aoi_data[0], list):
                    ring = aoi_data
                    if ring[0] != ring[-1]:
                        ring = ring + [ring[0]]
                    aoi_geom = Polygon(ring)
                else:
                    return Response({"error": "Invalid coordinates ring"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": "Unrecognized AOI format"}, status=status.HTTP_400_BAD_REQUEST)

            aoi_geom = make_valid(aoi_geom)
            if aoi_geom.is_empty or not isinstance(aoi_geom, Polygon):
                return Response({"error": "AOI must be a valid non-empty polygon"}, status=status.HTTP_400_BAD_REQUEST)

            if not bounds_data or len(bounds_data) != 4:
                bounds_data = list(aoi_geom.bounds)  # (minx, miny, maxx, maxy)

            # 1. Fetch / synthesize georeferenced AOI raster
            imagery_provider = ImageryProvider()
            img_rgb, transform, source_type = imagery_provider.get_aoi_raster(aoi_geom, bounds_data)

            # 2. Run Land-Use classification
            classifier = LandUseClassifier()
            classification_result = classifier.classify_aoi(img_rgb, transform, aoi_geom)

            features_fc = classification_result["feature_collection"]
            summary_stats = classification_result["summary_statistics"]

            # 3. Run Planning Recommendations Engine
            rec_engine = PlanningRecommendationEngine()
            recommendations_result = rec_engine.evaluate_recommendations(features_fc["features"], aoi_geom)

            recommendations_fc = recommendations_result["feature_collection"]
            rec_summary = recommendations_result["summary"]
            summary_stats["recommendations_summary"] = rec_summary

            # Overall confidence score
            conf_scores = [f["properties"].get("confidence", 70.0) for f in features_fc["features"]]
            overall_confidence = round(sum(conf_scores) / max(1, len(conf_scores)), 1)
            summary_stats["overall_confidence"] = overall_confidence

            # 4. Persist Analysis Run
            run = AIAnalysisRun.objects.create(
                aoi_geometry=mapping(aoi_geom),
                aoi_bounds=bounds_data,
                area_m2=summary_stats["total_area_m2"],
                source_imagery_type=source_type,
                status="COMPLETED",
                method_category=classifier.method_category,
                model_name=classifier.model_name,
                model_version=classifier.model_version,
                is_ml_model=classifier.is_ml_model,
                confidence_score=overall_confidence,
                summary_statistics=summary_stats,
                features_geojson=features_fc,
                recommendations_geojson=recommendations_fc,
                completed_at=timezone.now(),
            )

            # Return complete analysis response
            resp_data = AIAnalysisRunSerializer(run).data
            return Response(resp_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": f"AI analysis failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AIAnalysisRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AIAnalysisRun.objects.all()
    serializer_class = AIAnalysisRunSerializer
    permission_classes = [permissions.AllowAny]


class AIAnalysisGeoJSONView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            run = AIAnalysisRun.objects.get(pk=pk)
            return Response(run.features_geojson)
        except AIAnalysisRun.DoesNotExist:
            return Response({"error": "Analysis not found"}, status=status.HTTP_404_NOT_FOUND)


class AIRecommendationsGeoJSONView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            run = AIAnalysisRun.objects.get(pk=pk)
            return Response(run.recommendations_geojson)
        except AIAnalysisRun.DoesNotExist:
            return Response({"error": "Analysis not found"}, status=status.HTTP_404_NOT_FOUND)
