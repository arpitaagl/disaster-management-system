# Google Maps setup for Report Incident

The Report Incident page uses an embedded Google Maps location picker. Users can search for an address or landmark, click the map, or drag the pin. The selected address and coordinates are saved with the incident report.

## Configure the API key

1. In Google Cloud Console, select or create a project and enable billing.
2. Enable **Maps JavaScript API** and **Places API** for that project.
3. Create an API key. Restrict it to those APIs and to the app's allowed website referrers (include your deployed Streamlit app domain and local development origin if needed).
4. In Streamlit Community Cloud, open the app's **Settings → Secrets** and add:

   ```toml
   GOOGLE_MAPS_API_KEY = "YOUR_RESTRICTED_API_KEY"
   ```

5. Save the secrets and reboot/redeploy the app.

For local development, add the same setting to `.streamlit/secrets.toml` (do not commit this file) or set the `GOOGLE_MAPS_API_KEY` environment variable.

The key is used by browser-side Google Maps JavaScript, so API and website-referrer restrictions are essential. Google Maps may not load if billing, API enablement, or key restrictions are incorrect.
