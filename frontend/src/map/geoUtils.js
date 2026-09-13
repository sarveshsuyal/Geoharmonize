/**
 * Lightweight, dependency-free geometry helpers for the GIS map tools.
 * Kept separate from the AI/analysis geometry logic (which lives server-side).
 */

/** Recursively walk a GeoJSON geometry's coordinate arrays. */
function walkCoords(coords, fn) {
  if (typeof coords[0] === "number") {
    fn(coords);
    return;
  }
  coords.forEach((c) => walkCoords(c, fn));
}

/**
 * Compute a Leaflet-style bounds ([[south, west], [north, east]]) for a
 * single GeoJSON geometry, Feature, or FeatureCollection.
 * Returns null if no valid coordinates are found.
 */
export function geojsonBounds(geojson) {
  if (!geojson) return null;

  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;

  function visitGeometry(geometry) {
    if (!geometry || !geometry.coordinates) return;
    walkCoords(geometry.coordinates, ([lon, lat]) => {
      if (lon < minLon) minLon = lon;
      if (lon > maxLon) maxLon = lon;
      if (lat < minLat) minLat = lat;
      if (lat > maxLat) maxLat = lat;
    });
  }

  if (geojson.type === "FeatureCollection") {
    (geojson.features || []).forEach((f) => visitGeometry(f.geometry));
  } else if (geojson.type === "Feature") {
    visitGeometry(geojson.geometry);
  } else {
    visitGeometry(geojson);
  }

  if (!isFinite(minLon) || !isFinite(minLat) || !isFinite(maxLon) || !isFinite(maxLat)) return null;
  return [
    [minLat, minLon],
    [maxLat, maxLon],
  ];
}

/** Rough planar-approximation area in m^2 for a small rectangle/polygon ring - kept only
 * as a fast fallback; SelectAreaControl uses geodesicRingArea (below) for anything shown to the user. */
export function ringAreaSqMeters(ring) {
  if (!ring || ring.length < 3) return 0;
  const meanLat = ring.reduce((s, [, lat]) => s + lat, 0) / ring.length;
  const latRad = (meanLat * Math.PI) / 180;
  const mPerDegLat = 111320;
  const mPerDegLon = 111320 * Math.cos(latRad);

  let sum = 0;
  for (let i = 0; i < ring.length; i++) {
    const [lon1, lat1] = ring[i];
    const [lon2, lat2] = ring[(i + 1) % ring.length];
    const x1 = lon1 * mPerDegLon;
    const y1 = lat1 * mPerDegLat;
    const x2 = lon2 * mPerDegLon;
    const y2 = lat2 * mPerDegLat;
    sum += x1 * y2 - x2 * y1;
  }
  return Math.abs(sum / 2);
}

const EARTH_RADIUS_M = 6378137; // WGS84 equatorial radius

function toRad(deg) {
  return (deg * Math.PI) / 180;
}

/**
 * Proper geodesic area of a ring of [lon, lat] points, using the spherical-excess
 * method (the same approach used by mapbox/geojson-area and turf.js's `area`).
 * This is required instead of a naive planar/Cartesian degree calculation, which
 * distorts badly away from the equator - it's what SelectAreaControl uses for the
 * "Selected Area" figure shown to the user.
 */
export function geodesicRingArea(ring) {
  if (!ring || ring.length < 3) return 0;
  const coords = ring[0][0] === ring[ring.length - 1][0] && ring[0][1] === ring[ring.length - 1][1] ? ring.slice(0, -1) : ring;
  const n = coords.length;
  if (n < 3) return 0;

  let total = 0;
  for (let i = 0; i < n; i++) {
    const lower = coords[(i + n - 1) % n];
    const middle = coords[i];
    const upper = coords[(i + 1) % n];
    total += (toRad(upper[0]) - toRad(lower[0])) * Math.sin(toRad(middle[1]));
  }
  return Math.abs((total * EARTH_RADIUS_M * EARTH_RADIUS_M) / 2);
}

export function formatArea(m2) {
  if (!Number.isFinite(m2)) return "—";
  if (m2 >= 1_000_000) return `${(m2 / 1_000_000).toFixed(2)} km²`;
  if (m2 >= 10_000) return `${m2.toLocaleString(undefined, { maximumFractionDigits: 0 })} m² (${(m2 / 10_000).toFixed(2)} ha)`;
  return `${m2.toLocaleString(undefined, { maximumFractionDigits: 0 })} m²`;
}

/** Ray-casting point-in-polygon test against a single [lon, lat] ring. Planar test -
 * fine for the small extents a hand-drawn selection covers; not used for the area figure. */
export function pointInRing(point, ring) {
  const [x, y] = point;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    const intersects = yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
    if (intersects) inside = !inside;
  }
  return inside;
}

/** Best-effort "does this GeoJSON feature intersect the selection ring" check - a
 * vertex-based approximation (not exact polygon clipping), used only to give the
 * Select Area panel a feature count without adding a PostGIS-exact intersection
 * endpoint. Labelled as approximate wherever it's shown in the UI. */
export function featureRoughlyIntersectsRing(feature, selectionRing) {
  const geometry = feature?.geometry;
  if (!geometry) return false;

  const featureVertices = [];
  walkCoords(geometry.coordinates, (c) => featureVertices.push(c));
  if (featureVertices.length === 0) return false;

  // Case 1: any feature vertex falls inside the selection.
  if (featureVertices.some((v) => pointInRing(v, selectionRing))) return true;

  // Case 2: the feature is a polygon that fully contains the selection (so none
  // of the feature's own vertices land inside it) - check the reverse direction.
  if (featureVertices.length >= 3 && selectionRing.some((v) => pointInRing(v, featureVertices))) return true;

  return false;
}

export function isValidLat(v) {
  return Number.isFinite(v) && v >= -90 && v <= 90;
}

export function isValidLon(v) {
  return Number.isFinite(v) && v >= -180 && v <= 180;
}
