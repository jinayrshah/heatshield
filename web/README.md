# web/

The HeatShield web app (React + TypeScript + Vite + MapLibre). Installable as a PWA.

| Page | What it does |
|---|---|
| Heat now | Risk right now, today's dangerous hours, hourly chart and table, 7-day outlook |
| Plan a job | Safest time windows for a job of N hours on a chosen day |
| City map | All 24 BMC wards coloured by risk, 48-hour time slider, hotspot ranking, usage stats |
| Feeling unwell | Step-by-step symptom check with first aid; water, shelters and hospitals near you |
| My alerts | Sign up (no password), alerts inbox, Telegram / WhatsApp, settings, pause, delete my data |

```bash
npm install
npm run dev      # http://localhost:5173, forwards /api to the backend on :8000
npm run build    # output in dist/, served by the backend
```

Risk levels always show an icon and a word next to the colour, so they never rely on colour alone.
