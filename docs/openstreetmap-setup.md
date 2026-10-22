# OpenStreetMap location picker for Report Incident

The Report Incident page uses Leaflet with OpenStreetMap tiles. Users can search for a place, click the map, or drag the marker. The selected address (when available) and coordinates are passed into the incident report.

## Billing and API keys

- No Google Maps API key or Google Cloud billing account is required.
- Map tiles are provided by OpenStreetMap's community tile service. Follow its [tile usage policy](https://operations.osmfoundation.org/policies/tiles/); do not bulk-download tiles or use the service for heavy traffic.
- Place search and reverse geocoding use the public Nominatim service. Follow its [usage policy](https://operations.osmfoundation.org/policies/nominatim/), keep requests user-triggered, and do not build autocomplete or send repeated requests.
- Public community services have capacity limits and are not covered by an uptime guarantee. If usage grows, use a provider with an appropriate service plan or host/configure your own geocoding service.

No secrets configuration is needed for this picker. Leaflet and the public map/geocoding endpoints require an internet connection.
