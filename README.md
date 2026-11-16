# HeatShield

**Hyperlocal heat-stress early warning for outdoor workers — starting in Mumbai.**

HeatShield tells construction labourers, street vendors, delivery riders and other
outdoor workers how dangerous today's heat is *where they work*, and what to do
about it — work/rest schedule, water, safe hours — by WhatsApp, SMS or voice call,
in their own language, on any phone.

Unlike weather apps (air temperature / heat index) and district-level heat
warnings, HeatShield uses **WBGT** (Wet Bulb Globe Temperature), the occupational
heat-stress standard that accounts for humidity, sun, wind and workload — which
matters enormously in humid coastal cities like Mumbai.

## Status

| Part | State |
|---|---|
| WBGT physics engine (Liljegren 2008) | ✅ done, validated against ECMWF `thermofeel` to ±0.01 °C |
| Risk engine (NIOSH / ISO 7243 limits, work/rest) | ✅ done |
| Open-Meteo forecast → hourly WBGT CLI | ✅ done |
| API, database, alert job (morning, peak, warm night), heartbeat | ✅ done — see [`backend/`](backend/) |
| Web app: heat now, 7-day outlook, plan a job, Mumbai ward map, symptom check, water near me, sign-up and alerts inbox | ✅ done — see [`web/`](web/) |
| Alert sending: web inbox, Telegram, WhatsApp Cloud API | ✅ senders done; needs bot token / Meta approval to go live |
| Telegram bot conversation (sign-up, commands) | ⏳ next — roadmap package A2 |
| Deployment, station data collection | ⏳ next — packages A3, A4 |
| Street-level ML downscaling | ⏳ planned — see [`ml/`](ml/) |
| Team mode, weekly summary, regional languages, SMS / voice | ⏳ planned |
| Low-cost WBGT sensor nodes | ⏸ parked — see [`firmware/`](firmware/) |

What happens next, package by package: [`docs/ROADMAP.md`](docs/ROADMAP.md). Background: [`docs/PROPOSAL.md`](docs/PROPOSAL.md) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## Quick start (macOS / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                                   # run the tests
python -m heatshield.cli --city mumbai --work heavy   # today's hourly heat risk
```

### Run the website

```bash
pip install -r requirements.txt
(cd web && npm install && npm run build)        # build the web app once
uvicorn backend.main:app --reload               # open http://localhost:8000
```

No internet or want a repeatable demo? Start it with `HEATSHIELD_SAMPLE_DATA=1`
to use a recorded Mumbai forecast. While working on the web app, run
`npm run dev` in `web/` as well and open the address it prints (it forwards
`/api` to port 8000). Settings are listed in [`.env.example`](.env.example).

CLI options: `--work light|moderate|heavy|very_heavy`, `--days 1-7`,
`--unacclimatised` (for someone new to the heat).

Example output columns: local time, air temp, humidity, solar radiation,
globe temp, natural wet-bulb, **WBGT**, risk level, and minutes of work vs rest
per hour.

## How the numbers are made

```
Open-Meteo hourly forecast (temp, humidity, wind, sun, pressure)
        │
        ├── sun position (NOAA equations)
        ▼
Liljegren energy-balance model ──► globe temp + natural wet-bulb ──► WBGT
        │
        ▼
NIOSH/ISO 7243 limit for the workload ──► risk level + work/rest minutes per hour
```

## Disclaimer

HeatShield gives guidance based on international occupational standards. It is not
medical advice. Anyone with confusion, fainting, or very high body temperature
needs emergency care — call **108** or **112**.
