"""
inject_quality_issues.py

Takes the clean, internally-consistent simulation output (data/processed/)
and deliberately corrupts a COPY of it into data/raw/ - simulating the kind
of imperfections a real connected-vehicle telemetry pipeline actually
produces (sensor dropout, double-ingestion, firmware-version inconsistencies,
GPS glitches, clock drift).

Why do this at all: every real analytics project's first job is cleaning
messy source data. A synthetic dataset with zero imperfections wouldn't let
us demonstrate that skill. Because we control the corruption process, we can
also measure how well the Phase 4 cleaning pipeline recovers the ground
truth - which is not possible with real messy data (you never know the true
answer). This script logs exactly what it broke, row by row, into
injection_log.json so that claim is auditable rather than asserted.

Run: python src/etl/inject_quality_issues.py --seed 7
"""
import argparse
import json
import random

import numpy as np
import pandas as pd

CITY_VARIANTS = {
    "Bengaluru": ["Bengaluru", "Bangalore", "BLR", "bengaluru "],
    "Delhi NCR": ["Delhi NCR", "New Delhi", "Delhi", "DELHI NCR"],
    "Mumbai": ["Mumbai", "Bombay", "mumbai", "MUMBAI"],
}

CATEGORICAL_CASE_TARGETS = {
    "driving_mode": ["Eco", "City", "Sport"],
    "terrain": ["Flat", "Mixed", "Hilly"],
    "traffic_condition": ["Light", "Moderate", "Heavy"],
}


def messify_text_case(value, rng):
    """Randomly re-case / pad a categorical value to simulate inconsistent
    logging across firmware or app versions."""
    choice = rng.random()
    if choice < 0.33:
        return value.upper()
    elif choice < 0.66:
        return value.lower()
    else:
        return f" {value} "  # stray whitespace, a classic ingestion artifact


def inject_dim_vehicle_issues(df: pd.DataFrame, rng: random.Random, log: dict) -> pd.DataFrame:
    df = df.copy()
    n = len(df)

    # City name inconsistencies (~8% of rows touching Bengaluru/Delhi/Mumbai)
    idx = df[df["city_registered"].isin(CITY_VARIANTS.keys())].sample(
        frac=0.35, random_state=rng.randint(0, 10**6)
    ).index
    for i in idx:
        canon = df.loc[i, "city_registered"]
        df.loc[i, "city_registered"] = rng.choice(CITY_VARIANTS[canon])
    log["dim_vehicle_city_text_inconsistencies"] = len(idx)

    # A handful of missing city_registered values (dropout)
    idx = df.sample(frac=0.02, random_state=rng.randint(0, 10**6)).index
    df.loc[idx, "city_registered"] = np.nan
    log["dim_vehicle_missing_city"] = len(idx)

    # One duplicated vehicle row (simulates a re-registration data-entry error)
    dup_row = df.sample(1, random_state=rng.randint(0, 10**6))
    df = pd.concat([df, dup_row], ignore_index=True)
    log["dim_vehicle_duplicate_rows"] = 1

    return df


def inject_trip_issues(df: pd.DataFrame, rng: random.Random, log: dict) -> pd.DataFrame:
    df = df.copy()
    n = len(df)
    log_counts = {}

    # --- Missing values (sensor dropout) ---
    df["ac_usage"] = df["ac_usage"].astype(object)  # allow NaN in a bool column
    for col, frac in [("outside_temp_c", 0.02), ("avg_speed_kmph", 0.01),
                       ("ac_usage", 0.01), ("driving_mode", 0.008)]:
        idx = df.sample(frac=frac, random_state=rng.randint(0, 10**6)).index
        df.loc[idx, col] = np.nan
        log_counts[f"missing_{col}"] = len(idx)

    # --- Text case inconsistencies (categorical fields) ---
    for col in CATEGORICAL_CASE_TARGETS:
        idx = df.sample(frac=0.06, random_state=rng.randint(0, 10**6)).index
        df.loc[idx, col] = df.loc[idx, col].apply(lambda v: messify_text_case(v, rng) if pd.notna(v) else v)
        log_counts[f"text_inconsistency_{col}"] = len(idx)

    # --- Duplicate records (double-ingestion) ---
    dup_idx = df.sample(frac=0.012, random_state=rng.randint(0, 10**6)).index
    dup_rows = df.loc[dup_idx]
    df = pd.concat([df, dup_rows], ignore_index=True)
    log_counts["duplicate_rows"] = len(dup_idx)

    # --- Outliers (GPS/sensor glitches) ---
    idx = df.sample(frac=0.004, random_state=rng.randint(0, 10**6)).index
    df.loc[idx, "distance_km"] = df.loc[idx, "distance_km"] * rng.uniform(15, 40)
    log_counts["outlier_distance"] = len(idx)

    idx = df.sample(frac=0.003, random_state=rng.randint(0, 10**6)).index
    df.loc[idx, "energy_consumed_kwh"] = -abs(df.loc[idx, "energy_consumed_kwh"])
    log_counts["negative_energy_consumed"] = len(idx)

    # --- Invalid values (BMS/clock faults) ---
    idx = df.sample(frac=0.003, random_state=rng.randint(0, 10**6)).index
    df.loc[idx, "start_battery_pct"] = df.loc[idx, "start_battery_pct"] + rng.uniform(20, 60)
    log_counts["battery_pct_over_100"] = len(idx)

    idx = df.sample(frac=0.002, random_state=rng.randint(0, 10**6)).index
    # swap start/end time to simulate clock drift producing end < start
    tmp = df.loc[idx, "start_time"].copy()
    df.loc[idx, "start_time"] = df.loc[idx, "end_time"]
    df.loc[idx, "end_time"] = tmp
    log_counts["end_before_start_time"] = len(idx)

    log["fact_trip"] = log_counts
    return df


def inject_charging_issues(df: pd.DataFrame, rng: random.Random, log: dict) -> pd.DataFrame:
    df = df.copy()
    log_counts = {}

    for col, frac in [("wait_time_min", 0.02), ("charging_cost_inr", 0.015)]:
        idx = df.sample(frac=frac, random_state=rng.randint(0, 10**6)).index
        df.loc[idx, col] = np.nan
        log_counts[f"missing_{col}"] = len(idx)

    # connector_used text inconsistencies
    idx = df.sample(frac=0.05, random_state=rng.randint(0, 10**6)).index
    df.loc[idx, "connector_used"] = df.loc[idx, "connector_used"].apply(lambda v: messify_text_case(v, rng))
    log_counts["text_inconsistency_connector"] = len(idx)

    # charging_success stored inconsistently as string/int instead of bool
    df["charging_success"] = df["charging_success"].astype(object)
    idx = df.sample(frac=0.04, random_state=rng.randint(0, 10**6)).index
    replacement_map = {True: rng.choice(["Yes", "TRUE", "1", "true"]),
                        False: rng.choice(["No", "FALSE", "0", "false"])}
    df.loc[idx, "charging_success"] = df.loc[idx, "charging_success"].map(
        lambda v: rng.choice(["Yes", "TRUE", "1"]) if v else rng.choice(["No", "FALSE", "0"])
    )
    log_counts["inconsistent_boolean_encoding"] = len(idx)

    # duplicates
    dup_idx = df.sample(frac=0.015, random_state=rng.randint(0, 10**6)).index
    df = pd.concat([df, df.loc[dup_idx]], ignore_index=True)
    log_counts["duplicate_rows"] = len(dup_idx)

    # outlier: absurd energy_added
    idx = df.sample(frac=0.004, random_state=rng.randint(0, 10**6)).index
    df.loc[idx, "energy_added_kwh"] = df.loc[idx, "energy_added_kwh"] * rng.uniform(10, 25)
    log_counts["outlier_energy_added"] = len(idx)

    # invalid: negative cost
    idx = df.sample(frac=0.003, random_state=rng.randint(0, 10**6)).index
    df.loc[idx, "charging_cost_inr"] = -abs(df.loc[idx, "charging_cost_inr"].fillna(50))
    log_counts["negative_cost"] = len(idx)

    log["fact_charging"] = log_counts
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--in_dir", type=str, default="../../data/processed")
    parser.add_argument("--out_dir", type=str, default="../../data/raw")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    np.random.seed(args.seed)
    log = {}

    dim_vehicle = pd.read_csv(f"{args.in_dir}/dim_vehicle.csv")
    fact_trip = pd.read_csv(f"{args.in_dir}/fact_trip.csv")
    fact_charging = pd.read_csv(f"{args.in_dir}/fact_charging.csv")

    raw_vehicle = inject_dim_vehicle_issues(dim_vehicle, rng, log)
    raw_trip = inject_trip_issues(fact_trip, rng, log)
    raw_charging = inject_charging_issues(fact_charging, rng, log)

    raw_vehicle.to_csv(f"{args.out_dir}/dim_vehicle_raw.csv", index=False)
    raw_trip.to_csv(f"{args.out_dir}/fact_trip_raw.csv", index=False)
    raw_charging.to_csv(f"{args.out_dir}/fact_charging_raw.csv", index=False)

    with open(f"{args.out_dir}/injection_log.json", "w") as f:
        json.dump(log, f, indent=2)

    print(f"dim_vehicle: {len(dim_vehicle)} -> {len(raw_vehicle)} rows")
    print(f"fact_trip: {len(fact_trip)} -> {len(raw_trip)} rows")
    print(f"fact_charging: {len(fact_charging)} -> {len(raw_charging)} rows")
    print("\nInjection log:")
    print(json.dumps(log, indent=2))
