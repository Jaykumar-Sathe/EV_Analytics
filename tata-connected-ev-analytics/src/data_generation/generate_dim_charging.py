"""
generate_dim_charging.py

Builds dim_charging_network and dim_charging_station.

Design reasoning:
- Station count per network is proportional to that network's real relative
  scale (Tata Power EZ Charge and Statiq are India's two largest -> they get
  the most simulated stations), not an equal split. An equal split across
  10 networks would misrepresent the real market structure the charging
  analytics is supposed to reflect.
- Stations are scattered around each city's centre coordinates with a small
  random jitter (~0.05-0.15 degrees, roughly 5-15km) to simulate multiple
  real station locations across a metro without needing an actual address
  database.
- max_charger_power_kw and connector_types are drawn per-station from a
  realistic distribution: most stations are DC fast chargers (since that's
  the public-charging use case), a smaller share are AC-only (workplace/mall
  slow chargers), consistent with how these networks actually deploy hardware.

Run: python src/data_generation/generate_dim_charging.py --seed 42
"""
import argparse
import random

import numpy as np
import pandas as pd

from charging_network_specs import CHARGING_NETWORKS, CITY_COORDS

# Relative real-world scale weighting for station-count allocation across
# networks (Tata Power EZ Charge and Statiq lead India's public network by
# station count; smaller/regional players get proportionally fewer).
NETWORK_SCALE_WEIGHTS = {
    "Tata Power EZ Charge": 0.22,
    "Statiq": 0.20,
    "ChargeZone": 0.12,
    "Jio-bp Pulse": 0.10,
    "Bolt.Earth": 0.09,
    "Zeon Charging": 0.07,
    "Kazam": 0.06,
    "Shell Recharge": 0.06,
    "Glida": 0.05,
    "ElectriVa": 0.03,
}

TOTAL_STATIONS = 180  # across all networks, all 10 cities - realistic scale for one analytics project


def generate_dim_charging_network() -> pd.DataFrame:
    rows = []
    for i, net in enumerate(CHARGING_NETWORKS, start=1):
        rows.append({
            "network_id": i,
            "network_name": net["network_name"],
            "network_type": net["network_type"],
            "pricing_model": net["pricing_model"],
        })
    return pd.DataFrame(rows)


def generate_dim_charging_station(dim_network: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    np.random.seed(seed)

    network_name_to_id = dict(zip(dim_network["network_name"], dim_network["network_id"]))
    cities = list(CITY_COORDS.keys())

    rows = []
    station_id = 1
    for network_name, weight in NETWORK_SCALE_WEIGHTS.items():
        n_stations = max(1, round(TOTAL_STATIONS * weight))
        network_id = network_name_to_id[network_name]

        for _ in range(n_stations):
            city = rng.choice(cities)
            base_lat, base_lon = CITY_COORDS[city]
            lat = round(base_lat + np.random.uniform(-0.15, 0.15), 6)
            lon = round(base_lon + np.random.uniform(-0.15, 0.15), 6)

            # 70% of stations are DC fast-charging hubs, 30% AC-only (mall/workplace)
            is_dc = rng.random() < 0.70
            if is_dc:
                max_power = rng.choice([30, 50, 60, 100, 120, 150])
                connectors = "CCS2" if rng.random() < 0.8 else "CCS2, CHAdeMO"
                num_chargers = rng.choice([2, 4, 6, 8])
            else:
                max_power = rng.choice([3.3, 7.2, 22])
                connectors = "Type 2"
                num_chargers = rng.choice([1, 2, 4])

            status = rng.choices(
                ["Active", "Under Maintenance", "Inactive"], weights=[0.90, 0.07, 0.03], k=1
            )[0]

            rows.append({
                "station_id": station_id,
                "network_id": network_id,
                "station_name": f"{network_name} - {city} Hub {station_id}",
                "city": city,
                "latitude": lat,
                "longitude": lon,
                "max_charger_power_kw": max_power,
                "num_chargers": num_chargers,
                "connector_types": connectors,
                "operational_status": status,
            })
            station_id += 1

    return pd.DataFrame(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate dim_charging_network and dim_charging_station")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out_dir", type=str, default="../../data/processed")
    args = parser.parse_args()

    dim_network = generate_dim_charging_network()
    dim_station = generate_dim_charging_station(dim_network, args.seed)

    dim_network.to_csv(f"{args.out_dir}/dim_charging_network.csv", index=False)
    dim_station.to_csv(f"{args.out_dir}/dim_charging_station.csv", index=False)

    print(f"Generated {len(dim_network)} networks and {len(dim_station)} stations")
    print(dim_station.groupby("network_id")["station_id"].count())
