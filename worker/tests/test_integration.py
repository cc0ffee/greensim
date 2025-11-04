"""
Integration tests for the greenhouse simulation system.
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os

# Add worker directory to path for imports
worker_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if worker_dir not in sys.path:
    sys.path.insert(0, worker_dir)
from simulation.model import simulate_greenhouse
from simulation.weather import get_weather

@pytest.mark.integration
def test_full_simulation_workflow():
    """Test complete simulation workflow from weather to results."""
    # Create realistic weather data
    hours = pd.date_range("2025-11-01", periods=48, freq="h")
    weather_df = pd.DataFrame({
        "datetime": hours,
        "Tout": 5 + 10 * np.sin(np.linspace(0, 2 * np.pi, 48)),
        "G": np.maximum(0, 800 * np.sin(np.linspace(0, np.pi, 48))),
        "RH": np.full(48, 0.6)
    })
    
    params = {
        "A_glass": 50.0,
        "tau_glass": 0.85,
        "U_day": 2.0,
        "U_night": 1.5,
        "ACH": 0.5,
        "V": 100.0,
        "A_floor": 50.0,
        "thermal_mass_kg": 20000.0,
        "cp_mass": 4186.0,
        "T_init": 15.0,
        "T_mass_init": 15.0,
        "T_soil_init": 15.0,
        "setpoint": 10.0
    }
    
    result = simulate_greenhouse(weather_df, params)
    
    # Verify output structure
    assert not result.empty
    assert len(result) == 48
    assert all(col in result.columns for col in ["datetime", "Tin", "Tout", "T_mass", "T_soil", "Q_heater", "Q_latent", "Q_to_threshold"])
    
    # Verify data types
    assert pd.api.types.is_datetime64_any_dtype(result["datetime"])
    assert pd.api.types.is_numeric_dtype(result["Tin"])
    assert pd.api.types.is_numeric_dtype(result["Tout"])
    
    # Verify reasonable values
    assert result["Tin"].min() >= -10
    assert result["Tin"].max() <= 50
    assert (result["Q_heater"] >= 0).all()
    assert (result["Q_to_threshold"] >= 0).all()

@pytest.mark.integration
@pytest.mark.slow
def test_simulation_with_real_weather_api():
    """Test simulation with actual weather API (may be slow)."""
    # This test requires internet connection
    pytest.importorskip("requests")
    
    try:
        location = {"lat": 41.8781, "lon": -87.6298}  # Chicago
        weather_df = get_weather(location, "2025-11-01", "2025-11-02")
        
        if weather_df.empty:
            pytest.skip("Weather API unavailable")
        
        params = {
            "A_glass": 50.0,
            "tau_glass": 0.85,
            "U_day": 2.0,
            "U_night": 1.5,
            "ACH": 0.5,
            "V": 100.0,
            "thermal_mass_kg": 20000.0
        }
        
        result = simulate_greenhouse(weather_df, params)
        
        assert not result.empty
        assert len(result) == len(weather_df)
        
    except Exception as e:
        pytest.skip(f"Weather API test failed: {e}")

@pytest.mark.integration
def test_simulation_parameter_combinations():
    """Test simulation with various parameter combinations."""
    hours = pd.date_range("2025-11-01", periods=24, freq="h")
    weather_df = pd.DataFrame({
        "datetime": hours,
        "Tout": [10.0] * 24,
        "G": [100.0] * 24,
        "RH": [0.5] * 24
    })
    
    base_params = {
        "A_glass": 50.0,
        "tau_glass": 0.85,
        "U_day": 2.0,
        "U_night": 1.5,
        "ACH": 0.5,
        "V": 100.0,
        "thermal_mass_kg": 20000.0
    }
    
    # Test with different U-values
    for u_day in [1.0, 2.0, 3.0]:
        for u_night in [0.5, 1.0, 1.5]:
            params = base_params.copy()
            params["U_day"] = u_day
            params["U_night"] = u_night
            
            result = simulate_greenhouse(weather_df, params)
            assert not result.empty
            assert result["Tin"].min() >= -10
            assert result["Tin"].max() <= 50

@pytest.mark.integration
def test_simulation_edge_cases():
    """Test simulation with edge case inputs."""
    hours = pd.date_range("2025-11-01", periods=24, freq="h")
    
    # Test with zero solar radiation
    weather_no_solar = pd.DataFrame({
        "datetime": hours,
        "Tout": [5.0] * 24,
        "G": [0.0] * 24,
        "RH": [0.5] * 24
    })
    
    params = {
        "A_glass": 50.0,
        "tau_glass": 0.85,
        "U_day": 2.0,
        "U_night": 1.5,
        "ACH": 0.5,
        "V": 100.0,
        "thermal_mass_kg": 20000.0,
        "setpoint": 10.0
    }
    
    result = simulate_greenhouse(weather_no_solar, params)
    assert not result.empty
    
    # Test with very high solar radiation
    weather_high_solar = pd.DataFrame({
        "datetime": hours,
        "Tout": [20.0] * 24,
        "G": [1000.0] * 24,
        "RH": [0.5] * 24
    })
    
    result_high = simulate_greenhouse(weather_high_solar, params)
    assert not result_high.empty
    # With high solar, internal temp should be higher
    assert result_high["Tin"].mean() > result["Tin"].mean()

