# HeatShield — Roadmap and execution plan

This is the single plan for the project. It is written so that a person or an
AI coding agent can pick up any work package and finish it without more
context. Working rules for agents are in [`CLAUDE.md`](../CLAUDE.md).

**To start a package**, say: "Do work package A2 from docs/ROADMAP.md."
One package is one pull request. When it merges, tick it in the status table
here in the same PR.

Last reviewed: 2026-11-16.

## 1. Where the project stands

| Part | State on `main` |
|---|---|
| WBGT physics (Liljegren), risk engine (NIOSH / ISO 7243), CLI | Done, tested |
| Backend API, forecast cache, accounts, alert job, web / Telegram / WhatsApp senders | Done, tested (66 tests, CI green) |
| Web app: heat now, outlook, plan a job, ward map, symptom check, water near me, alerts | Done |
| Telegram bot (conversation, commands) | **Not in the repo.** An earlier attempt was never pushed. Package A2 |
| Deployment | Not started. Package A3 |
| Station data collection | Not started, and it cannot be fully back-filled. Package A4, start first |
| WhatsApp live, team mode, accuracy page, ML model, pilot | Not started |

### Problems found in the 2026-11-16 check

| # | Problem | Handled in |
|---|---|---|
| 1 | **WBGT jumps in near-calm wind.** Same air (33.6 °C, 29 % humidity, strong sun) gives 27.6 °C at 3 m/s wind but 36.2 °C at the 0.13 m/s floor. Forecast winds often drop near zero, so real users would see false "Extreme" hours. The reference tests only go down to 0.38 m/s at night. | A1 |
| 2 | The Telegram bot does not exist in the repo, so "Connect Telegram" has nothing to connect to. | A2 |
| 3 | Tables are created with `create_all`; there are no migrations, so any schema change after launch loses or breaks data. | A3 |
| 4 | No rate limiting, security headers, privacy page or consent record. Fine for a demo, not for public users. | A5 |
| 5 | The alert job runs inside the web process, so the service must run with exactly one worker or alerts are sent twice. (The unique key on alerts prevents duplicates in the database, but two workers still race.) | A3 |
| 6 | Searching a Mumbai area returns the centre of its ward, not the area itself. Harmless at ~10 km forecast resolution; must be fixed before the street-level model. | C3 |
| 7 | Live Open-Meteo, map tiles, Overpass and real Telegram / WhatsApp sends have never been exercised end to end (the build sandbox blocks them). | A3 smoke test |
| 8 | Focus ward "P" in older notes means **P/S** (Goregaon, Aarey); BMC has P/N and P/S. Code already uses P/S. | Fixed in docs |

## 2. Things only Bhagya can do

These block packages. The long-lead ones are marked; start them now.

| # | Task | Blocks | Lead time |
|---|---|---|---|
| H1 | Create a Telegram bot with @BotFather; save the token and username | A2 | 5 min |
| H2 | **Meta Business account, WhatsApp Cloud API test number, submit one utility template** with a single body variable | B1 | Days to weeks |
| H3 | Sign up for Oracle Cloud Always Free and create an Ubuntu ARM VM (4 OCPU / 24 GB is free). If sign-up or capacity fails, use Google Cloud `e2-micro` (always free) | A3 | 1 hour to days |
| H4 | data.gov.in account and API key (CPCB station data) | A4 | 10 min |
| H5 | **Register a Google Earth Engine project for non-commercial / academic use** | C1 | Up to a few days |
| H6 | Ask the repo owner (`jinayrshah`) to add `Bhagya-Shah` as a collaborator, so reviews can be requested | Reviews | 5 min |
| H7 | Recruit 15 to 30 pilot users (campus security, gardeners, canteen and construction staff, delivery riders) | D1 | Weeks |
| H8 | Confirm review and submission dates with the project guide, so section 3 can be adjusted | Timeline | — |

Secrets go in the server's `.env` or GitHub Actions secrets, never in the repo or in chat.

## 3. Timeline

Assumes two semesters ending around April to May 2027; adjust after H8.
Mumbai's heat peaks March to May, so the pilot must be running by early March.

| When | Stage | Outcome |
|---|---|---|
| Nov to mid-Dec 2026 | **A. Live and trustworthy** | Public URL, correct numbers, Telegram alerts working, station data accumulating |
| mid-Dec to Jan | **B. Reach and safety features** | WhatsApp, web push, team mode, accuracy page |
| Jan to Feb 2027 | **C. Street-level model** | Downscaled WBGT live with an honest accuracy comparison |
| Mar to Apr 2027 | **D. Pilot and write-up** | Real users in heat season, survey results, demo, report |

## 4. Status

| Package | Title | Needs | Status |
|---|---|---|---|
| A1 | Fix and validate WBGT in low wind | — | ☐ |
| A2 | Telegram bot | H1 | ☐ |
| A3 | Deploy with migrations and monitoring | H3, A2 preferred | ☐ |
| A4 | Station and forecast data collector | H4 (partly) | ☐ |
| A5 | Public-launch hardening and privacy | A3 | ☐ |
| B1 | WhatsApp, on a shared conversation core | H2, A2 | ☐ |
| B2 | Web push notifications and offline shell | A3 | ☐ |
| B3 | Team (supervisor) mode | A5 | ☐ |
| B4 | Forecast accuracy page | A4 + 2 weeks of data | ☐ |
| B5 | Weekly summary, return-to-heat, user-added water points | A5 | ☐ |
| C1 | Satellite feature grid | H5 | ☐ |
| C2 | Train and evaluate the downscaling model | C1, A4 + 6 weeks of data | ☐ |
| C3 | Serve the model in alerts and the map | C2 | ☐ |
| D1 | Pilot tooling and feedback | A5, H7 | ☐ |
| D2 | Hindi and Marathi | B1 | ☐ |
| D3 | Platform extras (API keys, widget, Q&A, events, triggers) | A5 | ☐ |
| D4 | Launch checks, evaluation report, demo | everything used in the demo | ☐ |

A1, A2 and A4 do not touch the same files and can run at the same time.
A2, A5, B1 and B3 all edit `backend/main.py` and `backend/db.py`; run them one after another.

---

## 5. Work packages

Each package lists what to build, the decisions already made, and "done when"
checks that must all be shown in the PR description.

### A1 — Fix and validate WBGT in low wind

**Why:** problem 1 above. This is a safety number; do it before real users.

- Reproduce: `outdoor_wbgt(33.6, 29, w, 759, 0.85, 0.75, 1012)` for `w` in 0.13, 0.3, 0.5, 1, 2, 3.
- Find out what established implementations do with calm winds and with the 10 m to 2 m conversion: Liljegren's original C code (stability-based wind estimate and its minimum speed), ECMWF `thermofeel`, Kong and Huber (2022) "Explicit calculations of WBGT compared with approximations and why it matters for labor productivity", and the US NWS WBGT method. Cite what you find; do not invent a number.
- Choose a floor and conversion from that evidence. Make the floor a named constant with the citation beside it. If sources disagree, pick the one used operationally and say so.
- Extend `tests/test_wbgt.py` with reference cases at low wind in daytime, and a test that WBGT changes smoothly (no jump larger than about 1.5 °C between 0.5 and 1 m/s for the case above).
- Re-run the recorded sample (`backend/data/sample_forecast_mumbai.json`) and report in the PR how many hours changed level before and after, per level.
- Update the README claim about validation so it states exactly what was compared.

**Done when:** new tests pass; the PR shows the before/after level counts; `docs/ARCHITECTURE.md` "Key design decisions" has a row for the wind treatment with its source.
**Do not:** change NIOSH limits or the risk bands in `risk.py`.

### A2 — Telegram bot

**Needs:** H1 for a live test; build and unit-test without it.

**Decisions:** no extra library: use plain HTTPS calls like the existing `TelegramChannel`. Receive updates by **webhook** at `POST /api/telegram/webhook/{secret}` (secret from `TELEGRAM_WEBHOOK_SECRET`, also checked against the `X-Telegram-Bot-Api-Secret-Token` header). For local development add `python -m backend.bot poll`, which uses `getUpdates` and feeds the same handler. Add `python -m backend.bot set-webhook <public-url>`.

Build `backend/conversation.py` as a **channel-neutral core**: input is `(channel, sender_id, text or location or button id)`, output is a list of messages with optional buttons. Telegram is the first adapter; WhatsApp (B1) reuses the core unchanged. Keep per-user conversation state in a new `conversations` table (`channel`, `sender_id`, `state`, `data` JSON, `updated_at`).

Flows (English, plain words, short messages):
- `/start <code>`: link to an existing web account with `messaging.link_telegram`. `/start` alone: sign-up. Ask for location (share a pin, or type an area: reuse the `/api/geocode` logic), type of work (4 buttons with examples), usual hours, "new to working in the heat?". Show a one-line privacy note and require "I agree". Create a `User` (with a random token so the same account can later be opened on the web).
- `/now`, `/today`, `/outlook` (7 days), `/plan` (ask hours, answer with best windows from `service.plan_windows`).
- `/unwell`: the symptom flow from `backend/content.py`, one question at a time, 108 / 112 always shown.
- `/settings` (place, work type, hours, new to heat, which alerts), `/pause`, `/resume`, `/stop` (delete all data after a confirm), `/help`.
- Unknown text: a short help reply. Never answer medical questions freely.

Reuse `service.py` and the renderers in `messaging.py`; add renderers there rather than formatting in the bot. Make `User.telegram_chat_id` unique when not empty.

**Done when:** tests drive every flow through the core with a fake sender (sign-up, link by code, each command, pause, stop, bad input, expired state); webhook rejects a wrong secret; a morning alert reaches a linked chat in a test using the existing channel; README has a "Telegram bot" section with BotFather steps. If H1 is done, include a screenshot or transcript of a real chat.

### A3 — Deploy with migrations and monitoring

**Needs:** H3. Prefer after A2 so the webhook goes live in the same step.

- **Alembic**: add migrations; first revision equals the current models. The app runs `alembic upgrade head` on start; remove `create_all` outside tests.
- **Docker**: multi-stage `Dockerfile` (Node builds `web/dist`, Python image serves it). Run `uvicorn backend.main:app --workers 1` and write the reason in a comment (problem 5).
- **`docker-compose.yml`**: `app`, `postgres:16` with a volume, `caddy` for automatic HTTPS. Without a paid domain use a free DuckDNS name or `<ip>.sslip.io`.
- **Postgres** through `DATABASE_URL` (`psycopg`). PostGIS is not needed until C3; do not add it now.
- **Backups**: nightly `pg_dump` kept for 14 days, plus a documented and tested restore.
- **Deploy**: `scripts/deploy.sh` (ssh, pull, build, migrate, restart) and a manually triggered GitHub Action that runs it with repository secrets.
- **Monitoring**: UptimeRobot free on `/api/health`; set `OPERATOR_TELEGRAM_CHAT_ID`. Make `/api/health` return HTTP 503 when `alert_job_healthy` is false so the monitor can see it.
- **Map tiles**: the OpenStreetMap tile server is not meant for production traffic. Switch the web map to a free hosted vector style (OpenFreeMap, no key) and keep OSM raster only as a fallback.
- `docs/DEPLOY.md`: every step from a fresh VM, written for someone who has not used a server before.

**Done when:** the public URL serves the app over HTTPS; a live-data smoke test is recorded in the PR (forecast for a Mumbai point, place search, water points, map tiles, sign-up, preview alert, Telegram alert if A2 is in); a restart keeps accounts; a backup was restored once; the monitor fires when the job is stopped on purpose.

### A4 — Station and forecast data collector

**Why first:** the model (C2) and the accuracy page (B4) need weeks of history.

- Research and confirm, with links in the PR, which free sources give hourly **observed** air temperature, humidity and wind for Mumbai. Candidates to verify, not assume: CPCB continuous air-quality stations (via data.gov.in or the CPCB portal; many Mumbai stations report temperature, humidity, wind and solar radiation), METAR for Mumbai airport VABB (near K/E), Meteostat hourly for IMD Santacruz and Colaba, IMD automatic weather stations.
- Tables: `stations` (id, source, name, lat, lon, ward, active), `observations` (station, time UTC, air °C, RH, wind m/s, solar, pressure, raw JSON; unique on station and time), `forecast_archive` (cell, issued-at, valid time, the six forecast variables, lead hours).
- Jobs in `backend/collect.py`, scheduled hourly: fetch new observations; store the forecast issued now for every station cell for the next 48 hours. One failing source must not stop the others; record each run in `job_runs` and tell the operator after three failures in a row.
- Back-fill what the sources allow (state the limit of each). For past forecasts check the Open-Meteo Historical Forecast API.
- Quality flags: out-of-range values, stuck sensors (same value for 6 hours), gaps. Keep raw values; flag rather than delete.
- Mark which stations sit in or beside the six focus wards (M/E, L, G/N, K/E, A, P/S) and record that list in `docs/REQUIREMENTS.md` section 6 ("Station locations to be confirmed").
- A small `GET /api/stations` and a table on the About page with last reading and age.

**Done when:** tests cover parsing for each source from saved real responses, de-duplication and quality flags; the PR lists stations found per focus ward and any ward with none; after deploy, the table shows fresh readings.

### A5 — Public-launch hardening and privacy

- Rate limits per IP (in memory is fine at this scale): sign-up, geocode, water, preview alert. Cap accounts per IP per day.
- Security headers (CSP that allows only the tile host, `X-Content-Type-Options`, `Referrer-Policy`), request size limit, no stack traces in responses.
- `Privacy` and `Terms` pages in the web app in plain language, aligned with India's DPDP Act 2023: what is stored (area to ~1 km, work type, hours, chat id or number if given), why, how long, how to delete, contact. Store consent time and policy version on the user.
- Data retention: delete alerts older than 90 days; delete accounts with no activity for 12 months after one warning.
- Operator page at `/#/admin`, opened with `ADMIN_TOKEN`: job runs, failures by channel, users by ward (counts only), stale forecast cells. No personal data.
- Structured JSON logs without tokens, phone numbers or coordinates.
- Accessibility pass on the web app to WCAG 2.1 AA: keyboard path through every page, contrast in both themes, screen-reader labels on the chart and map alternatives.

**Done when:** tests prove each limit and header; the admin page needs the token; a test shows logs contain no secrets; the accessibility findings and fixes are listed in the PR.

### B1 — WhatsApp, on the shared conversation core

**Needs:** H2, A2.

- `POST/GET /api/whatsapp/webhook` (verification handshake, signature check with the app secret). Adapter maps WhatsApp messages, buttons and shared locations to the core from A2.
- Outbound: inside the 24-hour customer window send normal text; outside it send the approved template (already in `WhatsAppChannel`). Track the window per user.
- "STOP" in any case pauses immediately; "START" resumes.
- Web sign-up: number entry leads to an opt-in message link (`wa.me/<number>?text=JOIN`); a number is only used after the user messages first.
- `docs/WHATSAPP.md`: the exact template text to submit, and the Meta set-up steps.

**Done when:** tests replay saved webhook payloads through sign-up, a command, STOP and an out-of-window send; a real message round trip is shown if H2 is complete, otherwise the PR says clearly that it is untested live.

### B2 — Web push notifications and offline shell

- Service worker with an offline shell and the last fetched forecast for the saved place ("last updated" clearly shown; never present old data as current).
- Web Push with VAPID keys (free, no third party): `push_subscriptions` table, a `WebPushChannel` beside the others, "Turn on notifications" in My alerts, removal of dead subscriptions.

**Done when:** a test sends through a fake push service and handles "gone" subscriptions; installing and receiving a notification is shown on Android Chrome; iOS limits are documented.

### B3 — Team (supervisor) mode

- A user can create a crew: name, site location, work type, shift hours; members by name (no account needed), optionally linked to their own Telegram or WhatsApp.
- Supervisor receives the crew's morning schedule and peak reminders; web page shows today's work and rest plan for the site, printable on one page.
- Compliance log: for each day, forecast peak, hours over the limit, the advised schedule, alerts sent. Export CSV and PDF.
- Members can leave; deleting a crew deletes its members' data.

**Done when:** tests cover crew lifecycle, permissions (only the supervisor sees the crew), exports and deletion.

### B4 — Forecast accuracy page

**Needs:** A4 with at least two weeks of data.

- Nightly job joins `forecast_archive` with `observations`: error in air temperature, humidity and wind at 6, 24 and 48 hour leads; WBGT computed from observed values against WBGT from the forecast; how often the risk level matched, was too high, or too low. "Too low" (under-warning) is the number that matters most; show it first.
- Web page: one chart per measure with the method explained in two sentences, per-station table, date range. Follow the chart rules already used in `HourChart.tsx`.
- State limits honestly: stations measure shaded air, not WBGT, so observed WBGT is itself an estimate (no globe thermometer).

**Done when:** metric code is tested on a small hand-checked data set; the page shows real numbers from the deployed collector.

### B5 — Weekly summary, return-to-heat, user-added water points

- Weekly message (Sunday evening): hours at each level during the user's working hours, hottest day, tip for next week.
- Acclimatisation: ask "been away from hot work for a week or more?" in settings and the bot; if yes, apply stricter limits for 7 days. Cite the NIOSH acclimatisation schedule in the code comment.
- Users can add a water or shade point (place on map, type, note). It appears after operator approval on the admin page. Report button on each point.

**Done when:** tests cover each; moderation cannot be bypassed.

### C1 — Satellite feature grid

**Needs:** H5.

- A script in `ml/features/` that builds a ~100 m grid over the BMC boundary (from `backend/data/bmc_wards.geojson`) and exports per cell: summer daytime land-surface temperature (Landsat 8/9, March to May composite, cloud-masked), night LST (MODIS or ECOSTRESS if usable), NDVI and NDBI (Sentinel-2), built-up fraction and tree cover (ESA WorldCover), elevation (SRTM), distance to coast, distance to large water or mangrove, and ward id.
- Output one Parquet file (about 50,000 rows, a few MB) committed under `ml/data/`, with a data card: sources, dates, licences, known gaps.
- A notebook or script producing sanity maps of each feature (saved as PNG in `docs/img/`).

**Done when:** the script runs from a clean checkout with only an Earth Engine login; the data card is complete; maps look right against known places (Aarey cool and green, Deonar and Dharavi hot and built).

### C2 — Train and evaluate the downscaling model

**Needs:** C1, A4 with at least six weeks of data (more is better; retrain in April).

**Framing, to keep the claim honest:** a handful of stations cannot teach a model 100 m WBGT directly. Build it in two steps and report both.
1. **Bias correction at stations:** predict observed air temperature, humidity and wind from the forecast values, hour, month and lead time (LightGBM, or simpler if it wins).
2. **Spatial adjustment:** predict each station's typical departure from the city-wide mean by hour of day from its grid features (strongly regularised; few stations). Apply to every cell to get a local offset to air temperature and humidity, then compute WBGT with the existing physics. The physics stays; the model only adjusts its inputs.

- Validation: leave-one-station-out, and a time split (train on earlier weeks, test on later). Compare against the raw forecast baseline with RMSE, MAE and bias per station and for the six focus wards; report under-warning rate for risk levels.
- SHAP summary for both steps. Uncertainty: report the spread across left-out stations.
- If the model does not beat the baseline for a variable, say so and ship the baseline for that variable.
- Everything reproducible: `python -m ml.train` writes a model file, a metrics JSON and plots; fixed seeds; `ml/README.md` explains each step.

**Done when:** the metrics table and plots are in the PR and in `docs/MODEL.md`; tests cover the feature join and the "fall back to baseline" rule.

### C3 — Serve the model in alerts and the map

- Precompute per-cell offsets by hour of day and month into a compact table shipped with the app (no heavy model at request time).
- `weather.py` applies the cell's offset after the forecast is fetched; responses say `"source": "open-meteo+downscaled"`. Automatic fallback to the raw forecast if the offset is missing or out of bounds (limit: ±5 °C), with a counter visible on the admin page.
- Fix problem 6: geocode Mumbai areas to their own coordinates.
- Map: replace ward fill with a ~250 m grid layer (ward outlines kept), ward ranking from cell means, a toggle "forecast only / street-level".
- About page: plain-language explanation and link to the accuracy page.

**Done when:** tests cover offset application, bounds and fallback; map performance is acceptable on a mid-range phone (record a measurement); alerts for two contrasting cells (Aarey vs Dharavi) differ in a test using fixed inputs.

### D1 — Pilot tooling and feedback

**Needs:** H7. Target: users enrolled by early March 2027.

- One-page onboarding sheet with QR codes for the web app and Telegram (printable, English first).
- In-chat and in-app feedback: after the 3rd and 10th alert ask two questions (understood? did you change anything today?) with one-tap answers.
- Pilot dashboard on the admin page: enrolled, active, alerts delivered, feedback answers, opt-outs. Export CSV for the report.
- A short survey (10 questions) as a web form storing anonymous answers.

**Done when:** a dry run with 3 test accounts produces the dashboard and export.

### D2 — Hindi and Marathi

- Move every user-facing string (web and messages) into translation files; language choice at sign-up and in settings.
- Draft translations may come from a model, but **safety text must be reviewed by a fluent speaker before release**; mark unreviewed strings and do not ship them.
- Numbers, times and units stay consistent across languages.

**Done when:** tests fail on any missing key; a reviewer sign-off list is in the PR.

### D3 — Platform extras

Build in this order and stop when time runs out; each is its own PR.
1. Public API keys with per-key limits, and an embeddable widget (`<iframe>` with today's risk for a place).
2. Trigger alerts: "tell me when WBGT stays above X for N hours" (the heat-insurance style trigger).
3. Event mode: a date, place and activity level give a go / adjust / postpone recommendation with the reasoning.
4. Plain-language Q&A limited to the engine's numbers and the safety content: use the smallest current Claude model, a hard monthly spending cap, refusal for medical questions, and logging of every answer for review. Read the `claude-api` skill before writing any code for this.

### D4 — Launch checks, evaluation report, demo

- Load test: 2,000 users spread over 200 cells, all due at 06:00; alerts finish within 10 minutes; fix what breaks (batching, per-channel rate limits).
- Restore test from backup on a fresh VM, timed.
- `docs/EVALUATION.md` generated from data: model accuracy, alert correctness, delivery rates, pilot feedback, uptime. This is the source for the report and the later paper.
- A 3-minute demo script and screenshots; a user guide page.

---

## 6. Decided tech stack

| Part | Choice |
|---|---|
| Language, API | Python 3.12, FastAPI |
| Database | SQLite for development, PostgreSQL in production (PostGIS only if C3 needs it) |
| Jobs | APScheduler inside the single web worker |
| Web | React, TypeScript, Vite, MapLibre |
| Bots | Direct HTTPS to Telegram Bot API and WhatsApp Cloud API, one shared conversation core |
| ML | LightGBM, SHAP, Google Earth Engine |
| Hosting | One free VM (Oracle Always Free, else Google `e2-micro`) with Docker Compose and Caddy |
| Monitoring | `/api/health`, UptimeRobot free, Telegram message to the operator |

Running cost target: ₹0 per month, plus an optional domain.

## 7. Parked

Hardware sensor nodes (ESP32 with a black globe), SMS and voice calls. The
architecture keeps a place for them (`firmware/`, channel adapters), but nothing
in this plan depends on them.
