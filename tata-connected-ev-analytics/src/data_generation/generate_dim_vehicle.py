"""
generate_dim_vehicle.py

Builds dim_vehicle: one row per physical vehicle (VIN-level).

Design reasoning:
- We do NOT generate random specs per vehicle. Every vehicle is assigned one
  of the real (model, variant) configurations from vehicle_specs.py, and
  inherits that configuration's specs exactly. This mirrors reality: a
  physical Nexon.ev Long Range either has a 45 kWh pack and 106 kW motor, or
  it doesn't - there is no in-between.
- purchase_date is constrained to fall on/after that configuration's
  launch_year, and is skewed toward more recent dates, reflecting a growing
  EV fleet (more vehicles were sold in the last 12 months than 3 years ago).
- driver_profile and city_registered are assigned independently of the
  vehicle's spec, because in reality a driver's behaviour and location don't
  depend on which trim they bought.

Run: python src/data_generation/generate_dim_vehicle.py --n 250 --seed 42
"""
import argparse
import random
from datetime import date, timedelta

import numpy as np
import pandas as pd

from vehicle_specs import (
    VEHICLE_SPECS, MODEL_POPULARITY_WEIGHTS, VARIANT_WEIGHTS,
    DRIVER_PROFILE_WEIGHTS, CITY_WEIGHTS,
)

TODAY = date(2026, 9, 19)  # analysis "as-of" date for this project


def _weighted_choice(rng: random.Random, weight_dict: dict):
    keys = list(weight_dict.keys())
    weights = list(weight_dict.values())
    return rng.choices(keys, weights=weights, k=1)[0]


def _skewed_purchase_date(rng: random.Random, launch_year: int) -> date:
    """
    Sample a purchase date between the configuration's launch date and today,
    skewed toward recent dates using a Beta(2, 1) shape (more weight near the
    right/recent end) - approximating a growing sales curve rather than a
    uniform distribution, which would unrealistically flatten fleet age.
    """
    launch_date = date(launch_year, 1, 1)
    span_days = (TODAY - launch_date).days
    if span_days <= 0:
        return TODAY
    frac = np.random.beta(2, 1)  # skewed toward 1 (recent)
    offset_days = int(frac * span_days)
    return launch_date + timedelta(days=offset_days)


def _generate_vin(rng: random.Random, model: str, index: int) -> str:
    """Plausible 17-character VIN. Not a real decodable VIN - a synthetic
    identifier in VIN format, consistent with how a telemetry platform would
    key vehicles."""
    wmi = "MAT"  # Tata Motors India WMI prefix
    model_code = {
        "Tiago.ev": "T1", "Tigor.ev": "T2", "Punch.ev": "T3", "Nexon.ev": "T4",
        "Curvv.ev": "T5", "Harrier.ev": "T6", "Sierra.ev": "T7",
    }[model]
    serial = "".join(rng.choices("0123456789ABCDEFGHJKLMNPRSTUVWXYZ", k=9))
    return f"{wmi}{model_code}{serial}{index:03d}"[:17]


def generate_dim_vehicle(n: int, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    np.random.seed(seed)

    specs_by_key = {(s["model"], s["variant"]): s for s in VEHICLE_SPECS}
    rows = []

    for i in range(1, n + 1):
        model = _weighted_choice(rng, MODEL_POPULARITY_WEIGHTS)
        variant = _weighted_choice(rng, VARIANT_WEIGHTS[model])
        spec = specs_by_key[(model, variant)]

        purchase_dt = _skewed_purchase_date(rng, spec["launch_year"])

        rows.append({
            "vehicle_id": i,
            "vin": _generate_vin(rng, model, i),
            "model": model,
            "variant": variant,
            "battery_capacity_kwh": spec["battery_capacity_kwh"],
            "battery_chemistry": spec["battery_chemistry"],
            "motor_power_kw": spec["motor_power_kw"],
            "torque_nm": spec["torque_nm"],
            "drive_type": spec["drive_type"],
            "body_type": spec["body_type"],
            "segment": spec["segment"],
            "launch_year": spec["launch_year"],
            "max_ac_charging_kw": spec["max_ac_charging_kw"],
            "max_dc_charging_kw": spec["max_dc_charging_kw"],
            "claimed_range_km": spec["claimed_range_km"],
            "expected_real_world_range_km": spec["expected_real_world_range_km"],
            "kerb_weight_kg": spec["kerb_weight_kg"],
            "purchase_date": purchase_dt,
            "driver_profile": _weighted_choice(rng, DRIVER_PROFILE_WEIGHTS),
            "city_registered": _weighted_choice(rng, CITY_WEIGHTS),
        })

    df = pd.DataFrame(rows)
    df["purchase_date"] = pd.to_datetime(df["purchase_date"])
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate dim_vehicle master data")
    parser.add_argument("--n", type=int, default=250, help="Fleet size")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--out", type=str, default="../../data/processed/dim_vehicle.csv")
    args = parser.parse_args()

    df = generate_dim_vehicle(args.n, args.seed)
    df.to_csv(args.out, index=False)
    print(f"Generated {len(df)} vehicles -> {args.out}")
    print(df["model"].value_counts())
