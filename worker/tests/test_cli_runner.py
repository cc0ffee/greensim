import pytest
import pandas as pd
import json
import sys
import os
from unittest.mock import patch, mock_open, MagicMock
import tempfile
import shutil

# Add worker directory to path for imports
worker_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if worker_dir not in sys.path:
    sys.path.insert(0, worker_dir)
from cli_runner import run_simulation

@pytest.mark.unit
def test_run_simulation_basic(tmp_path):
    """Test basic simulation run."""
    # Create temporary config file
    config = {
        "name": "test",
        "location": {"lat": 41.8781, "lon": -87.6298},
        "start_date": "2025-11-01",
        "end_date": "2025-11-01",
        "parameters": {
            "A_glass": 50.0,
            "tau_glass": 0.85,
            "U_day": 2.0,
            "U_night": 1.5,
            "ACH": 0.5,
            "V": 100.0,
            "thermal_mass_kg": 20000.0
        }
    }
    
    config_file = tmp_path / "test_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f)
    
    # Create results directory
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    
    # Mock weather and simulation
    mock_weather = pd.DataFrame({
        "datetime": pd.date_range("2025-11-01", periods=24, freq="h"),
        "Tout": [10.0] * 24,
        "G": [100.0] * 24,
        "RH": [0.5] * 24
    })
    
    mock_result = pd.DataFrame({
        "datetime": pd.date_range("2025-11-01", periods=24, freq="h"),
        "Tin": [15.0] * 24,
        "T_mass": [14.0] * 24,
        "T_soil": [13.0] * 24,
        "Tout": [10.0] * 24,
        "Q_heater": [0.0] * 24,
        "Q_latent": [0.0] * 24,
        "Q_to_threshold": [0.0] * 24
    })
    
    with patch('cli_runner.get_weather', return_value=mock_weather), \
         patch('cli_runner.simulate_greenhouse', return_value=mock_result), \
         patch('cli_runner.plt.savefig'), \
         patch('cli_runner.plt.show'):
        
        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            run_simulation(str(config_file))
        finally:
            os.chdir(original_cwd)
        
        # Check that CSV was created
        assert (results_dir / "test_results.csv").exists()

@pytest.mark.unit
def test_run_simulation_with_setpoint(tmp_path):
    """Test simulation with setpoint threshold."""
    config = {
        "name": "test",
        "location": {"lat": 41.8781, "lon": -87.6298},
        "start_date": "2025-11-01",
        "end_date": "2025-11-01",
        "parameters": {
            "A_glass": 50.0,
            "setpoint": 10.0
        }
    }
    
    config_file = tmp_path / "test_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f)
    
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    
    mock_weather = pd.DataFrame({
        "datetime": pd.date_range("2025-11-01", periods=24, freq="h"),
        "Tout": [5.0] * 24,
        "G": [0.0] * 24,
        "RH": [0.5] * 24
    })
    
    mock_result = pd.DataFrame({
        "datetime": pd.date_range("2025-11-01", periods=24, freq="h"),
        "Tin": [8.0] * 24,  # Below setpoint
        "T_mass": [8.0] * 24,
        "T_soil": [8.0] * 24,
        "Tout": [5.0] * 24,
        "Q_heater": [1000.0] * 24,
        "Q_latent": [0.0] * 24,
        "Q_to_threshold": [5000.0] * 24
    })
    
    with patch('cli_runner.get_weather', return_value=mock_weather), \
         patch('cli_runner.simulate_greenhouse', return_value=mock_result), \
         patch('cli_runner.plt.savefig'), \
         patch('cli_runner.plt.show'):
        
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            run_simulation(str(config_file))
        finally:
            os.chdir(original_cwd)
        
        # Should have created results
        assert (results_dir / "test_results.csv").exists()

@pytest.mark.unit
def test_run_simulation_with_reference_data(tmp_path):
    """Test simulation with reference data comparison."""
    config = {
        "name": "test",
        "location": {"lat": 41.8781, "lon": -87.6298},
        "start_date": "2025-11-01",
        "end_date": "2025-11-01",
        "parameters": {}
    }
    
    config_file = tmp_path / "test_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f)
    
    # Create reference data file in tmp_path/data (where cli_runner will look)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ref_data = pd.DataFrame({
        "datetime": pd.date_range("2025-11-01", periods=24, freq="h"),
        "Tin_typical": [15.0] * 24,
        "Tin_min": [10.0] * 24,
        "Tin_max": [20.0] * 24
    })
    ref_data.to_csv(data_dir / "reference_greenhouse_temps.csv", index=False)
    
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    
    mock_weather = pd.DataFrame({
        "datetime": pd.date_range("2025-11-01", periods=24, freq="h"),
        "Tout": [10.0] * 24,
        "G": [100.0] * 24,
        "RH": [0.5] * 24
    })
    
    mock_result = pd.DataFrame({
        "datetime": pd.date_range("2025-11-01", periods=24, freq="h"),
        "Tin": [15.0] * 24,
        "T_mass": [14.0] * 24,
        "T_soil": [13.0] * 24,
        "Tout": [10.0] * 24,
        "Q_heater": [0.0] * 24,
        "Q_latent": [0.0] * 24,
        "Q_to_threshold": [0.0] * 24
    })
    
    # Mock the functions and patch os.path.dirname to return tmp_path
    # This allows cli_runner to find the reference data file
    import cli_runner
    cli_runner_file = cli_runner.__file__
    
    with patch('cli_runner.get_weather', return_value=mock_weather), \
         patch('cli_runner.simulate_greenhouse', return_value=mock_result), \
         patch('cli_runner.plt.savefig'), \
         patch('cli_runner.plt.show'):
        
        # Patch os.path.dirname to return tmp_path when called with cli_runner's __file__
        original_dirname = os.path.dirname
        def mock_dirname(path):
            # If it's the cli_runner.py file path, return tmp_path
            if path == cli_runner_file or (isinstance(path, str) and 'cli_runner.py' in path):
                return str(tmp_path)
            return original_dirname(path)
        
        with patch('os.path.dirname', side_effect=mock_dirname):
            original_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                run_simulation(str(config_file))
            finally:
                os.chdir(original_cwd)
        
        assert (results_dir / "test_results.csv").exists()

@pytest.mark.unit
def test_run_simulation_default_config():
    """Test simulation with default config path."""
    mock_weather = pd.DataFrame({
        "datetime": pd.date_range("2025-11-01", periods=24, freq="h"),
        "Tout": [10.0] * 24,
        "G": [100.0] * 24,
        "RH": [0.5] * 24
    })
    
    mock_result = pd.DataFrame({
        "datetime": pd.date_range("2025-11-01", periods=24, freq="h"),
        "Tin": [15.0] * 24,
        "T_mass": [14.0] * 24,
        "T_soil": [13.0] * 24,
        "Tout": [10.0] * 24,
        "Q_heater": [0.0] * 24,
        "Q_latent": [0.0] * 24,
        "Q_to_threshold": [0.0] * 24
    })
    
    with patch('cli_runner.get_weather', return_value=mock_weather), \
         patch('cli_runner.simulate_greenhouse', return_value=mock_result), \
         patch('cli_runner.plt.savefig'), \
         patch('cli_runner.plt.show'), \
         patch('builtins.open', mock_open(read_data='{"parameters": {}}')):
        # Just test that it doesn't crash
        try:
            run_simulation("configs/default.json")
        except (FileNotFoundError, json.JSONDecodeError):
            pass  # Expected if config file doesn't exist in test env

