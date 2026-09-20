"""
simulation_helpers.py

Shared modeling logic for the trip/charging telemetry simulator. Each
function encodes one real-world relationship the brief calls for. None of
these are "the" correct EV physics model - they're deliberately simple,
directionally-correct approximations, documented so the reasoning is
auditable (a reviewer should be able to read a function and understand WHY
a number moves the way it does, not just that it does).
"""
import math
import random

import numpy as np

# ---------------------------------------------------------------------
# Battery chemistry degradation rates (%/year), directionally consistent
# with published LFP-vs-NMC cycle life research: LFP tolerates more cycles
# and calendar aging better than NMC.
# ---------------------------------------------------------------------
CHEMISTRY_DEGRADATION_PCT_PER_YEAR = {"LFP": 1.6, "NMC": 2.6}
MILEAGE_DEGRADATION_PCT_PER_100K_KM = 3.0
MIN_BATTERY_HEALTH_PCT = 78.0


def compute_battery_health(purchase_date, current_date, odometer_km, chemistry) -> float:
    age_years = max((current_date - purchase_date).days, 0) / 365.0
    calendar_loss = age_years * CHEMISTRY_DEGRADATION_PCT_PER_YEAR[chemistry]
    mileage_loss = (odometer_km / 100_000.0) * MILEAGE_DEGRADATION_PCT_PER_100K_KM
    health = 100.0 - calendar_loss - mileage_loss
    return round(max(health, MIN_BATTERY_HEALTH_PCT), 2)


# ---------------------------------------------------------------------
# City climate model: mean annual temp + seasonal swing, peaking in May
# (Indian pre-monsoon summer peak for most regions), with a sinusoidal
# approximation rather than month-by-month lookup tables.
# ---------------------------------------------------------------------
CITY_CLIMATE = {  # (annual_mean_c, seasonal_amplitude_c)
    "Delhi NCR": (25, 13), "Jaipur": (26, 13), "Mumbai": (27, 5),
    "Ahmedabad": (28, 11), "Surat": (28, 8), "Pune": (24, 8),
    "Bengaluru": (23, 5), "Chennai": (29, 5), "Hyderabad": (26, 8),
    "Kolkata": (27, 9),
}
CITY_TIER1_TRAFFIC = {"Mumbai", "Delhi NCR", "Bengaluru"}  # heavier baseline traffic


def get_temperature_c(city: str, month: int, rng: random.Random) -> float:
    mean_c, amp_c = CITY_CLIMATE[city]
    # peak in May (month=5); cosine wave over 12 months
    seasonal = amp_c * math.cos(2 * math.pi * (month - 5) / 12)
    noise = rng.uniform(-2.5, 2.5)
    return round(mean_c + seasonal + noise, 1)


def sample_traffic(city: str, rng: random.Random) -> str:
    if city in CITY_TIER1_TRAFFIC:
        weights = {"Heavy": 0.40, "Moderate": 0.35, "Light": 0.25}
    else:
        weights = {"Heavy": 0.20, "Moderate": 0.40, "Light": 0.40}
    return rng.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]


# ---------------------------------------------------------------------
# Driver-profile behavioural parameters
# ---------------------------------------------------------------------
TRIP_LAMBDA_PER_DAY = {  # Poisson mean trips/day
    "City Driver": 1.1, "Conservative Driver": 0.6, "Highway Driver": 0.5,
    "Aggressive Driver": 0.9, "Long Distance Traveller": 0.35,
}

DRIVING_MODE_WEIGHTS = {
    "City Driver": {"City": 0.70, "Eco": 0.20, "Sport": 0.10},
    "Conservative Driver": {"Eco": 0.70, "City": 0.25, "Sport": 0.05},
    "Highway Driver": {"City": 0.30, "Sport": 0.40, "Eco": 0.30},
    "Aggressive Driver": {"Sport": 0.70, "City": 0.25, "Eco": 0.05},
    "Long Distance Traveller": {"Eco": 0.50, "City": 0.30, "Sport": 0.20},
}

TERRAIN_WEIGHTS = {
    "default": {"Flat": 0.60, "Mixed": 0.30, "Hilly": 0.10},
    "Long Distance Traveller": {"Flat": 0.40, "Mixed": 0.35, "Hilly": 0.25},
}

# Network (public station) charging reliance - City/Conservative charge mostly
# at home (invisible to this dataset); Highway/Aggressive/LongDistance lean on
# public fast charging much more.
NETWORK_CHARGE_PROB = {
    "City Driver": 0.20, "Conservative Driver": 0.15, "Highway Driver": 0.55,
    "Aggressive Driver": 0.45, "Long Distance Traveller": 0.80,
}
# Battery % at/below which the driver would consider charging at all
CHARGE_TRIGGER_PCT = {
    "City Driver": 35, "Conservative Driver": 40, "Highway Driver": 30,
    "Aggressive Driver": 28, "Long Distance Traveller": 22,
}
# Probability of a realistic overnight home top-up (not captured as a data row)
HOME_TOPUP_PROB = {
    "City Driver": 0.88, "Conservative Driver": 0.90, "Highway Driver": 0.55,
    "Aggressive Driver": 0.55, "Long Distance Traveller": 0.35,
}

DISTANCE_RANGES_KM = {  # (min, max) for a "typical" trip
    "City Driver": (4, 35), "Conservative Driver": (4, 40),
    "Highway Driver": (30, 120), "Aggressive Driver": (8, 55),
    "Long Distance Traveller": (80, 320),
}


def sample_driving_mode(driver_profile: str, rng: random.Random) -> str:
    weights = DRIVING_MODE_WEIGHTS[driver_profile]
    return rng.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]


def sample_terrain(driver_profile: str, rng: random.Random) -> str:
    weights = TERRAIN_WEIGHTS.get(driver_profile, TERRAIN_WEIGHTS["default"])
    return rng.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]


def sample_distance_km(driver_profile: str, rng: random.Random) -> float:
    lo, hi = DISTANCE_RANGES_KM[driver_profile]
    if driver_profile == "Long Distance Traveller" and rng.random() < 0.15:
        return round(rng.uniform(5, 30), 1)  # occasional short local errand
    return round(rng.uniform(lo, hi), 1)


def sample_avg_speed_kmph(driving_mode: str, terrain: str, traffic: str, rng: random.Random) -> float:
    base = {"Eco": 34, "City": 30, "Sport": 55}[driving_mode]
    traffic_mult = {"Heavy": 0.60, "Moderate": 0.85, "Light": 1.10}[traffic]
    terrain_mult = {"Flat": 1.0, "Mixed": 0.92, "Hilly": 0.78}[terrain]
    speed = base * traffic_mult * terrain_mult * rng.uniform(0.92, 1.08)
    return round(max(8, min(speed, 140)), 1)


def sample_elevation_gain_m(distance_km: float, terrain: str, rng: random.Random) -> int:
    terrain_mult = {"Flat": 0.3, "Mixed": 1.0, "Hilly": 2.5}[terrain]
    return int(max(0, distance_km * terrain_mult * rng.uniform(0.5, 4.0)))


def sample_ac_usage(temp_c: float, rng: random.Random) -> bool:
    prob = 0.85 if (temp_c > 28 or temp_c < 16) else 0.35
    return rng.random() < prob


# ---------------------------------------------------------------------
# Energy consumption model - multiplicative stack, no single fixed formula.
# base_kwh_per_km is derived per-vehicle from its own real-world range spec,
# so every vehicle starts from ITS manufacturer-implied efficiency, not a
# fleet-wide constant.
# ---------------------------------------------------------------------
def compute_energy_consumed_kwh(
    distance_km, battery_capacity_kwh, expected_real_world_range_km,
    driving_mode, terrain, temp_c, ac_usage, traffic, battery_health_pct, rng,
) -> float:
    base_kwh_per_km = battery_capacity_kwh / expected_real_world_range_km

    mode_mult = {"Eco": 0.88, "City": 1.00, "Sport": 1.22}[driving_mode]
    terrain_mult = {"Flat": 1.00, "Mixed": 1.08, "Hilly": 1.22}[terrain]
    temp_mult = 1.15 if temp_c < 10 else (1.12 if temp_c > 35 else 1.0)
    ac_mult = 1.08 if ac_usage else 1.0
    traffic_mult = {"Heavy": 1.05, "Moderate": 1.00, "Light": 0.97}[traffic]
    health_mult = 1 + (100 - battery_health_pct) * 0.003
    noise = rng.uniform(0.95, 1.05)

    combined = mode_mult * terrain_mult * temp_mult * ac_mult * traffic_mult * health_mult * noise
    return round(distance_km * base_kwh_per_km * combined, 3)
