"""Turn a WBGT value into worker-level risk and a work/rest recommendation.

Exposure limits follow NIOSH (2016) Criteria for a Recommended Standard:
Occupational Exposure to Heat and Hot Environments, which match ISO 7243:2017:

    Acclimatised   (REL): WBGT_limit = 56.7 - 11.5 * log10(M)
    Unacclimatised (RAL): WBGT_limit = 59.9 - 14.1 * log10(M)

where M is the metabolic rate in watts. Work/rest is derived by finding the
time-weighted metabolic rate the environment allows and splitting each hour
between work and rest so the average stays at that rate (NIOSH's TWA approach).
This conservatively assumes the worker rests in the same conditions; resting
in shade would allow more work.

The four risk *bands* below are HeatShield's own communication thresholds
(not part of the standard) and are meant to be tuned during the pilot.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

# ISO 7243 / ISO 8996 metabolic rate classes (W, for a 1.8 m2 person).
METABOLIC_RATE_W = {
    "rest": 115,
    "light": 180,  # e.g. vending, traffic duty, light driving
    "moderate": 300,  # e.g. delivery riding, cleaning, walking with load
    "heavy": 415,  # e.g. construction, carrying bricks, digging
    "very_heavy": 520,  # e.g. heavy shovelling, loading trucks
}
REST_W = METABOLIC_RATE_W["rest"]


class RiskLevel(str, Enum):
    SAFE = "safe"
    CAUTION = "caution"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass(frozen=True)
class RiskAssessment:
    level: RiskLevel
    wbgt_c: float
    limit_c: float
    work_minutes_per_hour: int
    rest_minutes_per_hour: int


def wbgt_limit(metabolic_w: float, acclimatised: bool = True) -> float:
    if metabolic_w <= 0:
        raise ValueError("metabolic_w must be positive")
    if acclimatised:
        return 56.7 - 11.5 * math.log10(metabolic_w)
    return 59.9 - 14.1 * math.log10(metabolic_w)


def _allowed_metabolic_rate(wbgt_c: float, acclimatised: bool) -> float:
    """Inverse of wbgt_limit: highest time-weighted metabolic rate allowed."""
    if acclimatised:
        return 10 ** ((56.7 - wbgt_c) / 11.5)
    return 10 ** ((59.9 - wbgt_c) / 14.1)


def work_fraction(wbgt_c: float, workload: str, acclimatised: bool = True) -> float:
    """Fraction of each hour that can be spent working (0-1)."""
    m_work = METABOLIC_RATE_W[workload]
    m_allowed = _allowed_metabolic_rate(wbgt_c, acclimatised)
    if m_allowed >= m_work:
        return 1.0
    if m_allowed <= REST_W:
        return 0.0
    return (m_allowed - REST_W) / (m_work - REST_W)


def assess(wbgt_c: float, workload: str, acclimatised: bool = True) -> RiskAssessment:
    if workload not in METABOLIC_RATE_W:
        raise ValueError(f"unknown workload {workload!r}; choose from {sorted(METABOLIC_RATE_W)}")
    limit = wbgt_limit(METABOLIC_RATE_W[workload], acclimatised)
    frac = work_fraction(wbgt_c, workload, acclimatised)
    # Round work time DOWN to 5-minute steps so advice is never less safe than the model.
    work_min = int(math.floor(frac * 60 / 5) * 5)

    margin = wbgt_c - limit
    if margin < -2.0:
        level = RiskLevel.SAFE
    elif margin < 0.0:
        level = RiskLevel.CAUTION
    elif work_min > 0:
        level = RiskLevel.HIGH
    else:
        level = RiskLevel.EXTREME

    return RiskAssessment(
        level=level,
        wbgt_c=round(wbgt_c, 1),
        limit_c=round(limit, 1),
        work_minutes_per_hour=work_min,
        rest_minutes_per_hour=60 - work_min,
    )
