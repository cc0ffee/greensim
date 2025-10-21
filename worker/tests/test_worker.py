import pytest
import redis
import json
import time
from worker import process_job


@pytest.fixture
def rdb():
    r = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)
    yield r
    r.flushdb()  # Clean up after test

def test_worker_job(rdb):
    job = {
        "job_id": "test123",
        "params": {"A_glass": 50.0, "T_init": 20.0},
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
    result = json.loads(rdb.get(f"job_result:{job['job_id']}"))
    assert result["job_id"] == "test123"
