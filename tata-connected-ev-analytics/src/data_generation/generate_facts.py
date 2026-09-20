"""
generate_facts.py

Main stateful simulation: for each vehicle, walks forward day-by-day across
a bounded telemetry window, generating fact_trip and fact_charging rows that
are causally consistent with each other (battery state carries across events;
trips can't happen if there's no battery; charging always follows depletion).

Sequence per vehicle, per simulated day:
  1. Overnight home top-up check (invisible to the data - see Phase 3 notes
     in README/docs): with driver-profile-dependent probability, battery is
     silently refreshed before the day's driving starts.
  2. Sample number of trips today (Poisson, driver-profile-dependent rate).
  3. For each trip: sample conditions (mode, terrain, weather, traffic),
     compute energy consumption, drain battery, log the fact_trip row.
     If a trip's distance would drain the battery below empty, the trip
     distance is capped to what's physically achievable (range anxiety
     behaviour: shorter trip on a low battery, not a physically impossible one).
  4. After each trip, if battery has crossed the driver's charge-trigger
     threshold AND they resort to public charging this time (vs. waiting
     for a home top-up), generate a fact_charging row at a real station.

Run: python src/data_generation/generate_facts.py --seed 42
"""
import argparse
import random
from datetime import date, timedelta

import numpy as np
import pandas as pd

from simulation_helpers import (
    compute_battery_health, get_temperature_c, sample_traffic,
    TRIP_LAMBDA_PER_DAY, NETWORK_CHARGE_PROB, CHARGE_TRIGGER_PCT, HOME_TOPUP_PROB,
    sample_driving_mode, sample_terrain, sample_distance_km, sample_avg_speed_kmph,
    sample_elevation_gain_m, sample_ac_usage, compute_energy_consumed_kwh,
)
from charging_network_specs import CHARGING_NETWORKS

# Pricing lives in the spec file (it's a simulation input / tariff table, not
# a stored dimension attribute - real electricity tariffs are looked up from
# a pricing service, not baked into the network master record), so we build a
# lookup by network name for the simulator to use.
NETWORK_PRICING = {n["network_name"]: n for n in CHARGING_NETWORKS}

TODAY = date(2026, 9, 19)
WINDOW_DAYS = 180


def build_date_dim(start: date, end: date) -> pd.DataFrame:
    dates = pd.date_range(start, end, freq="D")
    df = pd.DataFrame({"full_date": dates})
    df["date_id"] = df["full_date"].dt.strftime("%Y%m%d").astype(int)
    df["day"] = df["full_date"].dt.day
    df["month"] = df["full_date"].dt.month
    df["month_name"] = df["full_date"].dt.strftime("%B")
    df["quarter"] = df["full_date"].dt.quarter
    df["year"] = df["full_date"].dt.year
    df["day_name"] = df["full_date"].dt.strftime("%A")
    df["is_weekend"] = df["full_date"].dt.dayofweek >= 5

    def season(m):
        if m in (12, 1, 2):
            return "Winter"
        if m in (3, 4, 5):
            return "Summer"
        if m in (6, 7, 8, 9):
            return "Monsoon"
        return "Post-Monsoon"
    df["season"] = df["month"].apply(season)
    return df[["date_id", "full_date", "day", "month", "month_name",
               "quarter", "year", "day_name", "is_weekend", "season"]]


def pick_station(stations_df: pd.DataFrame, city: str, rng: random.Random) -> pd.Series:
    city_stations = stations_df[stations_df["city"] == city]
    if city_stations.empty:
        city_stations = stations_df  # fallback: any station
    # 95% of the time pick an Active station; 5% the driver unluckily tries a
    # down one (generates a failed-session row - a real charging-reliability KPI)
    active = city_stations[city_stations["operational_status"] == "Active"]
    if rng.random() < 0.95 and not active.empty:
        return active.sample(1, random_state=rng.randint(0, 10**6)).iloc[0]
    return city_stations.sample(1, random_state=rng.randint(0, 10**6)).iloc[0]


def simulate_charging_session(vehicle, station, start_pct, current_dt, rng):
    is_dc = station["max_charger_power_kw"] > 22
    rated_power = min(
        station["max_charger_power_kw"],
        vehicle["max_dc_charging_kw"] if is_dc else vehicle["max_ac_charging_kw"],
    )
    derate = rng.uniform(0.65, 0.90) if is_dc else rng.uniform(0.90, 0.97)
    effective_power_kw = max(rated_power * derate, 1.0)

    station_up = station["operational_status"] == "Active"
    success = True
    if not station_up:
        success = rng.random() > 0.60  # 60% of attempts at a down station fail outright

    if not success:
        end_pct = start_pct + rng.uniform(0, 2)
        energy_added = round(rng.uniform(0, 1.5), 3)
        charging_time_min = int(rng.uniform(1, 8))
        wait_time_min = int(rng.uniform(5, 25))
    else:
        target_end = (rng.uniform(70, 85) if is_dc else rng.uniform(85, 100))
        end_pct = max(start_pct + 5, min(100, target_end))
        battery_gain_kwh = (end_pct - start_pct) / 100 * vehicle["battery_capacity_kwh"]
        charging_efficiency = rng.uniform(0.88, 0.95)
        energy_added = round(battery_gain_kwh / charging_efficiency, 3)
        charging_time_min = int(max(5, (battery_gain_kwh / effective_power_kw) * 60 + rng.uniform(2, 6)))
        wait_time_min = int(rng.uniform(8, 20)) if station["city"] in ("Mumbai", "Delhi NCR", "Bengaluru") else int(rng.uniform(0, 10))

    price_key = "base_price_dc_inr" if is_dc else "base_price_ac_inr"
    price_per_kwh = NETWORK_PRICING[station["network_name"]][price_key]
    peak_mult = 1.1 if rng.random() < 0.25 else 1.0
    cost = round(energy_added * price_per_kwh * peak_mult, 2)

    return {
        "end_pct": round(end_pct, 1),
        "energy_added_kwh": energy_added,
        "charging_power_kw": round(effective_power_kw, 2),
        "charging_time_min": charging_time_min,
        "wait_time_min": wait_time_min,
        "charging_cost_inr": cost,
        "charging_success": success,
        "connector_used": station["connector_types"].split(",")[0].strip(),
    }


def simulate_fleet(dim_vehicle, dim_network, dim_station, seed=42):
    rng = random.Random(seed)
    np.random.seed(seed)

    stations = dim_station.merge(dim_network, on="network_id", suffixes=("", "_net"))
    window_start_global = TODAY - timedelta(days=WINDOW_DAYS)

    trip_rows, charge_rows = [], []
    trip_id, charge_id = 1, 1

    for _, v in dim_vehicle.iterrows():
        purchase_dt = v["purchase_date"].date()
        window_start = max(purchase_dt, window_start_global)
        if window_start > TODAY:
            continue

        battery_pct = 100.0
        odometer_km = 0.0
        current_date = window_start

        while current_date <= TODAY:
            # 1. Overnight home top-up (invisible to the dataset)
            if battery_pct < 60 and rng.random() < HOME_TOPUP_PROB[v["driver_profile"]]:
                battery_pct = round(rng.uniform(75, 100), 1)

            # 2. Trips for the day - sequenced chronologically so that sorting
            # by start_time always matches the causal (battery-draining) order
            n_trips = np.random.poisson(TRIP_LAMBDA_PER_DAY[v["driver_profile"]])
            day_cursor = pd.Timestamp(current_date) + pd.Timedelta(hours=rng.uniform(6, 10))
            for _ in range(n_trips):
                if battery_pct < 8:
                    break  # too low to responsibly drive; will top up tomorrow

                driving_mode = sample_driving_mode(v["driver_profile"], rng)
                terrain = sample_terrain(v["driver_profile"], rng)
                traffic = sample_traffic(v["city_registered"], rng)
                temp_c = get_temperature_c(v["city_registered"], current_date.month, rng)
                ac_usage = sample_ac_usage(temp_c, rng)
                distance_km = sample_distance_km(v["driver_profile"], rng)

                battery_health = compute_battery_health(
                    purchase_dt, current_date, odometer_km, v["battery_chemistry"]
                )

                energy_kwh = compute_energy_consumed_kwh(
                    distance_km, v["battery_capacity_kwh"], v["expected_real_world_range_km"],
                    driving_mode, terrain, temp_c, ac_usage, traffic, battery_health, rng,
                )

                # Range-anxiety cap: don't let a trip drain below 5% remaining
                max_affordable_kwh = max(0.0, (battery_pct - 5) / 100 * v["battery_capacity_kwh"])
                if energy_kwh > max_affordable_kwh:
                    scale = max_affordable_kwh / energy_kwh if energy_kwh > 0 else 0
                    distance_km = round(distance_km * scale, 1)
                    energy_kwh = round(energy_kwh * scale, 3)
                    if distance_km < 1:
                        break

                start_pct = battery_pct
                end_pct = round(max(5, battery_pct - (energy_kwh / v["battery_capacity_kwh"]) * 100), 1)

                avg_speed = sample_avg_speed_kmph(driving_mode, terrain, traffic, rng)
                elevation_gain = sample_elevation_gain_m(distance_km, terrain, rng)
                duration_min = max(3, (distance_km / avg_speed) * 60)
                start_time = day_cursor
                end_time = start_time + pd.Timedelta(minutes=duration_min)
                # advance the cursor past this trip, plus a gap before the next one
                day_cursor = end_time + pd.Timedelta(minutes=rng.uniform(20, 180))

                estimated_range = round(
                    (start_pct / 100) * v["expected_real_world_range_km"] * (battery_health / 100)
                    * rng.uniform(0.95, 1.05)
                )
                actual_range_achieved = round(
                    distance_km * v["battery_capacity_kwh"] / energy_kwh
                ) if energy_kwh > 0 else estimated_range

                trip_rows.append({
                    "trip_id": trip_id, "vehicle_id": v["vehicle_id"],
                    "date_id": int(current_date.strftime("%Y%m%d")),
                    "start_time": start_time, "end_time": end_time,
                    "start_battery_pct": start_pct, "end_battery_pct": end_pct,
                    "distance_km": distance_km, "avg_speed_kmph": avg_speed,
                    "driving_mode": driving_mode, "terrain": terrain,
                    "elevation_gain_m": elevation_gain, "outside_temp_c": temp_c,
                    "ac_usage": ac_usage, "traffic_condition": traffic,
                    "energy_consumed_kwh": energy_kwh,
                    "estimated_range_km": estimated_range,
                    "actual_range_achieved_km": actual_range_achieved,
                    "battery_health_pct_at_trip": battery_health,
                })
                trip_id += 1
                odometer_km += distance_km
                battery_pct = end_pct

                # 3. Possible public charging session right after this trip
                if (battery_pct <= CHARGE_TRIGGER_PCT[v["driver_profile"]]
                        and rng.random() < NETWORK_CHARGE_PROB[v["driver_profile"]]):
                    station = pick_station(stations, v["city_registered"], rng)
                    result = simulate_charging_session(v, station, battery_pct, current_date, rng)
                    charge_start = end_time + pd.Timedelta(minutes=rng.uniform(2, 15))
                    charge_end = charge_start + pd.Timedelta(minutes=result["charging_time_min"])

                    charge_rows.append({
                        "charging_id": charge_id, "vehicle_id": v["vehicle_id"],
                        "station_id": int(station["station_id"]),
                        "date_id": int(current_date.strftime("%Y%m%d")),
                        "start_time": charge_start, "end_time": charge_end,
                        "start_battery_pct": battery_pct, "end_battery_pct": result["end_pct"],
                        "energy_added_kwh": result["energy_added_kwh"],
                        "charging_power_kw": result["charging_power_kw"],
                        "charging_time_min": result["charging_time_min"],
                        "wait_time_min": result["wait_time_min"],
                        "charging_cost_inr": result["charging_cost_inr"],
                        "charging_success": result["charging_success"],
                        "connector_used": result["connector_used"],
                    })
                    charge_id += 1
                    battery_pct = result["end_pct"]

            current_date += timedelta(days=1)

    return pd.DataFrame(trip_rows), pd.DataFrame(charge_rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate fact_trip and fact_charging")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--data_dir", type=str, default="../../data/processed")
    args = parser.parse_args()

    dim_vehicle = pd.read_csv(f"{args.data_dir}/dim_vehicle.csv", parse_dates=["purchase_date"])
    dim_network = pd.read_csv(f"{args.data_dir}/dim_charging_network.csv")
    dim_station = pd.read_csv(f"{args.data_dir}/dim_charging_station.csv")

    dim_date = build_date_dim(TODAY - timedelta(days=WINDOW_DAYS), TODAY)
    dim_date.to_csv(f"{args.data_dir}/dim_date.csv", index=False)

    fact_trip, fact_charging = simulate_fleet(dim_vehicle, dim_network, dim_station, args.seed)
    fact_trip.to_csv(f"{args.data_dir}/fact_trip.csv", index=False)
    fact_charging.to_csv(f"{args.data_dir}/fact_charging.csv", index=False)

    print(f"dim_date: {len(dim_date)} rows")
    print(f"fact_trip: {len(fact_trip)} rows")
    print(f"fact_charging: {len(fact_charging)} rows")
    print(f"\nTrips per vehicle - mean: {fact_trip.groupby('vehicle_id').size().mean():.1f}")
    print(f"Charging sessions per vehicle - mean: {fact_charging.groupby('vehicle_id').size().mean():.1f}")
