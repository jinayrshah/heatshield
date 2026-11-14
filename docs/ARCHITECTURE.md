# HeatShield — Architecture

## System overview

```
                 ┌────────────────────── DATA SOURCES ───────────────────────┐
                 │ Open-Meteo forecast   ERA5 history   Landsat/MODIS LST    │
                 │ Sentinel-2 NDVI       ESA WorldCover   OSM   CPCB/IMD AWS │
                 │ HeatShield sensor nodes (ESP32 → MQTT)                    │
                 └───────────────┬───────────────────────────────────────────┘
                                 ▼
   ┌──────────── PIPELINE (scheduled, hourly / daily) ────────────┐
   │ fetch forecast → WBGT engine (heatshield.wbgt)  ✅            │
   │ static features (Earth Engine, monthly) → ML downscaler (ml/) │
   │ → hourly WBGT grid (~100 m) stored in PostGIS                 │
   └───────────────┬──────────────────────────────────────────────┘
                   ▼
   ┌──────────── API (FastAPI) ───────────────────────────────────┐
   │ /wbgt?lat&lon&hours   /risk?cell&workload   /users  /alerts   │
   │ risk engine (heatshield.risk)  ✅                              │
   └───────┬──────────────────────┬───────────────────────┬───────┘
           ▼                      ▼                       ▼
   Alert scheduler          Inbound webhooks        Dashboard (React +
   (6 am daily + peak       (WhatsApp/SMS replies:   MapLibre): map,
   reminders)               STOP, symptoms, Q&A)     hotspots, placement
           │
           ▼
   WhatsApp (Gupshup / Meta Cloud API) · SMS (MSG91/Twilio, DLT templates)
   · Voice (Exotel/Twilio + IndicTTS pre-rendered audio)
```

## Repository layout

```
heatshield/        Python package — physics + risk (pure, no I/O except forecast.py)
  solar.py         sun position (NOAA)
  wbgt.py          Liljegren WBGT model
  risk.py          NIOSH/ISO 7243 limits → risk level + work/rest
  forecast.py      Open-Meteo client → hourly WBGT
  cli.py           command-line forecast
tests/             pytest suite (no network)
backend/           FastAPI service ✅: API, DB models, alert job, messaging channels
web/               React + Vite + MapLibre web app ✅ (PWA), served by the backend
ml/                downscaling notebooks + training code (planned)
firmware/          ESP32 sensor node (parked)
docs/              proposal, architecture, roadmap
```

## Key design decisions

| Decision | Choice | Why |
|---|---|---|
| Heat metric | WBGT (Liljegren physics) | Occupational standard; captures Mumbai humidity |
| Validation of physics | Compare with ECMWF `thermofeel` | Independent reference implementation |
| Limits | NIOSH REL/RAL formulas (= ISO 7243) | Published, citable, workload-aware |
| Risk logic | Rules, not ML | Transparent and auditable for safety advice |
| Downscaling | LightGBM on satellite features | Strong on tabular data, explainable via SHAP |
| Storage | PostgreSQL + PostGIS | Spatial queries on grid cells |
| Location privacy | Store grid cell id, not coordinates | Minimises personal data |
| Messaging | Channel adapters behind one interface | Swap WhatsApp/SMS/voice providers freely |

## As built (2026-11-14)

- **One process**: `uvicorn backend.main:app` serves the API under `/api` and the built web app. APScheduler runs the alert job in the same process every 30 minutes (minute 0 and 30, so half-hour timezones like IST work) and once at start-up.
- **Forecast cache**: locations are rounded to 2 decimals (~1 km cell). One Open-Meteo call per cell per hour; the city map fetches all 24 ward centres in one multi-location call. If a refresh fails, the previous forecast is served and marked stale for up to 36 h.
- **Database**: SQLite by default, Postgres via `DATABASE_URL`. Tables: users (cell, not coordinates), alerts (unique per user, kind, day and slot, so a re-run never double-sends), anonymous counters, job runs.
- **Accounts**: no password or phone number. Sign-up returns a random token kept on the device; only its SHA-256 hash is stored. Telegram is linked with a one-time code.
- **Channels**: web inbox always; Telegram and WhatsApp switch on when their environment variables are set. A failed channel is recorded per alert and does not stop the others.
- **Map**: MapLibre with OpenStreetMap raster tiles (no key). Ward polygons from DataMeet, simplified to ~40 m (29 KB).

## Failure handling

| Failure | Behaviour |
|---|---|
| Forecast fetch fails | ✅ Serve previous forecast marked stale (alerts say "based on an earlier forecast"); retry every 5 min; failed job run recorded and operator told on Telegram |
| Missing hourly values | ✅ Skip that hour (never guess); job planner skips windows with a gap |
| Message provider down | ✅ Logged per alert and in delivery-rate stats; other channels still sent. SMS fallback later |
| Sensor offline | Exclude from validation; dashboard shows "stale" after 2 h |
| Model output out of range | Fall back to raw forecast WBGT for that cell |

A silent pipeline failure on a hot day is the worst outcome, so every job run
is recorded and `/api/health` reports `alert_job_healthy: false` if there has
been no successful run for 75 minutes. Point UptimeRobot (free) at it.
