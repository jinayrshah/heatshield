# Working on HeatShield

HeatShield is a heat-risk alert system for Mumbai (final-year B.Tech project):
WBGT forecasts, work and rest guidance, and alerts on Telegram, WhatsApp and a
web app. People will act on its numbers in dangerous heat, so correctness and
plain wording matter more than speed.

## Read first

- `docs/ROADMAP.md`: the plan. Work is done one package at a time (A1, A2, ...).
- `docs/REQUIREMENTS.md`: decisions. `docs/ARCHITECTURE.md`: how it fits together.
- `backend/README.md` and `web/README.md`: what each file does.

## Commands

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python -m pytest -q                         # all tests, no network
(cd web && npm ci && npm run build)         # type-check and build the web app
HEATSHIELD_SAMPLE_DATA=1 uvicorn backend.main:app --reload   # run with the recorded forecast
```

## Rules

1. **One work package, one branch, one pull request.** Follow the package text in the roadmap, including its "done when" checks, and show each check in the PR description. Do not start a second package in the same PR.
2. **Run `pytest` and the web build before every push.** CI runs both.
3. **Update the docs in the same PR**: tick the package in `docs/ROADMAP.md`; record any new decision in `docs/REQUIREMENTS.md`; keep `docs/ARCHITECTURE.md` and the READMEs true.
4. **Physics and limits are protected.** Do not change `heatshield/wbgt.py`, `heatshield/risk.py` thresholds, or the first-aid text in `backend/content.py` without a cited source in the code and a test. Round towards safety (less work, never more).
5. **Never guess data.** Skip missing hours; mark stale forecasts as stale; do not invent station locations, licences or API behaviour. If a source could not be verified, say so in the PR.
6. **Privacy.** Store a ~1 km cell (2 decimals), never exact coordinates. No tokens, phone numbers or coordinates in logs. Every new stored field must be covered by "delete my data".
7. **Free tiers only.** No paid services or keys. Ask before adding a dependency that needs an account.
8. **Secrets** come from environment variables (`.env.example` lists them). Never commit or print them.
9. **One web worker.** The alert job runs inside the web process; alert sending must stay idempotent (unique user, kind, day, slot).
10. **Risk is never shown by colour alone**: always an icon and a word. Keep user-facing text short and plain; many users read English as a second language.
11. **Tests do not use the network.** Save a real response as a fixture and replay it. The build sandbox usually blocks Open-Meteo, OpenStreetMap, Overpass, Telegram and Meta, so state in the PR what was and was not tested live.
12. **Stop and ask** when a package needs something from the "Things only Bhagya can do" list that is not done, when sources disagree on a safety number, or when a change would alter what an alert tells people to do.
