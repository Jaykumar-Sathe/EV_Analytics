# Tata Connected EV Analytics Platform
### Real-World Range, Charging & Battery Intelligence Dashboard

An end-to-end data analytics project simulating the internal analytics platform
of Tata Motors' Connected Vehicle Analytics division — covering real-world EV
range analysis, charging network performance, battery health, and cost analytics
across Tata's EV lineup (Tiago.ev, Tigor.ev, Punch.ev, Nexon.ev, Curvv.ev, Harrier.ev).

> **Status:** Phase 1 of 8 complete — Architecture & Data Model Design.
> This project is being built incrementally, phase by phase, with full
> documentation of the engineering and business reasoning at each step.

## Project Phases

- [x] **Phase 1** — Architecture & Star Schema Data Model Design
- [x] **Phase 2** — Vehicle & Charging Network Master Data
- [x] **Phase 3** — Synthetic Telemetry Generation (trips + charging sessions)
- [x] **Phase 4** — Data Quality Injection & Cleaning Pipeline
- [ ] Phase 5 — PostgreSQL Loading & SQL Analytics
- [ ] Phase 6 — Exploratory Data Analysis (Python)
- [ ] Phase 7 — Power BI Dashboard
- [ ] Phase 8 — Documentation, Business Report & Portfolio Packaging

## Tech Stack

Python · Pandas · NumPy · PostgreSQL · SQL · Power BI · Excel · Git/GitHub · Jupyter

## Repository Structure

```
tata-connected-ev-analytics/
├── data/
│   ├── raw/            # Raw synthetic telemetry with realistic imperfections
│   ├── clean/          # Cleaned datasets
│   └── processed/      # Analysis-ready, modeled datasets
├── sql/
│   ├── schema/         # DDL - table creation scripts
│   ├── queries/        # Business-question SQL queries
│   └── views/          # Reusable SQL views
├── src/
│   ├── data_generation/ # Modular Python generators for master + telemetry data
│   └── etl/             # Cleaning & loading pipeline modules
├── notebooks/           # Jupyter notebooks for EDA (thin - logic lives in src/)
├── powerbi/             # .pbix file and DAX documentation
├── docs/                # Data dictionary, technical docs, architecture notes
├── reports/             # Business report, portfolio write-up
└── architecture_diagrams/
```

## Data Model

Star schema with 4 dimension tables and 2 fact tables. See
[`docs/data_model.md`](docs/data_model.md) for full column-level documentation
and [`sql/schema/01_create_tables.sql`](sql/schema/01_create_tables.sql) for DDL.

**Dimensions:** `dim_vehicle`, `dim_charging_network`, `dim_charging_station`, `dim_date`
**Facts:** `fact_trip` (grain: one row per trip), `fact_charging` (grain: one row per charging session)
