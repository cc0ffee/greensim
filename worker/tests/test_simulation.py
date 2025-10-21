import pytest
import pandas as pd
import numpy as np
from worker.simulation.model import simulate_greenhouse

@pytest.fixture
def dummy_weather():
    """Generate 24 hours of fake weather data for testing."""
    hours = pd.date_range("2025-10-01", periods=24, freq="H")
    data = {
        "datetime": hours,
        "Tout": np.linspace(5, 25, 24),
        "G": np.maximum(0, np.sin(np.linspace(0, np.pi, 24)) * 800),
        "RH": np.full(24, 0.5)
    }
    return pd.DataFrame(data)

def test_simulation_basic(dummy_weather):
    params = {
        "A_glass": 50.0,
        "tau_glass": 0.85,
        "U_day": 3.0,
        "U_night": 0.6,
        "ACH": 0.5,
        "V": 100.0,
        "thermal_mass_kg": 20000.0,
        "cp_mass": 4186.0,
        "T_init": 15.0,
        "T_mass_init": 15.0,
        "T_soil_init": 15.0,
        "A_mass": 20.0,
        "setpoint": 12.0
    }

    result = simulate_greenhouse(dummy_weather, params)
    assert not result.empty
    assert "Tin" in result.columns
    assert "Q_heater" in result.columns
    # Basic sanity check: temperatures within bounds
    assert result["Tin"].between(0, 50).all()
    assert result["T_mass"].between(0, 50).all()
    assert result["T_soil"].between(0, 50).all()

def test_thermal_mass_effect(dummy_weather):
    """Check that increasing thermal mass reduces temperature fluctuations."""
    params_low = {
        "thermal_mass_kg": 5000.0,
        "cp_mass": 4186.0,
        "A_glass": 50.0,
        "tau_glass": 0.85,
        "U_day": 3.0,
        "U_night": 0.6,
        "ACH": 0.5,
        "V": 100.0,
        "T_init": 15.0,
        "T_mass_init": 15.0,
        "T_soil_init": 15.0,
        "A_mass": 20.0
    }

    params_high = params_low.copy()
    params_high["thermal_mass_kg"] = 500000.0

    low = simulate_greenhouse(dummy_weather, params_low)
    high = simulate_greenhouse(dummy_weather, params_high)

    std_low = low["Tin"].std()
    std_high = high["Tin"].std()

    assert std_high < std_low, "Higher thermal mass should smooth temperature variations"
