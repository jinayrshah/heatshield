# HeatShield — Solo Roadmap (~6 months)

Mumbai's heat peaks **March–May** and again in **October**; the monsoon
(June–September) is cooler but very humid. Plan sensor data collection around
those windows.

| Month | Milestone | Done when |
|---|---|---|
| 1 | Literature review; WBGT engine + risk engine + CLI | ✅ tests pass; CLI prints Mumbai hourly risk |
| 1 | Order sensor parts (ESP32, SHT31, DS18B20, black globe, radiation shield) | Parts in hand |
| 2 | Build 1st sensor node; MQTT ingest; FastAPI + PostGIS skeleton | Node posts readings to DB |
| 2 | Telegram/WhatsApp sandbox bot: sign-up (language, workload, area) + morning alert | You receive your own 6 am alert |
| 3 | 3–5 sensors deployed (e.g. tree-lined road, market, construction site, seafront, tin-roof area) | ≥ 2 weeks of data |
| 3 | Earth Engine feature extraction (LST, NDVI, built-up, distance to sea) for Mumbai grid | Feature table on disk |
| 4 | Train LightGBM downscaler; evaluate vs sensors (RMSE raw vs downscaled); SHAP | Results table + plots |
| 4 | Hindi + Marathi messages (IndicTrans2 / Bhashini), SMS fallback, voice call prototype | Alert in 3 languages |
| 5 | Dashboard: WBGT map + hotspots + water-point placement | Deployed URL |
| 5 | Pilot with 15–30 users (campus staff / NGO / site) | Delivery + survey data |
| 6 | Report, paper draft, demo video, final deploy | Submitted |

## Bill of materials per sensor node (approx.)

| Part | ≈ ₹ |
|---|---|
| ESP32 dev board | 400 |
| SHT31 temp/RH sensor | 350 |
| DS18B20 probe + 40 mm matte-black ball (globe) | 250 |
| Radiation shield (stacked plates / DIY) | 200 |
| 18650 battery + holder + small solar panel / USB | 600 |
| Enclosure, wiring | 200 |
| **Total** | **~2,000** |
