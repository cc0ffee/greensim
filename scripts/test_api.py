#!/usr/bin/env python3
"""
Integration test script for Greenhouse Simulation API.
Tests all endpoints against running Docker services.
"""
import requests
import time
import sys
import json

BASE_URL = "http://localhost:8080"
TIMEOUT = 60  # seconds to wait for job completion

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_success(text):
    """Print success message."""
    print(f"✅ {text}")

def print_error(text):
    """Print error message."""
    print(f"❌ {text}")

def test_health():
    """Test backend health endpoint."""
    print_header("Testing /health")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "ok":
            print_success("Health check passed")
            return True
        else:
            print_error(f"Unexpected response: {data}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return False

def test_submit_job():
    """Test job submission."""
    print_header("Testing /simulate (Submit Job)")
    try:
        payload = {
            "lat": 41.8781,
            "lon": -87.6298,
            "start_date": "2025-11-01",
            "end_date": "2025-11-02"
        }
        response = requests.post(
            f"{BASE_URL}/simulate",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if "job_id" in data and data.get("status") == "queued":
            job_id = data["job_id"]
            print_success(f"Job submitted successfully")
            print(f"   Job ID: {job_id}")
            print(f"   Status: {data['status']}")
            return job_id
        else:
            print_error(f"Unexpected response: {data}")
            return None
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return None

def test_get_job_status(job_id):
    """Test getting job status."""
    print_header(f"Testing /jobs/{job_id} (Get Job Status)")
    try:
        response = requests.get(f"{BASE_URL}/jobs/{job_id}", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data.get("job_id") == job_id and "status" in data:
            print_success("Job status retrieved")
            print(f"   Job ID: {data['job_id']}")
            print(f"   Status: {data['status']}")
            print(f"   Created: {data.get('created_at', 'N/A')}")
            return data["status"]
        else:
            print_error(f"Unexpected response: {data}")
            return None
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return None

def test_get_results(job_id, max_wait=TIMEOUT):
    """Test getting results (wait for completion)."""
    print_header(f"Testing /results/{job_id} (Get Results)")
    print(f"Waiting up to {max_wait} seconds for job completion...")
    
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{BASE_URL}/results/{job_id}", timeout=5)
            response.raise_for_status()
            data = response.json()
            
            status = data.get("status")
            if status != last_status:
                print(f"   Status: {status}")
                last_status = status
            
            if status == "done":
                result = data.get("result", {})
                data_points = result.get("data", [])
                summary = result.get("summary", {})
                
                print_success("Results ready!")
                print(f"   Data points: {len(data_points)}")
                if summary:
                    print(f"   Summary: {json.dumps(summary, indent=2)}")
                return data
            elif status == "error":
                error_msg = data.get("error", "Unknown error")
                print_error(f"Job failed: {error_msg}")
                return None
            elif status in ["queued", "running"]:
                # Still processing, wait
                time.sleep(2)
            else:
                print_error(f"Unknown status: {status}")
                return None
        except requests.exceptions.RequestException as e:
            print_error(f"Request failed: {e}")
            return None
    
    print_error(f"Timeout waiting for results after {max_wait}s")
    return None

def test_list_recent_jobs():
    """Test listing recent jobs."""
    print_header("Testing /results (List Recent Jobs)")
    try:
        response = requests.get(f"{BASE_URL}/results", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if "recent_job_ids" in data:
            job_ids = data["recent_job_ids"]
            print_success(f"Found {len(job_ids)} recent jobs")
            if job_ids:
                print(f"   Latest jobs: {', '.join(job_ids[:5])}")
            return job_ids
        else:
            print_error(f"Unexpected response: {data}")
            return None
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return None

def test_submit_job_with_custom_params():
    """Test job submission with custom parameters."""
    print_header("Testing /simulate (Custom Parameters)")
    try:
        payload = {
            "lat": 41.8781,
            "lon": -87.6298,
            "start_date": "2025-11-01",
            "end_date": "2025-11-02",
            "A_glass": 75.0,
            "U_day": 2.5,
            "setpoint": 15.0,
            "heater_max_w": 10000.0
        }
        response = requests.post(
            f"{BASE_URL}/simulate",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if "job_id" in data:
            print_success("Job with custom parameters submitted")
            print(f"   Job ID: {data['job_id']}")
            return data["job_id"]
        else:
            print_error(f"Unexpected response: {data}")
            return None
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return None

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  Greenhouse Simulation API - Integration Tests")
    print("=" * 60)
    print(f"\nTesting against: {BASE_URL}")
    print("Make sure services are running: docker-compose up -d\n")
    
    results = {
        "health": False,
        "submit_job": False,
        "get_status": False,
        "get_results": False,
        "list_jobs": False,
        "custom_params": False
    }
    
    # Test 1: Health check
    results["health"] = test_health()
    if not results["health"]:
        print("\n❌ Health check failed. Is the backend running?")
        print("   Run: docker-compose up -d")
        return 1
    
    # Test 2: Submit job
    job_id = test_submit_job()
    results["submit_job"] = job_id is not None
    if not job_id:
        return 1
    
    # Test 3: Get job status
    status = test_get_job_status(job_id)
    results["get_status"] = status is not None
    
    # Test 4: Get results (wait for completion)
    results_data = test_get_results(job_id)
    results["get_results"] = results_data is not None
    
    # Test 5: List recent jobs
    recent_jobs = test_list_recent_jobs()
    results["list_jobs"] = recent_jobs is not None
    
    # Test 6: Submit job with custom parameters
    custom_job_id = test_submit_job_with_custom_params()
    results["custom_params"] = custom_job_id is not None
    
    # Summary
    print_header("Test Summary")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅" if result else "❌"
        print(f"  {status} {test_name.replace('_', ' ').title()}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n" + "=" * 60)
        print("  ✅ All tests passed!")
        print("=" * 60 + "\n")
        return 0
    else:
        print("\n" + "=" * 60)
        print(f"  ❌ {total - passed} test(s) failed")
        print("=" * 60 + "\n")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

