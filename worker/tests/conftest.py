"""
Pytest configuration and shared fixtures.
"""
import pytest
import sys
import os

# Add worker directory to path for imports BEFORE any other imports
# This ensures that 'simulation' module can be found when worker.py is imported
worker_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if worker_dir not in sys.path:
    sys.path.insert(0, worker_dir)
    
# Also add the parent directory in case tests are run from project root
parent_dir = os.path.dirname(worker_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

@pytest.fixture(scope="session")
def test_data_dir():
    """Return path to test data directory."""
    return os.path.join(os.path.dirname(__file__), '..', 'data')

