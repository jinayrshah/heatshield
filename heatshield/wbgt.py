"""Outdoor Wet Bulb Globe Temperature (WBGT) from standard weather variables.

Implements the physically based model of:

    Liljegren, J. C., Carhart, R. A., Lawday, P., Tschopp, S., & Sharp, R. (2008).
    Modeling the Wet Bulb Globe Temperature Using Standard Meteorological
    Measurements. Journal of Occupational and Environmental Hygiene, 5(10), 645-655.

The model solves energy balances for a 2-inch black globe and a natural
(unventilated) wet-bulb wick, then combines them:

    WBGT = 0.7 * T_nwb + 0.2 * T_globe + 0.1 * T_air

All internal temperatures are Kelvin; the public API uses degrees Celsius.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# --- Physical constants -----------------------------------------------------
STEFAN_BOLTZMANN = 5.6696e-8  # W m-2 K-4
CP = 1003.5  # J kg-1 K-1, specific heat of dry air
M_AIR = 28.97  # kg/kmol
M_H2O = 18.015  # kg/kmol
R_GAS = 8314.34  # J kmol-1 K-1
R_AIR = R_GAS / M_AIR
PRANDTL = CP / (CP + 1.25 * R_AIR)
RATIO = CP * M_AIR / M_H2O

# --- Instrument / surface properties (Liljegren 2008, Table 1) ---------------
GLOBE_DIAMETER = 0.0508  # m
GLOBE_EMISSIVITY = 0.95
GLOBE_ALBEDO = 0.05
WICK_DIAMETER = 0.007  # m
WICK_LENGTH = 0.0254  # m
WICK_EMISSIVITY = 0.95
WICK_ALBEDO = 0.4
SURFACE_EMISSIVITY = 0.999
SURFACE_ALBEDO = 0.45

MIN_WIND = 0.13  # m/s, floor used by Liljegren to avoid a zero convective term
MIN_COS_ZENITH = 0.0174  # ~89 deg; below this treat all radiation as diffuse


@dataclass(frozen=True)
class WBGTResult:
    wbgt_c: float
    globe_c: float
    natural_wet_bulb_c: float
    air_c: float


# --- Thermophysical properties of air --------------------------------------
def _esat_hpa(t_k: float) -> float:
    """Saturation vapour pressure over water (Buck 1981), hPa."""
    t_c = t_k - 273.15
    return 6.1121 * math.exp(17.502 * t_c / (240.97 + t_c))


def _viscosity(t_k: float) -> float:
    """Dynamic viscosity of air, kg m-1 s-1."""
    sigma, eps_kappa = 3.617, 97.0
    tr = t_k / eps_kappa
    omega = (tr - 2.9) / 0.4 * (-0.034) + 1.048
    return 2.6693e-6 * math.sqrt(M_AIR * t_k) / (sigma**2 * omega)


def _thermal_conductivity(t_k: float) -> float:
    """Thermal conductivity of air, W m-1 K-1."""
    return (CP + 1.25 * R_AIR) * _viscosity(t_k)


def _diffusivity(t_k: float, p_hpa: float) -> float:
    """Diffusivity of water vapour in air, m2 s-1."""
    pcrit13 = (36.4 * 218.0) ** (1 / 3)
    tcrit512 = (132.0 * 647.3) ** (5 / 12)
    tcrit12 = (132.0 * 647.3) ** 0.5
    mmix = (1 / M_AIR + 1 / M_H2O) ** 0.5
    return 3.640e-4 * (t_k / tcrit12) ** 2.334 * pcrit13 * tcrit512 * mmix / (p_hpa / 1013.25) * 1e-4


def _heat_of_evaporation(t_k: float) -> float:
    """Latent heat of vaporisation of water, J/kg."""
    return (313.15 - t_k) / 30.0 * (-71100.0) + 2.4073e6


def _density(t_k: float, p_hpa: float) -> float:
    return p_hpa * 100.0 / (R_AIR * t_k)


def _h_sphere(t_k: float, p_hpa: float, wind: float) -> float:
    """Convective heat transfer coefficient for the globe (sphere), W m-2 K-1."""
    re = wind * _density(t_k, p_hpa) * GLOBE_DIAMETER / _viscosity(t_k)
    nu = 2.0 + 0.6 * math.sqrt(re) * PRANDTL ** (1 / 3)
    return nu * _thermal_conductivity(t_k) / GLOBE_DIAMETER


def _h_cylinder(t_k: float, p_hpa: float, wind: float) -> float:
    """Convective heat transfer coefficient for the wick (cylinder in crossflow)."""
    re = wind * _density(t_k, p_hpa) * WICK_DIAMETER / _viscosity(t_k)
    nu = 0.281 * re**0.6 * PRANDTL**0.44
    return nu * _thermal_conductivity(t_k) / WICK_DIAMETER


def _atm_emissivity(ea_hpa: float) -> float:
    return 0.575 * ea_hpa ** (1 / 7)


# --- Instrument energy balances ---------------------------------------------
def _globe_temp(ta: float, ea: float, p: float, wind: float, solar: float, cza: float, fdir: float) -> float:
    eps_a = _atm_emissivity(ea)
    tsfc = ta
    tg = ta
    for _ in range(200):
        tref = 0.5 * (tg + ta)
        h = _h_sphere(tref, p, wind)
        radiative = 0.5 * (eps_a * ta**4 + SURFACE_EMISSIVITY * tsfc**4)
        solar_term = (
            solar
            / (2 * STEFAN_BOLTZMANN * GLOBE_EMISSIVITY)
            * (1 - GLOBE_ALBEDO)
            * (fdir * (1 / (2 * cza) - 1) + 1 + SURFACE_ALBEDO)
            if solar > 0
            else 0.0
        )
        tg_new = (radiative - h / (STEFAN_BOLTZMANN * GLOBE_EMISSIVITY) * (tg - ta) + solar_term) ** 0.25
        if abs(tg_new - tg) < 0.02:
            return tg_new
        tg = 0.9 * tg + 0.1 * tg_new
    return tg


def _natural_wet_bulb(
    ta: float, ea: float, p: float, wind: float, solar: float, cza: float, fdir: float
) -> float:
    eps_a = _atm_emissivity(ea)
    tsfc = ta
    # Start from the dew point.
    ln_ratio = math.log(max(ea, 1e-6) / 6.1121)
    tw = 240.97 * ln_ratio / (17.502 - ln_ratio) + 273.15
    zenith = math.acos(max(min(cza, 1.0), -1.0))
    for _ in range(500):
        tref = 0.5 * (tw + ta)
        h = _h_cylinder(tref, p, wind)
        f_atm = STEFAN_BOLTZMANN * WICK_EMISSIVITY * (
            0.5 * (eps_a * ta**4 + SURFACE_EMISSIVITY * tsfc**4) - tw**4
        )
        if solar > 0:
            f_atm += (1 - WICK_ALBEDO) * solar * (
                (1 - fdir) * (1 + 0.25 * WICK_DIAMETER / WICK_LENGTH)
                + fdir * (math.tan(zenith) / math.pi + 0.25 * WICK_DIAMETER / WICK_LENGTH)
                + SURFACE_ALBEDO
            )
        ewick = _esat_hpa(tw)
        schmidt = _viscosity(tref) / (_density(tref, p) * _diffusivity(tref, p))
        tw_new = (
            ta
            - _heat_of_evaporation(tref) / RATIO * (ewick - ea) / (p - ewick) * (PRANDTL / schmidt) ** 0.56
            + f_atm / h
        )
        if abs(tw_new - tw) < 0.02:
            return tw_new
        tw = 0.9 * tw + 0.1 * tw_new
    return tw


def outdoor_wbgt(
    air_c: float,
    rh_pct: float,
    wind_ms: float,
    solar_wm2: float = 0.0,
    cos_zenith: float = 0.0,
    direct_fraction: float = 0.0,
    pressure_hpa: float = 1013.25,
) -> WBGTResult:
    """Compute outdoor WBGT.

    Args:
        air_c: air temperature at ~2 m, deg C.
        rh_pct: relative humidity, 0-100 %.
        wind_ms: wind speed at ~2 m, m/s (convert 10 m winds before calling).
        solar_wm2: global horizontal irradiance, W/m2.
        cos_zenith: cosine of the solar zenith angle.
        direct_fraction: fraction of solar_wm2 that is direct beam (0-1).
        pressure_hpa: station (surface) pressure, hPa.
    """
    if not 0 <= rh_pct <= 100:
        raise ValueError(f"rh_pct out of range: {rh_pct}")
    if solar_wm2 < 0:
        raise ValueError(f"solar_wm2 must be >= 0: {solar_wm2}")

    ta = air_c + 273.15
    ea = max(rh_pct, 0.1) / 100.0 * _esat_hpa(ta)
    wind = max(wind_ms, MIN_WIND)

    # No sun -> no solar load. Very low sun -> treat all as diffuse (avoids 1/cos blowup).
    if cos_zenith <= 0:
        solar_wm2 = 0.0
    # Clamp to 0.9 as KNMI's operational implementation does: forecast models
    # occasionally report near-100 % direct beam, which overstates globe heating.
    fdir = min(max(direct_fraction, 0.0), 0.9)
    if cos_zenith < MIN_COS_ZENITH:
        fdir = 0.0
    cza = max(cos_zenith, MIN_COS_ZENITH)

    tg = _globe_temp(ta, ea, pressure_hpa, wind, solar_wm2, cza, fdir)
    tnwb = _natural_wet_bulb(ta, ea, pressure_hpa, wind, solar_wm2, cza, fdir)

    wbgt_k = 0.7 * tnwb + 0.2 * tg + 0.1 * ta
    return WBGTResult(
        wbgt_c=round(wbgt_k - 273.15, 2),
        globe_c=round(tg - 273.15, 2),
        natural_wet_bulb_c=round(tnwb - 273.15, 2),
        air_c=air_c,
    )


def wind_10m_to_2m(wind_10m: float, exponent: float = 0.25) -> float:
    """Reduce a 10 m wind to 2 m with a power law (urban-ish roughness)."""
    return wind_10m * (2.0 / 10.0) ** exponent
