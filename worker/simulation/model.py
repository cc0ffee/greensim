import pandas as pd
import numpy as np

# --- Physical constants ---
RHO_AIR = 1.225        # kg/m3
CP_AIR = 1005.0        # J/(kg*K)
SIGMA = 5.670374419e-8 # Stefan-Boltzmann W/m2/K4
LV = 2.45e6            # latent heat J/kg (approx)

def _sky_temperature_kelvin(T_out_C, cloud_factor=0.5):
    """Approximate sky temperature in Kelvin (slightly more realistic)."""
    T_sky = T_out_C - 6.0 * (1.0 - cloud_factor)
    return T_sky + 273.15

def simulate_greenhouse(weather_df: pd.DataFrame, params: dict, dt=3600.0, substeps=60, T_bounds=(0, 50)):
    """
    Stable greenhouse lumped simulation with smoother dynamics.

    weather_df: must contain columns 'datetime', 'Tout', 'G', optional 'RH'
    params: dict of greenhouse parameters
    dt: timestep in seconds
    substeps: smaller internal steps for numerical stability
    T_bounds: min and max allowed temperatures for air/mass/soil
    """

    # --- Parameters & defaults ---
    A_glass = params.get("A_glass", 50.0)                  # glass area (m2)
    tau_glass = params.get("tau_glass", 0.85)              # transmissivity of glass
    U_day = params.get("U_day", 2.0)                       # insulation W/m2K daytime
    U_night = params.get("U_night", 0.25)                  # insulation W/m2K nighttime
    ACH = params.get("ACH", 0.5)                           # air changes per hour
    V = params.get("V", 100.0)                             # greenhouse volume (m3)
    A_floor = params.get("A_floor", 50.0)                  # floor area (m2)
    fraction_solar_to_air = params.get("fraction_solar_to_air", 0.5)  # fraction of solar gain to air
    cloud_factor = params.get("cloud_factor", 0.5)         # for sky temperature

    # --- Thermal mass ---
    mass_kg = params.get("thermal_mass_kg", 20000.0)       # mass of air + structure (kg)
    cp_mass = params.get("cp_mass", 4186.0)                # specific heat J/(kg*K)
    C_mass = mass_kg * cp_mass                             # thermal capacitance

    soil_C_per_m2 = params.get("soil_C", 4e6)              # J/m2/K
    C_soil = soil_C_per_m2 * A_floor
    soil_U = params.get("soil_U", 0.5)                     # soil heat transfer coefficient

    heater_max_w = params.get("heater_max_w", 5000.0)
    evap_coeff = params.get("evap_coeff", 1e-8)            # evaporation coefficient

    # --- Initial temperatures ---
    T_air = float(params.get("T_init", 15.0))
    T_mass = float(params.get("T_mass_init", T_air))
    T_soil = float(params.get("T_soil_init", T_air))
    setpoint = params.get("setpoint", None)

    # --- Air properties ---
    rho_air = RHO_AIR
    cp_air = CP_AIR
    m_air = rho_air * V
    C_air = m_air * cp_air

    out_rows = []

    for _, row in weather_df.iterrows():
        # --- Extract weather data ---
        Tout = float(row.get("Tout", row.get("T_out", 0.0)))
        G = float(row.get("G", row.get("I", 0.0)))
        RH = float(row.get("RH", 0.5) or 0.5)
        hour = int(row["datetime"].hour) if "datetime" in row else 12

        # --- Determine insulation ---
        U_env = U_day if 6 <= hour <= 18 else U_night
        dt_step = float(dt) / max(1, int(substeps))

        # --- Substeps for numerical stability ---
        for _s in range(max(1, int(substeps))):
            # --- Solar gains ---
            Q_total_sw = G * A_glass * tau_glass
            Q_air_sw = Q_total_sw * fraction_solar_to_air
            Q_mass_sw = Q_total_sw * (1.0 - fraction_solar_to_air) * 0.6
            Q_soil_sw = Q_total_sw * (1.0 - fraction_solar_to_air) * 0.4

            # --- Heat losses ---
            Q_loss_env = U_env * A_glass * (T_air - Tout)
            m_dot = rho_air * V * (ACH / 3600.0)
            Q_vent = m_dot * cp_air * (T_air - Tout)

            # --- Longwave radiation ---
            T_air_K = np.clip(T_air + 273.15, 0, 1000)
            T_sky_K = np.clip(_sky_temperature_kelvin(Tout, cloud_factor), 0, 1000)
            emissivity = params.get("emissivity", 0.9)
            Q_lw = emissivity * SIGMA * A_glass * (T_air_K**4 - T_sky_K**4)

            # --- Heat exchange with mass and soil ---
            h_am = params.get("h_am", 3.0)
            Q_am = h_am * params.get("A_mass", 20.0) * (T_mass - T_air)

            h_as = params.get("h_as", 1.0)
            Q_as = h_as * A_floor * (T_soil - T_air)

            # --- Latent heat (evaporation) ---
            T_air_safe = np.clip(T_air, -50, 50)
            es = 0.6108 * np.exp(17.27 * T_air_safe / (T_air_safe + 237.3))
            ea = RH * es
            VPD = max(es - ea, 0.0)
            evap_kg_m2_s = evap_coeff * VPD
            Q_lat = evap_kg_m2_s * LV * A_floor

            # --- Net heat flows ---
            Q_air_in = Q_air_sw + Q_am + Q_as - Q_loss_env - Q_vent - Q_lw - Q_lat
            Q_mass_in = Q_mass_sw - Q_am
            Q_soil_in = Q_soil_sw - Q_as - soil_U * A_floor * (T_soil - Tout)

            # --- Euler integration ---
            dT_air = (Q_air_in * dt_step) / C_air
            dT_mass = (Q_mass_in * dt_step) / C_mass
            dT_soil = (Q_soil_in * dt_step) / C_soil

            T_air += dT_air
            T_mass += dT_mass
            T_soil += dT_soil

            # --- Heater control (gradual) ---
            Q_heater = 0.0
            if setpoint is not None and T_air < setpoint:
                power_needed = (setpoint - T_air) * (C_air + C_mass) / dt_step
                Q_heater = np.clip(power_needed, 0, heater_max_w)
                T_air += (Q_heater * dt_step) / (C_air + C_mass)

            # --- Clamp temperatures ---
            T_air = np.clip(T_air, *T_bounds)
            T_mass = np.clip(T_mass, *T_bounds)
            T_soil = np.clip(T_soil, *T_bounds)

        # --- Store results for this timestep ---
        out_rows.append({
            "datetime": row["datetime"],
            "Tout": Tout,
            "Tin": T_air,
            "T_mass": T_mass,
            "T_soil": T_soil,
            "Q_heater": Q_heater,
            "Q_latent": Q_lat,
        })

    return pd.DataFrame(out_rows)
