# backend/

FastAPI service: forecasts, risk, accounts, the alert job and delivery channels.
It also serves the built web app from `web/dist`, so one process runs everything.

| File | What it does |
|---|---|
| `main.py` | API routes (`/api/...`) and the web app. Interactive docs at `/api/docs`. |
| `weather.py` | Open-Meteo client for any location, ~1 km cell cache, stale fallback, offline sample. |
| `service.py` | Hourly rows, day summaries (dangerous hours, warm nights) and "plan a job". |
| `jobs.py` | Alert job every 30 min: 06:00 morning alert, peak reminders, warm-night alert, heartbeat. |
| `messaging.py` | Alert text, and the web, Telegram and WhatsApp channels. |
| `db.py` | Users, alerts, anonymous counters, job runs (SQLite or Postgres). |
| `wards.py`, `data/` | Mumbai BMC ward boundaries and the recorded sample forecast. |
| `content.py` | First-aid symptom flow and emergency numbers. |

## Main endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/forecast?lat&lon&workload&acclimatised` | Now, hourly rows and 7-day summaries |
| `GET /api/plan?lat&lon&duration_hours&day` | Best non-overlapping time windows for a job |
| `GET /api/city?workload` | 48 hours of WBGT and risk for all 24 wards |
| `GET /api/geocode?q` | Mumbai areas (offline) plus Open-Meteo place search |
| `GET /api/water?lat&lon` | Drinking water, shelters and hospitals from OpenStreetMap |
| `POST /api/users` | Sign up; returns a device token (no password) |
| `GET/PATCH/DELETE /api/me` | Settings, pause, delete all data |
| `GET /api/me/alerts`, `POST /api/me/alerts/preview` | Inbox; send today's alert now |
| `GET /api/stats`, `GET /api/health` | Anonymous totals; alert-job heartbeat |

## Telegram linking

Each web account gets a one-time code. "Connect Telegram" opens
`t.me/<bot>?start=<code>`; the bot's `/start` handler calls
`backend.messaging.link_telegram(session, code, chat_id)`, after which alerts
also go to that chat. The bot itself is built separately.
