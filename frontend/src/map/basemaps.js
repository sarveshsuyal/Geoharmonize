/**
 * Basemap definitions for the GIS map.
 *
 * Uses free map services:
 *  - Esri World Imagery (Satellite)
 *  - OpenStreetMap (Streets)
 *
 * No external API keys required.
 */

export const BASEMAPS = [
  {
    key: "satellite",
    label: "Satellite",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: "&copy; Esri, Maxar, Earthstar Geographics, and the GIS User Community",
    maxZoom: 19,
  },
  {
    key: "streets",
    label: "OpenStreetMap",
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19,
  },
];

export const DEFAULT_BASEMAP_KEY = "satellite";

export function getBasemap(key) {
  return BASEMAPS.find((b) => b.key === key) || BASEMAPS[0];
}

