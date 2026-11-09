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
backend/           FastAPI service, DB models, scheduler, messaging (planned)
ml/                downscaling notebooks + training code (planned)
firmware/          ESP32 sensor node (planned)
dashboard/         web dashboard (planned)
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

## Failure handling (to implement in backend)

| Failure | Behaviour |
|---|---|
| Forecast fetch fails | Retry with backoff; if still failing by 05:30, send alert from previous run marked "based on yesterday's forecast"; page the operator |
| Missing hourly values | Skip that hour (never guess); alert if > 3 hours missing |
| Message provider down | Fallback channel (WhatsApp → SMS); log undelivered |
| Sensor offline | Exclude from validation; dashboard shows "stale" after 2 h |
| Model output out of range | Fall back to raw forecast WBGT for that cell |

A silent pipeline failure on a hot day is the worst outcome, so the daily job
emits a heartbeat and the operator is alerted if it is missing.
