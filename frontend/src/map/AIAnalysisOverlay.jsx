import React from "react";
import { GeoJSON } from "react-leaflet";

/**
 * AIAnalysisOverlay: Transparent, switchable vector overlay for the Leaflet map.
 *
 * Renders:
 *  1. Land-use classification polygons with adjustable fillOpacity (0.15 - 0.85).
 *  2. Optional Planning Recommendations layer with distinct dashed styling.
 *
 * The original basemap remains 100% visible underneath.
 * Switching basemaps does not alter or reposition these vector features.
 */
export default function AIAnalysisOverlay({
  analysis,
  showLandUse = true,
  landUseOpacity = 0.4,
  showRecommendations = true,
  recommendationsOpacity = 0.45,
  onFeatureClick,
  onRecommendationClick,
}) {
  if (!analysis) return null;

  const featuresGeojson = analysis.features_geojson;
  const recommendationsGeojson = analysis.recommendations_geojson;

  return (
    <>
      {/* 1. Land-Use Classification Overlay */}
      {showLandUse && featuresGeojson && featuresGeojson.features?.length > 0 && (
        <GeoJSON
          key={`ai-landuse-${analysis.id}-${landUseOpacity}-${featuresGeojson.features.length}`}
          data={featuresGeojson}
          style={(feature) => {
            const props = feature.properties || {};
            const fillColor = props.color || props.fill_color || "#64748b";
            const strokeColor = props.stroke_color || fillColor;
            return {
              color: strokeColor,
              fillColor: fillColor,
              weight: 1.5,
              opacity: 0.8,
              fillOpacity: landUseOpacity,
            };
          }}
          onEachFeature={(feature, layer) => {
            const p = feature.properties || {};
            layer.bindTooltip(
              `<strong>${p.label || p.land_use}</strong><br/>${p.area_ha ? `${p.area_ha} ha` : `${p.area_m2} m²`} (${p.confidence}% conf)`,
              { sticky: true, className: "text-xs font-sans" }
            );
            if (onFeatureClick) {
              layer.on("click", () => onFeatureClick(feature));
            }
          }}
        />
      )}

      {/* 2. Planning Recommendations Overlay */}
      {showRecommendations && recommendationsGeojson && recommendationsGeojson.features?.length > 0 && (
        <GeoJSON
          key={`ai-rec-${analysis.id}-${recommendationsOpacity}-${recommendationsGeojson.features.length}`}
          data={recommendationsGeojson}
          style={(feature) => {
            const props = feature.properties || {};
            const isAgri = props.recommendation_type === "AGRICULTURE";
            const isConst = props.recommendation_type === "CONSTRUCTION";
            const color = isAgri ? "#10b981" : isConst ? "#f97316" : "#94a3b8";
            const stroke = isAgri ? "#047857" : isConst ? "#c2410c" : "#475569";

            return {
              color: stroke,
              fillColor: color,
              weight: 2.5,
              dashArray: "5, 5",
              opacity: 0.9,
              fillOpacity: recommendationsOpacity,
            };
          }}
          onEachFeature={(feature, layer) => {
            const p = feature.properties || {};
            layer.bindTooltip(
              `<strong>★ ${p.label}</strong><br/>Suitability: ${p.suitability_score}% | ${p.area_ha} ha`,
              { sticky: true, className: "text-xs font-sans" }
            );
            if (onRecommendationClick) {
              layer.on("click", () => onRecommendationClick(feature));
            }
          }}
        />
      )}
    </>
  );
}
