"""
vehicle_specs.py

Reference data: real Tata Motors EV specifications, sourced from manufacturer
data and verified automotive publications (Autocar India, Team-BHP, Electrive,
Tata Motors' own ev.tatamotors.com, Wikipedia model pages) as of Sep 2026.

This is intentionally hardcoded rather than scraped live, because a data
model's dimension reference data should be a controlled, versioned artifact -
exactly how a real analytics team would maintain a vehicle master table
(manual curation + periodic review), not a live-scraped one.

Each entry represents ONE sellable configuration (model + battery pack +
drivetrain), matching how Tata actually segments trims. Where manufacturer
kerb weight was not published for a configuration, we derive an engineering
estimate from the closest published trim of the same body class and note it
with `kerb_weight_estimated: True` - we NEVER fabricate silently.

Real-world range figures below are Tata's own disclosed C75 / real-world
expectation figures where published; where not published, we apply a
conservative 78-82% haircut on the MIDC claimed figure, consistent with the
haircut Tata itself discloses on the models where it does publish both
numbers. This ratio is documented, not arbitrary.
"""

VEHICLE_SPECS = [
    # ---------------------------------------------------------------
    # TIAGO.EV — entry-level hatchback, A-segment
    # ---------------------------------------------------------------
    {
        "model": "Tiago.ev", "variant": "Medium Range (XE)",
        "battery_capacity_kwh": 19.2, "battery_chemistry": "NMC",
        "motor_power_kw": 45.0, "torque_nm": 110, "drive_type": "FWD",
        "body_type": "Hatchback", "segment": "A-Segment",
        "launch_year": 2022, "max_ac_charging_kw": 3.3, "max_dc_charging_kw": 25.0,
        "claimed_range_km": 250, "expected_real_world_range_km": 200,
        "kerb_weight_kg": 1235, "kerb_weight_estimated": False,
    },
    {
        "model": "Tiago.ev", "variant": "Long Range (XZ+ Tech LR)",
        "battery_capacity_kwh": 24.0, "battery_chemistry": "NMC",
        "motor_power_kw": 55.0, "torque_nm": 114, "drive_type": "FWD",
        "body_type": "Hatchback", "segment": "A-Segment",
        "launch_year": 2022, "max_ac_charging_kw": 7.2, "max_dc_charging_kw": 25.0,
        "claimed_range_km": 315, "expected_real_world_range_km": 250,
        "kerb_weight_kg": 1255, "kerb_weight_estimated": False,
    },
    # ---------------------------------------------------------------
    # TIGOR.EV — compact sedan
    # ---------------------------------------------------------------
    {
        "model": "Tigor.ev", "variant": "XZ+ Lux",
        "battery_capacity_kwh": 26.0, "battery_chemistry": "NMC",
        "motor_power_kw": 55.0, "torque_nm": 170, "drive_type": "FWD",
        "body_type": "Sedan", "segment": "Compact Sedan",
        "launch_year": 2021, "max_ac_charging_kw": 7.2, "max_dc_charging_kw": 50.0,
        "claimed_range_km": 315, "expected_real_world_range_km": 250,
        "kerb_weight_kg": 1235, "kerb_weight_estimated": False,
    },
    # ---------------------------------------------------------------
    # PUNCH.EV — compact SUV (2026 facelift specs; prismatic-cell pack)
    # ---------------------------------------------------------------
    {
        "model": "Punch.ev", "variant": "Standard Range (30 kWh)",
        "battery_capacity_kwh": 30.0, "battery_chemistry": "LFP",
        "motor_power_kw": 60.0, "torque_nm": 114, "drive_type": "FWD",
        "body_type": "SUV", "segment": "Compact SUV",
        "launch_year": 2026, "max_ac_charging_kw": 3.3, "max_dc_charging_kw": 30.0,
        "claimed_range_km": 375, "expected_real_world_range_km": 280,
        "kerb_weight_kg": 1360, "kerb_weight_estimated": False,
    },
    {
        "model": "Punch.ev", "variant": "Long Range (40 kWh)",
        "battery_capacity_kwh": 40.0, "battery_chemistry": "LFP",
        "motor_power_kw": 90.0, "torque_nm": 190, "drive_type": "FWD",
        "body_type": "SUV", "segment": "Compact SUV",
        "launch_year": 2026, "max_ac_charging_kw": 7.2, "max_dc_charging_kw": 50.0,
        "claimed_range_km": 468, "expected_real_world_range_km": 345,
        "kerb_weight_kg": 1360, "kerb_weight_estimated": False,
    },
    # ---------------------------------------------------------------
    # NEXON.EV — India's best-selling EV, compact SUV, Ziptron platform
    # ---------------------------------------------------------------
    {
        "model": "Nexon.ev", "variant": "Medium Range (30 kWh)",
        "battery_capacity_kwh": 30.0, "battery_chemistry": "NMC",
        "motor_power_kw": 95.0, "torque_nm": 215, "drive_type": "FWD",
        "body_type": "SUV", "segment": "Compact SUV",
        "launch_year": 2020, "max_ac_charging_kw": 7.2, "max_dc_charging_kw": 30.0,
        "claimed_range_km": 275, "expected_real_world_range_km": 220,
        "kerb_weight_kg": 1400, "kerb_weight_estimated": True,
    },
    {
        "model": "Nexon.ev", "variant": "Long Range (45 kWh)",
        "battery_capacity_kwh": 45.0, "battery_chemistry": "NMC",
        "motor_power_kw": 106.0, "torque_nm": 215, "drive_type": "FWD",
        "body_type": "SUV", "segment": "Compact SUV",
        "launch_year": 2023, "max_ac_charging_kw": 7.2, "max_dc_charging_kw": 50.0,
        "claimed_range_km": 489, "expected_real_world_range_km": 350,
        "kerb_weight_kg": 1500, "kerb_weight_estimated": True,
    },
    # ---------------------------------------------------------------
    # CURVV.EV — SUV coupe, Tata Gen-2 EV platform
    # ---------------------------------------------------------------
    {
        "model": "Curvv.ev", "variant": "Accomplished (45 kWh)",
        "battery_capacity_kwh": 45.0, "battery_chemistry": "LFP",
        "motor_power_kw": 110.0, "torque_nm": 215, "drive_type": "FWD",
        "body_type": "SUV Coupe", "segment": "Subcompact Crossover SUV",
        "launch_year": 2024, "max_ac_charging_kw": 7.2, "max_dc_charging_kw": 60.0,
        "claimed_range_km": 502, "expected_real_world_range_km": 340,
        "kerb_weight_kg": 1480, "kerb_weight_estimated": True,
    },
    {
        "model": "Curvv.ev", "variant": "Empowered+ A (55 kWh)",
        "battery_capacity_kwh": 55.0, "battery_chemistry": "LFP",
        "motor_power_kw": 123.0, "torque_nm": 215, "drive_type": "FWD",
        "body_type": "SUV Coupe", "segment": "Subcompact Crossover SUV",
        "launch_year": 2024, "max_ac_charging_kw": 7.2, "max_dc_charging_kw": 70.0,
        "claimed_range_km": 585, "expected_real_world_range_km": 410,
        "kerb_weight_kg": 1530, "kerb_weight_estimated": True,
    },
    # ---------------------------------------------------------------
    # HARRIER.EV — flagship midsize SUV, Acti.ev+ platform, first Tata AWD EV
    # ---------------------------------------------------------------
    {
        "model": "Harrier.ev", "variant": "RWD (65 kWh)",
        "battery_capacity_kwh": 65.0, "battery_chemistry": "LFP",
        "motor_power_kw": 175.0, "torque_nm": 315, "drive_type": "RWD",
        "body_type": "SUV", "segment": "Midsize SUV",
        "launch_year": 2025, "max_ac_charging_kw": 7.2, "max_dc_charging_kw": 100.0,
        "claimed_range_km": 538, "expected_real_world_range_km": 400,
        "kerb_weight_kg": 1800, "kerb_weight_estimated": True,
    },
    {
        "model": "Harrier.ev", "variant": "RWD (75 kWh)",
        "battery_capacity_kwh": 75.0, "battery_chemistry": "LFP",
        "motor_power_kw": 175.0, "torque_nm": 315, "drive_type": "RWD",
        "body_type": "SUV", "segment": "Midsize SUV",
        "launch_year": 2025, "max_ac_charging_kw": 7.2, "max_dc_charging_kw": 120.0,
        "claimed_range_km": 627, "expected_real_world_range_km": 490,
        "kerb_weight_kg": 1850, "kerb_weight_estimated": True,
    },
    {
        "model": "Harrier.ev", "variant": "AWD (75 kWh)",
        "battery_capacity_kwh": 75.0, "battery_chemistry": "LFP",
        "motor_power_kw": 291.0, "torque_nm": 504, "drive_type": "AWD",
        "body_type": "SUV", "segment": "Midsize SUV",
        "launch_year": 2025, "max_ac_charging_kw": 7.2, "max_dc_charging_kw": 120.0,
        "claimed_range_km": 622, "expected_real_world_range_km": 460,
        "kerb_weight_kg": 1950, "kerb_weight_estimated": True,
    },
    # ---------------------------------------------------------------
    # SIERRA.EV — newest model (launched 30 Jun 2026), Acti.ev+ / TiDAL E&E
    # ---------------------------------------------------------------
    {
        "model": "Sierra.ev", "variant": "RWD (63 kWh)",
        "battery_capacity_kwh": 63.0, "battery_chemistry": "LFP",
        "motor_power_kw": 175.0, "torque_nm": 315, "drive_type": "RWD",
        "body_type": "SUV", "segment": "Midsize SUV",
        "launch_year": 2026, "max_ac_charging_kw": 7.2, "max_dc_charging_kw": 120.0,
        "claimed_range_km": 565, "expected_real_world_range_km": 450,
        "kerb_weight_kg": 1750, "kerb_weight_estimated": True,
    },
    {
        "model": "Sierra.ev", "variant": "RWD (75 kWh)",
        "battery_capacity_kwh": 75.0, "battery_chemistry": "LFP",
        "motor_power_kw": 156.0, "torque_nm": 315, "drive_type": "RWD",
        "body_type": "SUV", "segment": "Midsize SUV",
        "launch_year": 2026, "max_ac_charging_kw": 7.2, "max_dc_charging_kw": 120.0,
        "claimed_range_km": 665, "expected_real_world_range_km": 520,
        "kerb_weight_kg": 1800, "kerb_weight_estimated": True,
    },
    {
        "model": "Sierra.ev", "variant": "AWD / QWD (75 kWh)",
        "battery_capacity_kwh": 75.0, "battery_chemistry": "LFP",
        "motor_power_kw": 259.0, "torque_nm": 504, "drive_type": "AWD",
        "body_type": "SUV", "segment": "Midsize SUV",
        "launch_year": 2026, "max_ac_charging_kw": 7.2, "max_dc_charging_kw": 120.0,
        "claimed_range_km": 624, "expected_real_world_range_km": 490,
        "kerb_weight_kg": 1900, "kerb_weight_estimated": True,
    },
]

# Relative sales-volume weights across models, reflecting Nexon.ev's real
# market leadership and the newer/premium models' lower current volumes.
MODEL_POPULARITY_WEIGHTS = {
    "Nexon.ev": 0.30,
    "Tiago.ev": 0.20,
    "Punch.ev": 0.20,
    "Tigor.ev": 0.10,
    "Curvv.ev": 0.10,
    "Harrier.ev": 0.06,
    "Sierra.ev": 0.04,
}

# Within-model split across battery/drivetrain configuration, reflecting the
# real-world trend of buyers increasingly preferring the long-range pack.
VARIANT_WEIGHTS = {
    "Tiago.ev": {"Medium Range (XE)": 0.40, "Long Range (XZ+ Tech LR)": 0.60},
    "Tigor.ev": {"XZ+ Lux": 1.00},
    "Punch.ev": {"Standard Range (30 kWh)": 0.35, "Long Range (40 kWh)": 0.65},
    "Nexon.ev": {"Medium Range (30 kWh)": 0.40, "Long Range (45 kWh)": 0.60},
    "Curvv.ev": {"Accomplished (45 kWh)": 0.45, "Empowered+ A (55 kWh)": 0.55},
    "Harrier.ev": {"RWD (65 kWh)": 0.20, "RWD (75 kWh)": 0.50, "AWD (75 kWh)": 0.30},
    "Sierra.ev": {"RWD (63 kWh)": 0.35, "RWD (75 kWh)": 0.45, "AWD / QWD (75 kWh)": 0.20},
}

DRIVER_PROFILE_WEIGHTS = {
    "City Driver": 0.40,
    "Conservative Driver": 0.20,
    "Highway Driver": 0.15,
    "Aggressive Driver": 0.15,
    "Long Distance Traveller": 0.10,
}

# Cities weighted loosely by real Indian EV adoption / Tata dealership density
CITY_WEIGHTS = {
    "Bengaluru": 0.16, "Delhi NCR": 0.15, "Mumbai": 0.14, "Pune": 0.11,
    "Chennai": 0.10, "Hyderabad": 0.10, "Ahmedabad": 0.09,
    "Kolkata": 0.06, "Jaipur": 0.05, "Surat": 0.04,
}
