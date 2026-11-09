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
| Street-level ML downscaling | ⏳ planned — see [`ml/`](ml/) |
| Low-cost WBGT sensor nodes | ⏳ planned — see [`firmware/`](firmware/) |
| API, database, alert scheduler | ⏳ planned — see [`backend/`](backend/) |
| WhatsApp / SMS / voice alerts (Hindi, Marathi) | ⏳ planned |
| City / employer dashboard | ⏳ planned — see [`dashboard/`](dashboard/) |

Full plan: [`docs/PROPOSAL.md`](docs/PROPOSAL.md) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · [`docs/ROADMAP.md`](docs/ROADMAP.md)

## Quick start (macOS / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                                   # run the tests
python -m heatshield.cli --city mumbai --work heavy   # today's hourly heat risk
```

Options: `--work light|moderate|heavy|very_heavy`, `--days 1-7`,
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
