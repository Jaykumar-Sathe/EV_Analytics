# Data Quality Report — Tata Connected EV Analytics Platform

## Methodology

This project's telemetry (Phase 3) was generated as an internally-consistent
simulation — a luxury real ingestion pipelines never have. To demonstrate a
realistic data cleaning workflow, `src/etl/inject_quality_issues.py`
deliberately corrupts a copy of that clean data into `data/raw/`, modeling
the kinds of defects a real connected-vehicle telemetry pipeline actually
produces: sensor dropout, double-ingestion on API retry, inconsistent
categorical encoding across firmware/app versions, GPS/BMS sensor glitches,
and clock drift.

`src/etl/clean_pipeline.py` then reconstructs `data/clean/` from `data/raw/`
using explicit, stated business rules — no silent transformations. Because
the ground truth (`data/processed/`) is still available, the pipeline's
output is additionally scored against it. **This self-scoring step is only
possible because the data is synthetic** — it is presented here as a
methodology validation, not a claim that any real-world pipeline can
guarantee this accuracy against data whose true values are unknown.

## Issues Injected (data/raw/)

| Table | Issue | Rows Affected |
|---|---|---|
| dim_vehicle | City name inconsistencies (Bangalore/BLR/Bengaluru variants) | 36 |
| dim_vehicle | Missing city_registered | 5 |
| dim_vehicle | Duplicate vehicle row | 1 |
| fact_trip | Missing outside_temp_c | 534 |
| fact_trip | Missing avg_speed_kmph | 267 |
| fact_trip | Missing ac_usage | 267 |
| fact_trip | Missing driving_mode | 214 |
| fact_trip | Text case/whitespace inconsistency — driving_mode | 1,602 |
| fact_trip | Text case/whitespace inconsistency — terrain | 1,602 |
| fact_trip | Text case/whitespace inconsistency — traffic_condition | 1,602 |
| fact_trip | Duplicate rows (double-ingestion) | 320 |
| fact_trip | Outlier distance_km (GPS glitch, 15–40x inflation) | 108 |
| fact_trip | Negative energy_consumed_kwh (sign-flip) | 81 |
| fact_trip | Battery % pushed over 100 (BMS fault) | 81 |
| fact_trip | end_time before start_time (clock drift) | 54 |
| fact_charging | Missing wait_time_min | 29 |
| fact_charging | Missing charging_cost_inr | 22 |
| fact_charging | connector_used text inconsistency | 73 |
| fact_charging | charging_success inconsistent boolean encoding (Yes/TRUE/1/etc.) | 59 |
| fact_charging | Duplicate rows | 22 |
| fact_charging | Outlier energy_added_kwh (10–25x inflation) | 6 |
| fact_charging | Negative charging_cost_inr | 4 |

Full machine-readable log: `data/raw/injection_log.json`

## Cleaning Rules Applied (data/clean/)

1. **Deduplication** — exact duplicates removed on each table's business key
   (`vehicle_id`, `trip_id`, `charging_id`), keeping the first occurrence.
2. **Text standardization** — categorical fields (`driving_mode`, `terrain`,
   `traffic_condition`, city names) are case/whitespace-normalized against a
   canonical value list. A value that still doesn't match anything
   recognizable is treated as missing, not guessed.
3. **Invalid value correction** —
   - Battery percentages clipped to the physically valid [0, 100] range.
   - Negative energy/cost values corrected via absolute value (sign-flip
     assumption, a common sensor/billing fault mode).
   - `end_time < start_time` rows have start/end swapped (clock-drift
     assumption).
4. **Outlier handling** — distance and energy-added outliers are **capped at
   a physically plausible ceiling and flagged** (`distance_km_was_outlier`,
   `energy_added_was_outlier`), not silently dropped — the underlying event
   is still real, only its magnitude was corrupted.
5. **Missing value imputation** — numeric gaps filled with the per-vehicle
   median (falling back to the column-wide median); categorical gaps filled
   with the per-vehicle mode. **Every imputed field has a companion
   `_was_imputed` boolean column** so downstream analysis can exclude or
   weight imputed values differently — imputation is never silent.

## Results

| Table | Raw rows | Clean rows | Rows removed (duplicates) |
|---|---|---|---|
| dim_vehicle | 251 | 250 | 1 |
| fact_trip | 27,025 | 26,705 | 320 |
| fact_charging | 1,489 | 1,467 | 22 |

**Row counts after cleaning exactly match the original ground-truth counts**
from Phase 3 (250 / 26,705 / 1,467) — every duplicate injected was correctly
identified and removed, with no genuine rows lost.

### Accuracy against ground truth (methodology validation)

| Metric | Result |
|---|---|
| Row count matches ground truth | ✅ Yes |
| Mean absolute distance_km error (post-cleaning vs. true) | 1.62 km |
| % of trip rows within 1 km of true distance_km | 99.6% |

The residual ~1.6 km average error comes almost entirely from the 71 outlier
rows (out of 108 injected) whose inflated distance fell *below* our chosen
600 km detection ceiling and therefore weren't flagged — a genuine, honestly
reported limitation of simple threshold-based outlier detection, not a
cleaning pipeline bug. A production system would likely supplement this with
a statistical (e.g. z-score or IQR-based, per driver-profile) outlier
detector rather than one fixed ceiling — noted here as a real improvement
opportunity rather than silently patched over.

## Full report

Machine-readable version: `data/clean/data_quality_report.json`
