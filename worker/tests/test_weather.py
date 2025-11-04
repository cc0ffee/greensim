import pytest
import pandas as pd
import numpy as np
import sys
import os
from unittest.mock import patch, Mock

# Add worker directory to path for imports
worker_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if worker_dir not in sys.path:
    sys.path.insert(0, worker_dir)
from simulation.weather import get_weather

@pytest.mark.unit
def test_get_weather_success():
    """Test successful weather data retrieval."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "hourly": {
            "time": ["2025-11-01T00:00", "2025-11-01T01:00"],
            "temperature_2m": [10.0, 11.0],
            "shortwave_radiation": [0.0, 100.0],
            "relativehumidity_2m": [50.0, 55.0]
        }
    }
    mock_response.raise_for_status = Mock()
    
    with patch('simulation.weather.requests.get', return_value=mock_response):
        result = get_weather({"lat": 41.8781, "lon": -87.6298}, "2025-11-01", "2025-11-01")
    
    assert not result.empty
    assert len(result) == 2
    assert "datetime" in result.columns
    assert "Tout" in result.columns
    assert "G" in result.columns
    assert "RH" in result.columns
    assert result["Tout"].iloc[0] == 10.0
    assert result["RH"].iloc[0] == 0.5  # 50% / 100

@pytest.mark.unit
def test_get_weather_missing_rh():
    """Test weather data with missing relative humidity."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "hourly": {
            "time": ["2025-11-01T00:00"],
            "temperature_2m": [10.0],
            "shortwave_radiation": [0.0]
        }
    }
    mock_response.raise_for_status = Mock()
    
    with patch('simulation.weather.requests.get', return_value=mock_response):
        result = get_weather({"lat": 41.8781, "lon": -87.6298}, "2025-11-01", "2025-11-01")
    
    assert not result.empty
    assert result["RH"].iloc[0] == 0.5  # Default 50%

@pytest.mark.unit
def test_get_weather_api_error():
    """Test handling of API errors."""
    with patch('simulation.weather.requests.get', side_effect=Exception("API Error")):
        result = get_weather({"lat": 41.8781, "lon": -87.6298}, "2025-11-01", "2025-11-01")
    
    assert result.empty
    assert list(result.columns) == ["datetime", "Tout", "G", "RH"]

@pytest.mark.unit
def test_get_weather_invalid_format():
    """Test handling of invalid API response format."""
    mock_response = Mock()
    mock_response.json.return_value = {"invalid": "data"}
    mock_response.raise_for_status = Mock()
    
    with patch('simulation.weather.requests.get', return_value=mock_response):
        result = get_weather({"lat": 41.8781, "lon": -87.6298}, "2025-11-01", "2025-11-01")
    
    assert result.empty
    assert list(result.columns) == ["datetime", "Tout", "G", "RH"]

@pytest.mark.unit
def test_get_weather_timeout():
    """Test handling of timeout errors."""
    with patch('simulation.weather.requests.get', side_effect=Exception("Timeout")):
        result = get_weather({"lat": 41.8781, "lon": -87.6298}, "2025-11-01", "2025-11-01")
    
    assert result.empty

@pytest.mark.unit
def test_get_weather_different_timezone():
    """Test weather data retrieval with different timezone."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "hourly": {
            "time": ["2025-11-01T00:00"],
            "temperature_2m": [10.0],
            "shortwave_radiation": [0.0],
            "relativehumidity_2m": [50.0]
        }
    }
    mock_response.raise_for_status = Mock()
    
    with patch('simulation.weather.requests.get', return_value=mock_response) as mock_get:
        get_weather({"lat": 41.8781, "lon": -87.6298}, "2025-11-01", "2025-11-01", timezone="America/Chicago")
        # Check that timezone parameter was included in URL
        assert "timezone=America/Chicago" in mock_get.call_args[0][0]

