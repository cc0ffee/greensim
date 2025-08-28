import pandas as pd
import numpy as np

def simulate_greenhouse(weather_df: pd.DataFrame, params: dict, dt=3600):
    # Extract parameters
    A_glass = params.get("A_glass", 50.0)         # m² glazing area
    tau_glass = params.get("tau_glass", 0.85)     # transmissivity
    U_day = params.get("U_day", 3.0)              # W/m²K
    U_night = params.get("U_night", 0.6)          # W/m²K (mat engaged)
    ACH = params.get("ACH", 0.5)                  # air changes/hour
    V = params.get("V", 100.0)                    # greenhouse volume m³
    C = params.get("C", 2e7)                      # thermal mass J/K
    T_init = params.get("T_init", 15.0)           # °C
    setpoint = params.get("setpoint", 12.0)       # °C

    rho_air, c_air = 1.2, 1005
    m_air = rho_air * V
    C_tot = C + m_air * c_air

    T_in = T_init
    T_series = []

    for _, row in weather_df.iterrows():
        Tout, G, hour = row["Tout"], row["G"], row["datetime"].hour

        # Loss coeff (day vs night mat)
        U = U_day if 6 <= hour <= 18 else U_night

        # Solar gain
        Q_solar = tau_glass * A_glass * G

        # Transmission loss
        Q_loss = U * A_glass * (T_in - Tout)

        # Ventilation loss
        ACH_s = ACH / 3600.0
        Q_vent = ACH_s * V * rho_air * c_air * (T_in - Tout)

        # Energy balance
        dQ = (Q_solar - Q_loss - Q_vent) * dt
        T_in += np.clip(dQ / C_tot, -5, 5)

        # Heater (if below setpoint)
        heater = 0.0
        if T_in < setpoint:
            heater_needed = (setpoint - T_in) * C_tot
            heater = heater_needed / dt
            T_in = setpoint

        T_series.append([row["datetime"], T_in, heater])

    return pd.DataFrame(T_series, columns=["datetime", "Tin", "Q_heater"])