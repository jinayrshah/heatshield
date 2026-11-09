# HeatShield — Project Proposal

**Domain:** Climate (climate adaptation × public health)
**Pilot city:** Mumbai
**Team:** 1 (solo)

## 1. Problem

Extreme heat is the deadliest weather hazard, and it is getting worse across India.
The people most exposed are outdoor informal workers — construction labourers,
street vendors, delivery riders, sanitation and port workers — who cannot stop work
and often have only a basic phone.

Mumbai is a particularly important case: its air temperature rarely looks extreme
(often 32–36 °C), but its **humidity** is very high. Sweat cannot evaporate, so the
body cannot cool itself. Air-temperature-based warnings systematically
**under-warn** humid coastal cities. This is exactly what WBGT captures.

## 2. Why WBGT

```
Outdoor WBGT = 0.7 × natural wet-bulb  +  0.2 × globe temp  +  0.1 × air temp
               (humidity + wind)          (sun / radiation)
```

WBGT is the measure used by ISO 7243, NIOSH, ACGIH, militaries and sports bodies.
Combined with workload (how hard the job is), it gives a defensible safe work/rest
schedule.

## 3. Gap in existing solutions

| Existing | What it misses |
|---|---|
| Weather apps | Air temp / heat index only, no work guidance, smartphone + English |
| IMD / city heat warnings and Heat Action Plans | District-level, air-temperature based, same message for everyone |
| OSHA-NIOSH Heat Safety Tool | US-centric, smartphone only, heat index not WBGT |
| Research heat-island maps | Historical maps, not operational alerts |

**Nobody combines:** street-level WBGT + workload-specific advice + local language +
feature-phone delivery + ground-truth validation.

## 4. Solution — four parts

1. **WBGT engine + street-level ML model** — compute WBGT from forecasts, then
   downscale from ~10 km to ~100 m using satellite land-surface temperature,
   vegetation (NDVI), built-up density and distance to the sea.
2. **Low-cost WBGT sensors** — 3–5 ESP32 nodes (~₹2,000 each) at contrasting Mumbai
   sites for ground truth and model validation.
3. **Personal alerts** — risk engine (NIOSH limits by workload and
   acclimatisation) → WhatsApp / SMS / voice in Hindi and Marathi (AI4Bharat /
   Bhashini), with an SMS reply channel for symptoms.
4. **Dashboard** — live WBGT map, hotspot ranking, water-point placement
   suggestions, employer compliance export.

## 5. Novel contributions

1. Street-level WBGT model for Mumbai, validated against self-built sensors.
2. Open-source low-cost WBGT sensor design.
3. Standards-based (NIOSH/ISO 7243) work/rest alerts, multilingual, feature-phone friendly.
4. Water-point placement optimisation for heat officers.
5. A real deployment with pilot metrics.

## 6. Evaluation

| What | Metric |
|---|---|
| Model accuracy | RMSE/MAE vs sensors: raw forecast WBGT vs downscaled WBGT |
| Alert correctness | Precision/recall of high-risk hours vs measured WBGT |
| Reach | Delivered / read / answered rates |
| Usefulness | Pilot user survey (understood? changed behaviour?) |
| Reliability | Pipeline uptime, alert latency |

## 7. Scope for a solo developer

Core (must ship): Parts 1 (forecast WBGT + ML downscaling) and 3 (alerts).
Strong add (should ship): Part 2 with 3 sensors.
Lightweight (could ship): Part 4 as a single map page + one optimisation view.
Stretch (only if ahead): voice Q&A assistant, heat-insurance trigger.

## 8. Ethics and privacy

- Collect only phone, language, workload, coarse location (grid cell, never live GPS).
- Explicit consent in the user's language; STOP to opt out. DPDP Act 2023 aligned.
- Not medical advice; severe-symptom replies always direct to 108/112.
- Rate-limit alerts to avoid fatigue; address employers too, not only workers.

## 9. Risks

| Risk | Mitigation |
|---|---|
| No partner NGO | Pilot on own campus (security, gardening, construction staff) |
| WhatsApp Business / DLT approval delays | Telegram + Twilio sandbox for demo |
| Too few sensors for ML | Add CPCB station temp/RH and IMD AWS data as ground truth |
| Monsoon (Jun–Sep) reduces heat signal | Collect data Mar–May and Oct ("October heat") |

## 10. Key references

- Liljegren et al. (2008), *Modeling the WBGT using standard meteorological measurements*, JOEH 5(10).
- NIOSH (2016), *Criteria for a Recommended Standard: Occupational Exposure to Heat and Hot Environments*.
- ISO 7243:2017, *Ergonomics of the thermal environment — WBGT index*.
- NDMA Heat Wave Guidelines; Ahmedabad Heat Action Plan (2013); Mumbai Climate Action Plan.
- Lancet Countdown on Health and Climate Change (annual reports).
