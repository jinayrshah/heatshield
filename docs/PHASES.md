# HeatShield — Phased Build Plan

Status: **draft, awaiting approval.** No phase starts until this plan is approved.

Each phase ends with something real people can use, deployed. Phases run in
order, but two long-lead items start early (see "Start now").

```
P0 Foundation ─► P1 Telegram alerts (MVP, live) ─► P2 WhatsApp + web app ─► P3 Dashboard
                         │                                                       │
                         └──► station data collection runs daily from P1 ──► P5 Street-level ML
                                                                                 │
                 P4 Safety features (team, water map, warm nights, ...) ◄────────┘
                                         │
                                         ▼
                              P6 Platform extras ─► P7 Launch hardening
```

## Start now (long lead time)

| Item | Why early |
|---|---|
| Meta Business account + WhatsApp Cloud API test number | Business verification and message-template approval can take days to weeks |
| Daily collection of public station readings (IMD, CPCB) for Mumbai | The ML model needs weeks of history; it cannot be collected later in one go |

## P0 — Foundation

- Project structure for a service: config, logging, settings via environment variables.
- GitHub Actions: tests on every push.
- Database schema (users, locations, preferences, alerts sent, forecast cache).
- Server provisioned, HTTPS, deploy script.

**Done when:** an empty API is live at a public URL, tests run on every push.

## P1 — Telegram alerts (MVP, first real users)

- Sign-up: share location pin or type an area, choose work type, usual hours, "new to heat?".
- `/now`, `/today`, `/outlook` (3–7 days), "Plan a job" (best window for N hours).
- 06:00 morning alert; peak-hour reminder when risk turns high or extreme.
- Symptom flow: first aid, emergency numbers 108 / 112.
- `/pause`, `/stop`, `/settings`, delete-my-data.
- Forecast cache: locations rounded to ~1 km cells; one Open-Meteo call per active cell per hour (well inside the free limit).
- Monitoring: heartbeat; you get a Telegram message if the 05:30 forecast run fails.

**Done when:** you and 5–10 real people receive correct alerts for a week.

## P2 — WhatsApp + web app

- One messaging core with channel adapters (Telegram, WhatsApp); same flows on both.
- WhatsApp approved utility templates for morning alerts and reminders.
- Web app (installable PWA): check any location, sign up, manage settings.

**Done when:** the same user journey works on Telegram, WhatsApp and the web.

## P3 — Dashboard

- City map of hourly WBGT (Mumbai grid), time slider, risk colours.
- Hotspot ranking by ward; focus wards highlighted.
- Usage statistics: users, alerts sent, delivery rate (no personal data shown).
- Admin view: system health, failed jobs, message failures.

**Done when:** a public dashboard URL shows today's live Mumbai heat map.

## P4 — Safety features

- Team mode: supervisor adds a crew, receives crew schedule and a compliance log (PDF/CSV).
- Cooling and water map: OpenStreetMap drinking water / shelters + user-submitted places with moderation; "Water near me".
- Warm-night alert.
- Acclimatisation tracker: stricter limits for the first 14 days or after time away.
- Weekly heat-exposure summary per user.

**Done when:** each feature is live in the bots and visible on the dashboard where relevant.

## P5 — Street-level ML model

- Feature extraction (Google Earth Engine): land-surface temperature, NDVI, built-up density, distance to sea, elevation for a ~100 m Mumbai grid.
- Training data: collected station readings vs forecast; model learns the local correction.
- LightGBM model; validation by holding out whole stations; SHAP explanations.
- Deep evaluation in focus wards M/E, L, G/N, K/E, A and P.
- Model output feeds alerts and the dashboard; automatic fallback to raw forecast if the model fails checks.
- Forecast accuracy page: forecast vs observed, updated daily.

**Done when:** downscaled WBGT is live and the accuracy page shows it beating the raw forecast (or honestly shows where it does not).

## P6 — Platform extras

- Public REST API with keys and rate limits; embeddable heat widget.
- Plain-English Q&A assistant, restricted to the risk engine's numbers and safety guidance.
- Event / sports organiser mode.
- Heat-insurance style trigger alerts (threshold exceeded for N hours).

## P7 — Launch hardening

- Privacy policy, consent flow, data retention (DPDP Act 2023).
- Backups and restore test; rate limiting; abuse protection.
- Load test for city-wide alert bursts at 06:00.
- User guide, outreach material, short demo video.

## Proposed tech stack (to approve)

| Part | Choice | Why |
|---|---|---|
| Language | Python 3.12 | WBGT engine and ML already in Python |
| API | FastAPI | Fast, typed, auto API docs |
| Bots | python-telegram-bot; WhatsApp Cloud API over HTTPS | Mature, free |
| Database | PostgreSQL + PostGIS | Spatial queries on grid cells |
| Jobs | APScheduler inside the service (P1); move to a queue only if needed | Fewer moving parts |
| Dashboard / web | React + Vite + MapLibre | Free, no map API key needed |
| ML | LightGBM, Google Earth Engine, SHAP | Free for research |
| Hosting | Oracle Cloud Always Free VM (always on) + Docker Compose; static web on Cloudflare Pages | Free; free tiers that sleep would miss the 06:00 alerts |
| Monitoring | Health checks + Telegram alerts to you; UptimeRobot free | Free |

Estimated running cost: ₹0 / month, plus an optional domain (~₹700–1,000 / year).
