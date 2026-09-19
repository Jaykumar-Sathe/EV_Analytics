-- =====================================================================
-- Tata Connected EV Analytics Platform
-- Star Schema DDL - PostgreSQL
-- =====================================================================
-- Grain definitions:
--   fact_trip     -> one row per completed trip (ignition-on to ignition-off)
--   fact_charging -> one row per completed charging session (plug-in to plug-out)
-- =====================================================================

-- ---------------------------------------------------------------------
-- DIMENSION: dim_date
-- Standard date dimension. Avoids doing date arithmetic inside DAX/SQL
-- repeatedly and lets us pre-compute business-relevant attributes
-- like season, which matters a lot for EV range analysis in India.
-- ---------------------------------------------------------------------
CREATE TABLE dim_date (
    date_id         INT PRIMARY KEY,           -- format YYYYMMDD
    full_date       DATE NOT NULL UNIQUE,
    day             INT NOT NULL,
    month           INT NOT NULL,
    month_name      VARCHAR(15) NOT NULL,
    quarter         INT NOT NULL,
    year            INT NOT NULL,
    day_name        VARCHAR(15) NOT NULL,
    is_weekend      BOOLEAN NOT NULL,
    season          VARCHAR(15) NOT NULL        -- Summer/Monsoon/Winter (India-specific)
);

-- ---------------------------------------------------------------------
-- DIMENSION: dim_vehicle
-- Grain: one row per physical vehicle (VIN-level), not per model.
-- Specs are static attributes pulled from real manufacturer data.
-- ---------------------------------------------------------------------
CREATE TABLE dim_vehicle (
    vehicle_id                     SERIAL PRIMARY KEY,
    vin                             VARCHAR(17) NOT NULL UNIQUE,
    model                           VARCHAR(30) NOT NULL,
    variant                         VARCHAR(50) NOT NULL,
    battery_capacity_kwh           DECIMAL(5,2) NOT NULL,
    battery_chemistry              VARCHAR(10) NOT NULL,      -- LFP / NMC
    motor_power_kw                 DECIMAL(6,2) NOT NULL,
    torque_nm                      DECIMAL(6,2) NOT NULL,
    drive_type                     VARCHAR(10) NOT NULL,      -- FWD / AWD
    body_type                      VARCHAR(20) NOT NULL,
    segment                        VARCHAR(20) NOT NULL,
    launch_year                    INT NOT NULL,
    max_ac_charging_kw             DECIMAL(4,2) NOT NULL,
    max_dc_charging_kw             DECIMAL(5,2) NOT NULL,
    claimed_range_km               INT NOT NULL,
    expected_real_world_range_km   INT NOT NULL,
    kerb_weight_kg                 INT NOT NULL,
    purchase_date                  DATE NOT NULL,
    driver_profile                 VARCHAR(30) NOT NULL,      -- City/Highway/Aggressive/Conservative/LongDistance
    city_registered                VARCHAR(30) NOT NULL
);

-- ---------------------------------------------------------------------
-- DIMENSION: dim_charging_network
-- ---------------------------------------------------------------------
CREATE TABLE dim_charging_network (
    network_id      SERIAL PRIMARY KEY,
    network_name    VARCHAR(50) NOT NULL UNIQUE,
    network_type    VARCHAR(20) NOT NULL,       -- Public / Semi-Public
    pricing_model   VARCHAR(20) NOT NULL        -- per_kWh / per_minute
);

-- ---------------------------------------------------------------------
-- DIMENSION: dim_charging_station
-- ---------------------------------------------------------------------
CREATE TABLE dim_charging_station (
    station_id             SERIAL PRIMARY KEY,
    network_id             INT NOT NULL REFERENCES dim_charging_network(network_id),
    station_name           VARCHAR(80) NOT NULL,
    city                   VARCHAR(30) NOT NULL,
    latitude               DECIMAL(9,6) NOT NULL,
    longitude              DECIMAL(9,6) NOT NULL,
    max_charger_power_kw   DECIMAL(5,2) NOT NULL,
    num_chargers           INT NOT NULL,
    connector_types        VARCHAR(50) NOT NULL,  -- CCS2 / Type2 / GB/T etc.
    operational_status     VARCHAR(15) NOT NULL   -- Active/Under Maintenance/Inactive
);

-- ---------------------------------------------------------------------
-- FACT: fact_trip
-- Grain: one row = one trip.
-- ---------------------------------------------------------------------
CREATE TABLE fact_trip (
    trip_id                     BIGSERIAL PRIMARY KEY,
    vehicle_id                  INT NOT NULL REFERENCES dim_vehicle(vehicle_id),
    date_id                     INT NOT NULL REFERENCES dim_date(date_id),
    start_time                  TIMESTAMP NOT NULL,
    end_time                    TIMESTAMP NOT NULL,
    start_battery_pct           DECIMAL(5,2) NOT NULL,
    end_battery_pct             DECIMAL(5,2) NOT NULL,
    distance_km                 DECIMAL(6,2) NOT NULL,
    avg_speed_kmph              DECIMAL(5,2) NOT NULL,
    driving_mode                VARCHAR(15) NOT NULL,   -- Eco/City/Sport
    terrain                     VARCHAR(15) NOT NULL,   -- Flat/Hilly/Mixed
    elevation_gain_m            INT NOT NULL,
    outside_temp_c              DECIMAL(4,1) NOT NULL,
    ac_usage                    BOOLEAN NOT NULL,
    traffic_condition           VARCHAR(15) NOT NULL,   -- Light/Moderate/Heavy
    energy_consumed_kwh         DECIMAL(6,3) NOT NULL,
    estimated_range_km          INT NOT NULL,
    actual_range_achieved_km    INT NOT NULL,
    battery_health_pct_at_trip  DECIMAL(5,2) NOT NULL
);

-- ---------------------------------------------------------------------
-- FACT: fact_charging
-- Grain: one row = one charging session.
-- ---------------------------------------------------------------------
CREATE TABLE fact_charging (
    charging_id         BIGSERIAL PRIMARY KEY,
    vehicle_id          INT NOT NULL REFERENCES dim_vehicle(vehicle_id),
    station_id          INT NOT NULL REFERENCES dim_charging_station(station_id),
    date_id             INT NOT NULL REFERENCES dim_date(date_id),
    start_time           TIMESTAMP NOT NULL,
    end_time             TIMESTAMP NOT NULL,
    start_battery_pct   DECIMAL(5,2) NOT NULL,
    end_battery_pct     DECIMAL(5,2) NOT NULL,
    energy_added_kwh    DECIMAL(6,3) NOT NULL,
    charging_power_kw   DECIMAL(5,2) NOT NULL,
    charging_time_min   INT NOT NULL,
    wait_time_min       INT NOT NULL,
    charging_cost_inr   DECIMAL(8,2) NOT NULL,
    charging_success    BOOLEAN NOT NULL,
    connector_used       VARCHAR(20) NOT NULL
);

-- Indexes for common analytical join/filter patterns
CREATE INDEX idx_trip_vehicle ON fact_trip(vehicle_id);
CREATE INDEX idx_trip_date ON fact_trip(date_id);
CREATE INDEX idx_charging_vehicle ON fact_charging(vehicle_id);
CREATE INDEX idx_charging_station ON fact_charging(station_id);
CREATE INDEX idx_charging_date ON fact_charging(date_id);
CREATE INDEX idx_station_network ON dim_charging_station(network_id);
