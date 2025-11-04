"""
Test that imports work correctly.
"""
import pytest
import sys
import os

def test_imports_work():
    """Test that all modules can be imported."""
    # Add worker directory to path
    worker_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if worker_dir not in sys.path:
        sys.path.insert(0, worker_dir)
    
    # Test imports
    from simulation.model import simulate_greenhouse, calculate_heat_to_threshold
    from simulation.weather import get_weather
    
    assert simulate_greenhouse is not None
    assert calculate_heat_to_threshold is not None
    assert get_weather is not None
    
    # Test worker import
    import importlib.util
    worker_file = os.path.join(worker_dir, 'worker.py')
    spec = importlib.util.spec_from_file_location("worker", worker_file)
    worker_module = importlib.util.module_from_spec(spec)
    sys.modules["worker"] = worker_module
    spec.loader.exec_module(worker_module)
    
    assert hasattr(worker_module, 'process_job')
    assert hasattr(worker_module, 'update_job_status')
    assert hasattr(worker_module, 'connect_redis')

