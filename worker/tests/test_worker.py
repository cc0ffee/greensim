import pytest
import redis
import json
import time
import sys
import os
from unittest.mock import patch, MagicMock

# Add worker directory to path for imports
worker_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if worker_dir not in sys.path:
    sys.path.insert(0, worker_dir)

# Import after path is set - import directly as module
# The worker directory is now in sys.path, so 'worker' module can find 'simulation'
import importlib
import importlib.util

# Load worker.py as a module
worker_file = os.path.join(worker_dir, 'worker.py')
spec = importlib.util.spec_from_file_location("worker", worker_file)
worker_module = importlib.util.module_from_spec(spec)
# Register it as 'worker' module so imports work correctly
sys.modules["worker"] = worker_module
spec.loader.exec_module(worker_module)

# Import functions from the loaded module
process_job = worker_module.process_job
update_job_status = worker_module.update_job_status
connect_redis = worker_module.connect_redis

@pytest.fixture
def rdb():
    """Redis database fixture for testing."""
    try:
        r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
        r.ping()  # Test connection
        yield r
        r.flushdb()  # Clean up after test
    except redis.ConnectionError:
        pytest.skip("Redis not available")

@pytest.mark.unit
def test_update_job_status(rdb):
    """Test job status update functionality."""
    job_id = "test_status"
    meta_key = f"job_meta:{job_id}"
    
    # Set initial meta
    initial_meta = {"status": "queued", "created_at": "2025-11-01T00:00:00"}
    rdb.set(meta_key, json.dumps(initial_meta))
    
    # Update status
    update_job_status(rdb, job_id, "running")
    
    # Check updated status
    meta = json.loads(rdb.get(meta_key))
    assert meta["status"] == "running"
    assert "updated_at" in meta

@pytest.mark.unit
def test_update_job_status_with_error(rdb):
    """Test job status update with error message."""
    job_id = "test_error"
    meta_key = f"job_meta:{job_id}"
    
    initial_meta = {"status": "queued", "created_at": "2025-11-01T00:00:00"}
    rdb.set(meta_key, json.dumps(initial_meta))
    
    update_job_status(rdb, job_id, "error", "Test error message")
    
    meta = json.loads(rdb.get(meta_key))
    assert meta["status"] == "error"
    assert meta["error"] == "Test error message"

@pytest.mark.integration
def test_worker_job_success(rdb):
    """Test successful job processing."""
    job = {
        "job_id": "test123",
        "params": {
            "A_glass": 50.0,
            "T_init": 20.0,
            "lat": 41.8781,
            "lon": -87.6298,
            "start_date": "2025-11-01",
            "end_date": "2025-11-01"
        },
        "created_at": "2025-10-05T00:00:00"
    }

    # Set initial job meta
    meta = {"status": "queued", "created_at": job["created_at"]}
    rdb.set(f"job_meta:{job['job_id']}", json.dumps(meta))

    # Process the job
    process_job(job, rdb)

    # Check job status
    meta_after = json.loads(rdb.get(f"job_meta:{job['job_id']}"))
    assert meta_after["status"] == "done"
    
    # Check result exists
    result = json.loads(rdb.get(f"job_result:{job['job_id']}"))
    assert result["job_id"] == "test123"
    assert "data" in result
    assert "summary" in result

@pytest.mark.integration
def test_worker_job_error_handling(rdb):
    """Test job processing error handling."""
    # Use a job that will cause an error by mocking get_weather to raise an exception
    job = {
        "job_id": "test_error",
        "params": {
            "lat": 41.8781,
            "lon": -87.6298,
            "start_date": "2025-11-01",
            "end_date": "2025-11-02"
        },
        "created_at": "2025-10-05T00:00:00"
    }

    meta = {"status": "queued", "created_at": job["created_at"]}
    rdb.set(f"job_meta:{job['job_id']}", json.dumps(meta))

    # Mock get_weather to raise an exception - patch it in the worker_module namespace
    # Since get_weather is imported at module level, we need to patch it where it's used
    original_get_weather = worker_module.get_weather
    worker_module.get_weather = MagicMock(side_effect=Exception("Test error: Weather API failed"))
    try:
        # Process job (should handle error gracefully)
        process_job(job, rdb)
    finally:
        # Restore original
        worker_module.get_weather = original_get_weather

    # Check job status is error
    meta_after = json.loads(rdb.get(f"job_meta:{job['job_id']}"))
    assert meta_after["status"] == "error"
    assert "error" in meta_after

@pytest.mark.unit
def test_connect_redis():
    """Test Redis connection function."""
    with patch('worker.redis.from_url') as mock_redis:
        mock_redis.return_value = MagicMock()
        rdb = connect_redis()
        assert rdb is not None
        mock_redis.assert_called_once()
