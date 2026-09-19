"""
charging_network_specs.py

Reference data on real EV charging networks operating in India, sourced from
network self-reported scale figures and public charging-cost aggregators
(evfy.in, spinny.com city guides, statiq.in) as of Sep 2026.

network_type distinguishes networks built primarily for public/highway
charging (most DC-fast-charger-heavy networks) vs. those with a stronger
residential/workplace (semi-public) footprint like Kazam.

pricing_model and base_price_per_kwh_inr are approximations from observed
city-level pricing ranges (typically ₹8-15/kWh on AC, ₹18-27/kWh on DC fast
charging across networks) - real networks vary tariffs by state electricity
board pricing, so this is a representative single value per network to drive
the charging-cost simulation, not a claim of exact current tariff.
"""

CHARGING_NETWORKS = [
    {
        "network_name": "Tata Power EZ Charge", "network_type": "Public",
        "pricing_model": "per_kWh", "base_price_ac_inr": 11.0, "base_price_dc_inr": 21.0,
        "scale_note": "India's largest network: 5,500+ public stations across 620+ cities (2025)",
    },
    {
        "network_name": "Statiq", "network_type": "Public",
        "pricing_model": "per_kWh", "base_price_ac_inr": 10.0, "base_price_dc_inr": 20.0,
        "scale_note": "India's largest by station count: 7,000+ stations across 63+ cities",
    },
    {
        "network_name": "ChargeZone", "network_type": "Public",
        "pricing_model": "per_kWh", "base_price_ac_inr": 12.0, "base_price_dc_inr": 22.0,
        "scale_note": "End-to-end highway and fleet charging infrastructure operator",
    },
    {
        "network_name": "Jio-bp Pulse", "network_type": "Public",
        "pricing_model": "per_kWh", "base_price_ac_inr": 12.5, "base_price_dc_inr": 23.0,
        "scale_note": "Fuel-retail-integrated network, co-located with bp/Jio outlets",
    },
    {
        "network_name": "Bolt.Earth", "network_type": "Public",
        "pricing_model": "per_kWh", "base_price_ac_inr": 10.5, "base_price_dc_inr": 19.5,
        "scale_note": "App-first aggregator network across residential and commercial sites",
    },
    {
        "network_name": "Zeon Charging", "network_type": "Public",
        "pricing_model": "per_kWh", "base_price_ac_inr": 11.5, "base_price_dc_inr": 21.5,
        "scale_note": "Fleet and public charging infrastructure operator",
    },
    {
        "network_name": "Kazam", "network_type": "Semi-Public",
        "pricing_model": "per_kWh", "base_price_ac_inr": 9.0, "base_price_dc_inr": 17.0,
        "scale_note": "Residential and workplace-charging-focused network",
    },
    {
        "network_name": "Shell Recharge", "network_type": "Public",
        "pricing_model": "per_kWh", "base_price_ac_inr": 13.0, "base_price_dc_inr": 24.0,
        "scale_note": "Fuel-retail-integrated highway charging network",
    },
    {
        "network_name": "Glida", "network_type": "Public",
        "pricing_model": "per_kWh", "base_price_ac_inr": 10.0, "base_price_dc_inr": 19.0,
        "scale_note": "Mall, hospitality and commercial-site charging network",
    },
    {
        "network_name": "ElectriVa", "network_type": "Public",
        "pricing_model": "per_kWh", "base_price_ac_inr": 10.5, "base_price_dc_inr": 20.0,
        "scale_note": "Regional public charging network",
    },
]

CONNECTOR_TYPES_BY_CHARGER_CLASS = {
    "AC": ["Type 2"],
    "DC": ["CCS2"],
    "DC_MULTI": ["CCS2", "CHAdeMO"],
}

# City coordinates (approx city-centre) used to scatter stations realistically
CITY_COORDS = {
    "Bengaluru": (12.9716, 77.5946),
    "Delhi NCR": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
    "Pune": (18.5204, 73.8567),
    "Chennai": (13.0827, 80.2707),
    "Hyderabad": (17.3850, 78.4867),
    "Ahmedabad": (23.0225, 72.5714),
    "Kolkata": (22.5726, 88.3639),
    "Jaipur": (26.9124, 75.7873),
    "Surat": (21.1702, 72.8311),
}
