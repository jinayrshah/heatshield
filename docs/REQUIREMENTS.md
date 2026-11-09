# HeatShield — Requirements (living document)

Decisions agreed in the planning thread. Update this file whenever a decision changes.

## 1. Project context

| Item | Decision |
|---|---|
| Type | Final-year B.Tech major project |
| Duration | 2 semesters |
| Team | 1 (solo) |
| Primary goal | A working, end-to-end product **deployed for real-world use** |
| Later (not now) | Research paper, publication, formal evaluation write-up |
| Angle | Product first |
| Budget | ≤ ₹1,500–2,000 total |
| Starting city | Mumbai (system must work for any location) |

## 2. Users

Broad, not tied to one NGO or employer:

- **Outdoor workers**: construction, delivery riders, vendors, drivers, security, sanitation, farm workers.
- **Supervisors / employers**: anyone responsible for a crew.
- **General public**: people planning outdoor activity (commuters, runners, parents, event organisers).
- **City / health officials, researchers**: read-only dashboard and open data.

## 3. Scope decisions

| Area | Decision |
|---|---|
| Language | English only for now (design so more can be added later) |
| Channels | Telegram bot (primary demo), WhatsApp (Cloud API) where budget allows; web app |
| Hardware sensors | **Out of scope for now.** Parked for later; architecture keeps a slot for them |
| Street-level ML model | In scope. Ground truth from public stations (CPCB, IMD) and satellite data, since own sensors are parked |
| Personal alerts + risk engine | In scope |
| Dashboard | In scope |
| Voice calls / SMS / regional languages | Later |

## 4. Feature tiers

### Must have (core product)
- Sign-up through the bot: location (pin or area name), work type, usual work hours.
- Daily morning alert: today's heat risk, dangerous hours, work/rest schedule, water guidance.
- Peak-hour reminders when risk is high or extreme.
- `/now` instant check for any location.
- "Plan my day": the safest windows for a task of a given length and effort.
- 3–7 day heat outlook.
- Symptom check flow with first aid and emergency numbers (108 / 112).
- Pause, stop and change settings at any time.
- Works for any location (Open-Meteo is global); Mumbai is the showcase.
- Web dashboard: WBGT map, hotspots, alert statistics.
- Street-level WBGT model for Mumbai.
- Deployed, monitored, with a heartbeat alert if the daily job fails.

### Should have (make it stand out)
- Supervisor / team mode: one person registers a crew, gets the crew schedule and a compliance log.
- Cooling and water map: drinking water, shade, cooling points (OpenStreetMap + user-submitted).
- Warm-night alert: nights too hot for the body to recover.
- Acclimatisation tracker: stricter limits for the first 1–2 weeks or after time away.
- Weekly heat-exposure summary per user.
- Forecast accuracy page: forecast vs observed station data.
- Public API and an embeddable widget.
- Progressive web app for people who use neither bot.

### Could have (if time allows)
- AI question answering in plain English, limited to the risk engine's numbers.
- Event / sports organiser mode.
- Heat-insurance style trigger alerts.
- Regional languages, SMS and voice calls.
- Hardware sensor nodes.

## 5. Budget plan (target ≤ ₹2,000)

| Item | Plan | ≈ Cost |
|---|---|---|
| Weather data | Open-Meteo, satellite data via Google Earth Engine | Free |
| Telegram bot | Telegram Bot API | Free |
| WhatsApp | Meta Cloud API free allowance for testing | Free–low |
| Hosting | Free tier (Render / Fly.io / Oracle Cloud always-free VM) | Free |
| Database | Postgres + PostGIS free tier (Supabase / Neon) or on the VM | Free |
| Domain (optional) | `.in` or `.com` | ₹700–1,000 / year |
| AI answers (optional) | Small model, capped usage | ₹0–500 |

## 6. Open questions

- Which features from "Should have" to commit to for semester 1 vs semester 2.
- Telegram only, or Telegram + WhatsApp for the final deployment.
- Whether the street-level model covers all of Mumbai or a few wards first.
