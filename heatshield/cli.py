"""Command line: print today's hourly heat risk for a city and workload.

    python -m heatshield.cli --city mumbai --work heavy
"""

from __future__ import annotations

import argparse
import sys

from .forecast import CITIES, ForecastError, compute_hourly_wbgt, fetch_open_meteo
from .risk import METABOLIC_RATE_W, assess

LEVEL_LABEL = {"safe": "SAFE", "caution": "CAUTION", "high": "HIGH", "extreme": "EXTREME"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HeatShield hourly heat-stress forecast")
    parser.add_argument("--city", default="mumbai", choices=sorted(CITIES))
    parser.add_argument("--work", default="heavy", choices=[k for k in METABOLIC_RATE_W if k != "rest"])
    parser.add_argument("--days", type=int, default=1, choices=range(1, 8))
    parser.add_argument("--unacclimatised", action="store_true", help="new to the heat (e.g. first 1-2 weeks)")
    args = parser.parse_args(argv)

    city = CITIES[args.city]
    try:
        hours = compute_hourly_wbgt(fetch_open_meteo(city, days=args.days), city)
    except ForecastError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not hours:
        print("error: forecast contained no usable hours", file=sys.stderr)
        return 1

    acc = not args.unacclimatised
    print(f"HeatShield — {city.name}, workload: {args.work}, {'acclimatised' if acc else 'NOT acclimatised'}")
    print(f"{'time':<17}{'air':>6}{'RH':>5}{'sun':>6}{'globe':>7}{'Tnwb':>6}{'WBGT':>6}  {'risk':<8}work/rest per hour")
    for h in hours:
        a = assess(h.wbgt_c, args.work, acclimatised=acc)
        print(
            f"{h.time_local:%a %d %b %H:%M} {h.air_c:>5.1f}{h.rh_pct:>5.0f}{h.solar_wm2:>6.0f}"
            f"{h.globe_c:>7.1f}{h.natural_wet_bulb_c:>6.1f}{h.wbgt_c:>6.1f}  {LEVEL_LABEL[a.level.value]:<8}"
            f"{a.work_minutes_per_hour:>2} min work / {a.rest_minutes_per_hour:>2} min rest"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
