/**
 * Simulated AI GIS Analysis Engine (Client-side fallback).
 * 
 * Activated automatically when the backend Docker container (port 8000) is offline
 * or during preview demos. Produces realistic georeferenced land-use classification
 * and planning recommendation polygons tailored to the user's selected AOI.
 */

export function generateSimulatedAIAnalysis(selectionData) {
  const [minx, miny, maxx, maxy] = selectionData.bounds || [77.70, 29.05, 77.71, 29.06];
  const totalAreaM2 = Math.round(selectionData.areaM2 || 50000);
  const totalAreaHa = Number((totalAreaM2 / 10000).toFixed(2));

  const dx = (maxx - minx) / 3;
  const dy = (maxy - miny) / 3;

  const classes = [
    { key: "AGRICULTURE", label: "Active Cultivated Field", color: "#eab308", conf: 89, rec: "AGRICULTURE", score: 92, reason: "Optimal soil profile & high vegetative index (NDVI: 0.68)." },
    { key: "BUILT_UP", label: "Residential / Commercial Structure", color: "#ef4444", conf: 86, reason: "High spectral reflectance and rectilinear edge density." },
    { key: "BARE_LAND", label: "Vacant Parcel / Open Ground", color: "#22c55e", conf: 81, rec: "CONSTRUCTION", score: 84, reason: "Flat topography, proximity to road access, clear of water bodies." },
    { key: "AGRICULTURE", label: "Agricultural Plot (Rabi Season)", color: "#eab308", conf: 91, rec: "AGRICULTURE", score: 88, reason: "Continuous crop rotation history in land records." },
    { key: "VEGETATION", label: "Dense Tree Canopy / Orchard", color: "#15803d", conf: 94, reason: "High infrared absorption, clustered canopy texture." },
    { key: "BUILT_UP", label: "Ancillary Farm Building", color: "#ef4444", conf: 83, reason: "Compact rectangular footprint with road connectivity." },
    { key: "BARE_LAND", label: "Unutilized Open Plot", color: "#22c55e", conf: 78, rec: "CONSTRUCTION", score: 79, reason: "Zoned residential-mixed with no active encroachment." },
    { key: "ROAD", label: "Access Corridor / Road Surface", color: "#f97316", conf: 85, reason: "Linear high-contrast spectral feature connecting parcels." },
    { key: "AGRICULTURE", label: "Arable Farmland", color: "#eab308", conf: 87, rec: "AGRICULTURE", score: 90, reason: "Favorable slope (<3%) with historical irrigation access." },
  ];

  const features = [];
  const recFeatures = [];

  let idx = 0;
  for (let r = 0; r < 3; r++) {
    for (let c = 0; c < 3; c++) {
      const x0 = minx + c * dx;
      const x1 = x0 + dx;
      const y0 = miny + r * dy;
      const y1 = y0 + dy;

      const polyRing = [
        [x0, y0],
        [x1, y0],
        [x1, y1],
        [x0, y1],
        [x0, y0],
      ];

      const item = classes[idx % classes.length];
      const subAreaM2 = Math.round(totalAreaM2 / 9);
      const subAreaHa = Number((subAreaM2 / 10000).toFixed(2));

      features.push({
        type: "Feature",
        id: `feat-${idx + 1}`,
        geometry: {
          type: "Polygon",
          coordinates: [polyRing],
        },
        properties: {
          id: idx + 1,
          land_use: item.key,
          label: item.label,
          color: item.color,
          fill_color: item.color,
          stroke_color: item.color,
          confidence: item.conf,
          area_m2: subAreaM2,
          area_ha: subAreaHa,
          reasons: [item.reason],
        },
      });

      if (item.rec) {
        recFeatures.push({
          type: "Feature",
          id: `rec-${idx + 1}`,
          geometry: {
            type: "Polygon",
            coordinates: [polyRing],
          },
          properties: {
            id: idx + 1,
            recommendation_type: item.rec,
            label: item.rec === "AGRICULTURE" ? "Agriculture Candidate" : "Construction Candidate",
            suitability_score: item.score,
            confidence: item.conf,
            area_m2: subAreaM2,
            area_ha: subAreaHa,
            reasons: [item.reason],
          },
        });
      }

      idx++;
    }
  }

  // Calculate statistics
  const counts = {};
  features.forEach((f) => {
    const k = f.properties.land_use;
    counts[k] = (counts[k] || 0) + 1;
  });

  const totalCount = features.length;
  const percentages = {
    AGRICULTURE: Math.round(((counts.AGRICULTURE || 0) / totalCount) * 100),
    BUILT_UP: Math.round(((counts.BUILT_UP || 0) / totalCount) * 100),
    BARE_LAND: Math.round(((counts.BARE_LAND || 0) / totalCount) * 100),
    VEGETATION: Math.round(((counts.VEGETATION || 0) / totalCount) * 100),
    ROAD: Math.round(((counts.ROAD || 0) / totalCount) * 100),
    WATER: 0,
  };

  const agriRecHa = Number(((totalAreaHa * (percentages.AGRICULTURE || 30)) / 100).toFixed(2));
  const constRecHa = Number(((totalAreaHa * (percentages.BARE_LAND || 20)) / 100).toFixed(2));

  return {
    id: Date.now(),
    is_simulated: true,
    method_category: "COMPUTER_VISION_HEURISTIC",
    model_name: "OpenCV Spectral Segmentation",
    model_version: "v1.4 (Preview Engine)",
    confidence_score: 87.2,
    summary_statistics: {
      total_area_m2: totalAreaM2,
      total_area_ha: totalAreaHa,
      percentages,
      detected_buildings_count: counts.BUILT_UP ? counts.BUILT_UP * 2 : 2,
      detected_road_length_km: Number((((maxx - minx) * 111) * 0.8).toFixed(2)),
      overall_confidence: 87.2,
      recommendations_summary: {
        agriculture_candidate_ha: agriRecHa,
        construction_candidate_ha: constRecHa,
        disclaimer: "Simulated GIS analysis (Backend Docker offline). Start backend container for full satellite tile extraction.",
      },
    },
    features_geojson: {
      type: "FeatureCollection",
      features,
    },
    recommendations_geojson: {
      type: "FeatureCollection",
      features: recFeatures,
    },
  };
}
