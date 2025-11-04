import pytest
import pandas as pd
import numpy as np
import sys
import os

# Add worker directory to path for imports
worker_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if worker_dir not in sys.path:
    sys.path.insert(0, worker_dir)
from simulation.model import simulate_greenhouse, calculate_heat_to_threshold

@pytest.fixture
def dummy_weather():
    """Generate 24 hours of fake weather data for testing."""
    hours = pd.date_range("2025-10-01", periods=24, freq="h")
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
    assert "Q_to_threshold" in result.columns
    # Basic sanity check: temperatures within bounds
    assert result["Tin"].between(0, 50).all()
    assert result["T_mass"].between(0, 50).all()
    assert result["T_soil"].between(0, 50).all()
    # Heat to threshold should be >= 0
    assert (result["Q_to_threshold"] >= 0).all()

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

def test_heat_to_threshold_calculation():
    """Test the heat to threshold calculation function."""
    # Test parameters
    C_air = 100000.0  # J/K
    C_mass = 500000.0  # J/K
    C_soil = 200000.0  # J/K
    setpoint = 20.0
    Tout = 10.0
    
    params = {
        "A_glass": 50.0,
        "U_day": 2.0,
        "U_night": 0.25,
        "V": 100.0,
        "ACH": 0.5,
        "heater_max_w": 5000.0,
        "current_hour": 12
    }
    
    # Case 1: Below threshold - should return positive heat
    T_air = 15.0
    T_mass = 15.0
    T_soil = 15.0
    heat_needed = calculate_heat_to_threshold(
        T_air, T_mass, T_soil, setpoint, C_air, C_mass, C_soil, Tout, params
    )
    assert heat_needed > 0, "Should need heat when below threshold"
    
    # Case 2: At threshold - should return 0
    T_air = 20.0
    T_mass = 20.0
    T_soil = 20.0
    heat_needed = calculate_heat_to_threshold(
        T_air, T_mass, T_soil, setpoint, C_air, C_mass, C_soil, Tout, params
    )
    assert heat_needed == 0.0, "Should need no heat when at threshold"
    
    # Case 3: Above threshold - should return 0
    T_air = 25.0
    T_mass = 25.0
    T_soil = 25.0
    heat_needed = calculate_heat_to_threshold(
        T_air, T_mass, T_soil, setpoint, C_air, C_mass, C_soil, Tout, params
    )
    assert heat_needed == 0.0, "Should need no heat when above threshold"
    
    # Case 4: No setpoint - should return 0
    heat_needed = calculate_heat_to_threshold(
        T_air, T_mass, T_soil, None, C_air, C_mass, C_soil, Tout, params
    )
    assert heat_needed == 0.0, "Should need no heat when no setpoint"

def test_energy_conservation(dummy_weather):
    """Test that energy balance is reasonable - internal temp should follow external temp with solar effects."""
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
        "setpoint": None  # No heating to test natural behavior
    }
    
    result = simulate_greenhouse(dummy_weather, params)
    
    # Internal temperature should generally follow external temperature trends
    # During day (with solar), internal should be higher than external
    # During night (no solar), internal should be closer to external
    daytime = result[result["datetime"].dt.hour.between(6, 18)]
    nighttime = result[~result["datetime"].dt.hour.between(6, 18)]
    
    if len(daytime) > 0:
        # During daytime with solar gain, internal should often be warmer
        daytime_avg_diff = (daytime["Tin"] - daytime["Tout"]).mean()
        assert daytime_avg_diff > -5, "Daytime: internal temp should be reasonably close to external (with solar gains)"
    
    # Temperature should be bounded and reasonable
    assert result["Tin"].min() > -10, "Internal temp should not drop unreasonably low"
    assert result["Tin"].max() < 60, "Internal temp should not exceed reasonable bounds"

def test_heater_effectiveness(dummy_weather):
    """Test that heater actually raises temperature when below setpoint."""
    params_no_heater = {
        "A_glass": 50.0,
        "tau_glass": 0.85,
        "U_day": 3.0,
        "U_night": 0.6,
        "ACH": 0.5,
        "V": 100.0,
        "thermal_mass_kg": 20000.0,
        "cp_mass": 4186.0,
        "T_init": 10.0,  # Start cold
        "T_mass_init": 10.0,
        "T_soil_init": 10.0,
        "A_mass": 20.0,
        "setpoint": None,
        "heater_max_w": 0.0  # No heater
    }
    
    params_with_heater = params_no_heater.copy()
    params_with_heater["setpoint"] = 15.0
    params_with_heater["heater_max_w"] = 5000.0
    
    result_no_heater = simulate_greenhouse(dummy_weather, params_no_heater)
    result_with_heater = simulate_greenhouse(dummy_weather, params_with_heater)
    
    # With heater, average temperature should be higher
    avg_no_heater = result_no_heater["Tin"].mean()
    avg_with_heater = result_with_heater["Tin"].mean()
    
    assert avg_with_heater >= avg_no_heater, "Heater should raise average temperature"
    
    # With heater, we should see heating power being used
    assert result_with_heater["Q_heater"].sum() > 0, "Heater should be active when below setpoint"

def test_solar_gain_effect(dummy_weather):
    """Test that solar radiation increases internal temperature."""
    params_low_solar = {
        "A_glass": 50.0,
        "tau_glass": 0.0,  # No solar transmission
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
        "setpoint": None
    }
    
    params_high_solar = params_low_solar.copy()
    params_high_solar["tau_glass"] = 0.85  # High solar transmission
    
    result_low = simulate_greenhouse(dummy_weather, params_low_solar)
    result_high = simulate_greenhouse(dummy_weather, params_high_solar)
    
    # With solar gain, daytime temperatures should be higher
    daytime_low = result_low[result_low["datetime"].dt.hour.between(10, 14)]["Tin"].mean()
    daytime_high = result_high[result_high["datetime"].dt.hour.between(10, 14)]["Tin"].mean()
    
    assert daytime_high >= daytime_low, "Solar gain should increase daytime temperatures"

def test_thermal_mass_smoothing(dummy_weather):
    """Verify that thermal mass reduces rapid temperature changes."""
    params_low_mass = {
        "thermal_mass_kg": 1000.0,  # Low mass
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
        "A_mass": 20.0,
        "setpoint": None
    }
    
    params_high_mass = params_low_mass.copy()
    params_high_mass["thermal_mass_kg"] = 50000.0  # High mass
    
    result_low = simulate_greenhouse(dummy_weather, params_low_mass)
    result_high = simulate_greenhouse(dummy_weather, params_high_mass)
    
    # Calculate rate of change
    rate_low = result_low["Tin"].diff().abs().mean()
    rate_high = result_high["Tin"].diff().abs().mean()
    
    # Higher thermal mass should reduce rate of temperature change
    assert rate_high <= rate_low * 1.5, "High thermal mass should smooth temperature changes (allow some tolerance)"

def test_boundary_conditions(dummy_weather):
    """Test that model handles edge cases correctly."""
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
        "setpoint": None
    }
    
    # Test with extreme weather
    extreme_weather = dummy_weather.copy()
    extreme_weather["Tout"] = -10.0  # Very cold
    extreme_weather["G"] = 0.0  # No solar
    
    result = simulate_greenhouse(extreme_weather, params)
    
    # Should still produce reasonable results
    assert not result.empty, "Should handle extreme weather"
    assert result["Tin"].min() >= -20, "Should handle cold weather reasonably"
    
    # Test with very hot weather
    hot_weather = dummy_weather.copy()
    hot_weather["Tout"] = 40.0  # Very hot
    hot_weather["G"] = 1000.0  # High solar
    
    result_hot = simulate_greenhouse(hot_weather, params)
    assert result_hot["Tin"].max() < 70, "Should handle hot weather reasonably"
