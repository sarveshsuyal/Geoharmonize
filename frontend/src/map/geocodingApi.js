import axios from "axios";

/**
 * Geocoding client using OpenStreetMap Nominatim API.
 * Free service, no API key required.
 */
export async function geocode(query, { limit = 5 } = {}) {
  if (!query || query.trim().length < 2) return [];

  try {
    const url = "https://nominatim.openstreetmap.org/search";
    const res = await axios.get(url, {
      params: {
        q: query.trim(),
        format: "json",
        limit,
        addressdetails: 1,
      },
    });

    const items = Array.isArray(res.data) ? res.data : [];

    return items.map((item) => {
      const lat = parseFloat(item.lat);
      const lon = parseFloat(item.lon);
      let bbox = null;

      if (Array.isArray(item.boundingbox) && item.boundingbox.length === 4) {
        // Nominatim returns [south_lat, north_lat, west_lon, east_lon]
        const south = parseFloat(item.boundingbox[0]);
        const north = parseFloat(item.boundingbox[1]);
        const west = parseFloat(item.boundingbox[2]);
        const east = parseFloat(item.boundingbox[3]);
        if (!isNaN(west) && !isNaN(south) && !isNaN(east) && !isNaN(north)) {
          bbox = [west, south, east, north]; // [minLon, minLat, maxLon, maxLat]
        }
      }

      return {
        id: item.place_id ? String(item.place_id) : `${item.osm_type || "osm"}_${item.osm_id || Math.random()}`,
        name: item.display_name,
        center: [lon, lat], // [lon, lat]
        bbox,
        placeType: item.type || item.class || "place",
      };
    });
  } catch (err) {
    console.error("Nominatim geocoding request failed:", err);
    return [];
  }
}

