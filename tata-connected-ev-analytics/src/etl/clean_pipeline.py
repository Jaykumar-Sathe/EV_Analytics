"""
clean_pipeline.py

Transforms data/raw/ -> data/clean/, undoing (as best a real pipeline could)
the imperfections injected in Phase 4. Every cleaning decision below is a
STATED business rule, not a silent transformation - the print/report output
is the audit trail a real data engineering team would keep.

Because this is synthetic data, we can additionally score the pipeline
against the known ground truth (data/processed/) - most real projects can't
do this, so this comparison is presented as a methodology note, not a claim
that any real pipeline can guarantee this level of accuracy.

Run: python src/etl/clean_pipeline.py
"""
import json

import numpy as np
import pandas as pd

CANONICAL_CITY = {
    "bengaluru": "Bengaluru", "bangalore": "Bengaluru", "blr": "Bengaluru",
    "delhi ncr": "Delhi NCR", "new delhi": "Delhi NCR", "delhi": "Delhi NCR",
    "mumbai": "Mumbai", "bombay": "Mumbai",
}
CANONICAL_CATEGORICAL = {
    "driving_mode": ["Eco", "City", "Sport"],
    "terrain": ["Flat", "Mixed", "Hilly"],
    "traffic_condition": ["Light", "Moderate", "Heavy"],
}
BOOL_MAP = {"yes": True, "true": True, "1": True, "1.0": True,
            "no": False, "false": False, "0": False, "0.0": False}


def standardize_text(value, canonical_list):
    """Case/whitespace-normalize a categorical value against its known
    canonical set. Returns np.nan if it doesn't match anything recognizable -
    a genuinely unrecognizable value should be flagged, not silently guessed."""
    if pd.isna(value):
        return np.nan
    cleaned = str(value).strip()
    for c in canonical_list:
        if cleaned.lower() == c.lower():
            return c
    return np.nan


def clean_dim_vehicle(df: pd.DataFrame, report: dict) -> pd.DataFrame:
    df = df.copy()
    before = len(df)

    # Deduplicate on vehicle_id (business key) - keep first occurrence
    df = df.drop_duplicates(subset=["vehicle_id"], keep="first")
    report["dim_vehicle_duplicates_removed"] = before - len(df)

    # Standardize city text
    n_before_missing = df["city_registered"].isna().sum()
    df["city_registered"] = df["city_registered"].str.strip().str.lower().map(CANONICAL_CITY).fillna(
        df["city_registered"]
    )
    # After mapping known variants, anything still not in the canonical set (or null) is flagged
    valid_cities = set(CANONICAL_CITY.values()) | {
        "Pune", "Chennai", "Hyderabad", "Ahmedabad", "Kolkata", "Jaipur", "Surat"
    }
    df["city_registered_was_missing"] = ~df["city_registered"].isin(valid_cities)
    report["dim_vehicle_city_values_standardized"] = int(
        (df["city_registered_was_missing"] == False).sum()
    ) - 0  # informational
    report["dim_vehicle_city_still_missing_after_cleaning"] = int(df["city_registered_was_missing"].sum())
    df.loc[df["city_registered_was_missing"], "city_registered"] = "Unknown"

    return df


def clean_fact_trip(df: pd.DataFrame, report: dict) -> pd.DataFrame:
    df = df.copy()
    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])
    before = len(df)

    # 1. Remove exact duplicate rows (business key: trip_id)
    df = df.drop_duplicates(subset=["trip_id"], keep="first")
    report["fact_trip_duplicates_removed"] = before - len(df)

    # 2. Standardize categorical text fields
    for col, canonical in CANONICAL_CATEGORICAL.items():
        df[col] = df[col].apply(lambda v: standardize_text(v, canonical))

    # 3. Fix invalid timestamps: end_time before start_time -> swap (clock-drift assumption)
    bad_time_mask = df["end_time"] < df["start_time"]
    df.loc[bad_time_mask, ["start_time", "end_time"]] = df.loc[bad_time_mask, ["end_time", "start_time"]].values
    report["fact_trip_swapped_start_end_time"] = int(bad_time_mask.sum())

    # 4. Fix invalid battery percentages: clip to [0, 100], flag what was fixed
    for col in ["start_battery_pct", "end_battery_pct"]:
        invalid_mask = (df[col] < 0) | (df[col] > 100)
        report[f"fact_trip_{col}_out_of_range_fixed"] = int(invalid_mask.sum())
        df[col] = df[col].clip(0, 100)

    # 5. Fix negative energy_consumed_kwh (sensor sign-flip assumption -> take abs)
    neg_mask = df["energy_consumed_kwh"] < 0
    df.loc[neg_mask, "energy_consumed_kwh"] = df.loc[neg_mask, "energy_consumed_kwh"].abs()
    report["fact_trip_negative_energy_fixed"] = int(neg_mask.sum())

    # 6. Outlier distance: flag and cap at a physically plausible single-trip
    # ceiling (600km - beyond any EV's real-world range in one trip on this
    # fleet) rather than silently dropping, since the underlying event
    # (a trip happened) is still real; only the magnitude is corrupted.
    df["distance_km_was_outlier"] = df["distance_km"] > 600
    report["fact_trip_distance_outliers_capped"] = int(df["distance_km_was_outlier"].sum())
    df.loc[df["distance_km_was_outlier"], "distance_km"] = df.loc[
        df["distance_km_was_outlier"], "distance_km"
    ].clip(upper=600)

    # 7. Missing value imputation, WITH a flag column per imputed field
    # (industry best practice: never silently fabricate - always mark it)
    for col in ["outside_temp_c", "avg_speed_kmph"]:
        flag_col = f"{col}_was_imputed"
        df[flag_col] = df[col].isna()
        report[f"fact_trip_{col}_missing_imputed"] = int(df[flag_col].sum())
        df[col] = df.groupby("vehicle_id")[col].transform(lambda s: s.fillna(s.median()))
        df[col] = df[col].fillna(df[col].median())  # fallback if a whole vehicle group was null

    df["ac_usage_was_imputed"] = df["ac_usage"].isna()
    report["fact_trip_ac_usage_missing_imputed"] = int(df["ac_usage_was_imputed"].sum())
    df["ac_usage"] = df["ac_usage"].fillna(False)  # conservative default

    df["driving_mode_was_imputed"] = df["driving_mode"].isna()
    report["fact_trip_driving_mode_missing_imputed"] = int(df["driving_mode_was_imputed"].sum())
    mode_fill = df.groupby("vehicle_id")["driving_mode"].transform(
        lambda s: s.mode().iloc[0] if not s.mode().empty else "City"
    )
    df["driving_mode"] = df["driving_mode"].fillna(mode_fill)

    return df


def clean_fact_charging(df: pd.DataFrame, report: dict) -> pd.DataFrame:
    df = df.copy()
    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])
    before = len(df)

    # 1. Remove exact duplicates
    df = df.drop_duplicates(subset=["charging_id"], keep="first")
    report["fact_charging_duplicates_removed"] = before - len(df)

    # 2. Standardize connector_used text (strip/case only - values are free-ish text)
    df["connector_used"] = df["connector_used"].str.strip().str.upper()

    # 3. Normalize inconsistent boolean encoding for charging_success
    df["charging_success"] = df["charging_success"].apply(
        lambda v: BOOL_MAP.get(str(v).strip().lower(), v) if not isinstance(v, (bool, np.bool_)) else v
    ).astype(bool)

    # 4. Fix negative cost (billing sign-flip assumption)
    neg_mask = df["charging_cost_inr"] < 0
    df.loc[neg_mask, "charging_cost_inr"] = df.loc[neg_mask, "charging_cost_inr"].abs()
    report["fact_charging_negative_cost_fixed"] = int(neg_mask.sum())

    # 5. Outlier energy_added: flag + cap at largest plausible single session
    # (largest battery in fleet is 75 kWh; allow some headroom for a near-0->100% session)
    df["energy_added_was_outlier"] = df["energy_added_kwh"] > 90
    report["fact_charging_energy_added_outliers_capped"] = int(df["energy_added_was_outlier"].sum())
    df.loc[df["energy_added_was_outlier"], "energy_added_kwh"] = 90.0

    # 6. Missing value imputation with flags
    for col in ["wait_time_min", "charging_cost_inr"]:
        flag_col = f"{col}_was_imputed"
        df[flag_col] = df[col].isna()
        report[f"fact_charging_{col}_missing_imputed"] = int(df[flag_col].sum())
        df[col] = df[col].fillna(df[col].median())

    return df


if __name__ == "__main__":
    import os
    base = os.path.dirname(__file__)
    raw_dir = os.path.join(base, "../../data/raw")
    clean_dir = os.path.join(base, "../../data/clean")
    truth_dir = os.path.join(base, "../../data/processed")

    report = {}

    raw_vehicle = pd.read_csv(f"{raw_dir}/dim_vehicle_raw.csv")
    raw_trip = pd.read_csv(f"{raw_dir}/fact_trip_raw.csv")
    raw_charging = pd.read_csv(f"{raw_dir}/fact_charging_raw.csv")

    clean_vehicle = clean_dim_vehicle(raw_vehicle, report)
    clean_trip = clean_fact_trip(raw_trip, report)
    clean_charging = clean_fact_charging(raw_charging, report)

    clean_vehicle.to_csv(f"{clean_dir}/dim_vehicle.csv", index=False)
    clean_trip.to_csv(f"{clean_dir}/fact_trip.csv", index=False)
    clean_charging.to_csv(f"{clean_dir}/fact_charging.csv", index=False)

    # --- Self-measurement against known ground truth (synthetic-data-only luxury) ---
    truth_trip = pd.read_csv(f"{truth_dir}/fact_trip.csv")
    merged = clean_trip[clean_trip["trip_id"].isin(truth_trip["trip_id"])].merge(
        truth_trip, on="trip_id", suffixes=("_clean", "_truth")
    )
    dist_recovery_error = (merged["distance_km_clean"] - merged["distance_km_truth"]).abs()
    report["ground_truth_check_row_count_match"] = len(clean_trip.drop_duplicates("trip_id")) == len(truth_trip)
    report["ground_truth_check_mean_abs_distance_error_km"] = round(float(dist_recovery_error.mean()), 4)
    report["ground_truth_check_pct_rows_within_1km_of_truth"] = round(
        float((dist_recovery_error <= 1.0).mean() * 100), 2
    )

    with open(f"{clean_dir}/data_quality_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"dim_vehicle: {len(raw_vehicle)} raw -> {len(clean_vehicle)} clean")
    print(f"fact_trip: {len(raw_trip)} raw -> {len(clean_trip)} clean")
    print(f"fact_charging: {len(raw_charging)} raw -> {len(clean_charging)} clean")
    print("\nData quality report:")
    print(json.dumps(report, indent=2))
