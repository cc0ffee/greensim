#!/bin/bash
# Integration test script for Greenhouse Simulation API
# Tests all endpoints against running Docker services

set -e

BASE_URL="http://localhost:8080"
TIMEOUT=60  # seconds to wait for job completion

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo "============================================================"
    echo "  $1"
    echo "============================================================"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Test 1: Health check
test_health() {
    print_header "Testing /health"
    if curl -s -f "${BASE_URL}/health" | grep -q '"status":"ok"'; then
        print_success "Health check passed"
        return 0
    else
        print_error "Health check failed"
        return 1
    fi
}

# Test 2: Submit job
test_submit_job() {
    print_header "Testing /simulate (Submit Job)"
    
    RESPONSE=$(curl -s -X POST "${BASE_URL}/simulate" \
        -H "Content-Type: application/json" \
        -d '{
            "lat": 41.8781,
            "lon": -87.6298,
            "start_date": "2025-11-01",
            "end_date": "2025-11-02"
        }')
    
    JOB_ID=$(echo "$RESPONSE" | grep -o '"job_id":"[^"]*' | cut -d'"' -f4 || echo "")
    
    if [ -z "$JOB_ID" ]; then
        print_error "Failed to get job_id"
        echo "Response: $RESPONSE"
        return 1
    fi
    
    print_success "Job submitted successfully"
    echo "   Job ID: $JOB_ID"
    echo "   Response: $RESPONSE"
    echo "$JOB_ID"
    return 0
}

# Test 3: Get job status
test_get_job_status() {
    local job_id=$1
    print_header "Testing /jobs/${job_id} (Get Job Status)"
    
    RESPONSE=$(curl -s "${BASE_URL}/jobs/${job_id}")
    
    if echo "$RESPONSE" | grep -q '"status"'; then
        STATUS=$(echo "$RESPONSE" | grep -o '"status":"[^"]*' | cut -d'"' -f4)
        print_success "Job status retrieved"
        echo "   Status: $STATUS"
        echo "$STATUS"
        return 0
    else
        print_error "Failed to get job status"
        echo "Response: $RESPONSE"
        return 1
    fi
}

# Test 4: Get results (wait for completion)
test_get_results() {
    local job_id=$1
    print_header "Testing /results/${job_id} (Get Results)"
    echo "Waiting up to ${TIMEOUT}s for job completion..."
    
    start_time=$(date +%s)
    last_status=""
    
    while true; do
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))
        
        if [ $elapsed -ge $TIMEOUT ]; then
            print_error "Timeout waiting for results after ${TIMEOUT}s"
            return 1
        fi
        
        RESPONSE=$(curl -s "${BASE_URL}/results/${job_id}")
        STATUS=$(echo "$RESPONSE" | grep -o '"status":"[^"]*' | cut -d'"' -f4 || echo "")
        
        if [ "$STATUS" != "$last_status" ] && [ -n "$STATUS" ]; then
            echo "   Status: $STATUS"
            last_status="$STATUS"
        fi
        
        if [ "$STATUS" == "done" ]; then
            print_success "Results ready!"
            echo "   Response preview: $(echo "$RESPONSE" | head -c 200)..."
            return 0
        elif [ "$STATUS" == "error" ]; then
            ERROR=$(echo "$RESPONSE" | grep -o '"error":"[^"]*' | cut -d'"' -f4 || echo "Unknown error")
            print_error "Job failed: $ERROR"
            return 1
        fi
        
        sleep 2
    done
}

# Test 5: List recent jobs
test_list_recent_jobs() {
    print_header "Testing /results (List Recent Jobs)"
    
    RESPONSE=$(curl -s "${BASE_URL}/results")
    
    if echo "$RESPONSE" | grep -q '"recent_job_ids"'; then
        COUNT=$(echo "$RESPONSE" | grep -o '"recent_job_ids":\[[^]]*\]' | grep -o ',' | wc -l || echo "0")
        COUNT=$((COUNT + 1))
        print_success "Found recent jobs"
        echo "   Response: $RESPONSE"
        return 0
    else
        print_error "Failed to get recent jobs"
        echo "Response: $RESPONSE"
        return 1
    fi
}

# Main test execution
main() {
    echo ""
    echo "============================================================"
    echo "  Greenhouse Simulation API - Integration Tests"
    echo "============================================================"
    echo ""
    echo "Testing against: ${BASE_URL}"
    echo "Make sure services are running: docker-compose up -d"
    echo ""
    
    # Track results
    TESTS_PASSED=0
    TESTS_FAILED=0
    
    # Test 1: Health check
    if test_health; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
        print_warning "Health check failed. Is the backend running?"
        echo "   Run: docker-compose up -d"
        exit 1
    fi
    
    # Test 2: Submit job
    JOB_ID=$(test_submit_job)
    if [ $? -eq 0 ]; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
        exit 1
    fi
    
    # Test 3: Get job status
    if test_get_job_status "$JOB_ID" > /dev/null; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
    
    # Test 4: Get results
    if test_get_results "$JOB_ID"; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
    
    # Test 5: List recent jobs
    if test_list_recent_jobs; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
    
    # Summary
    print_header "Test Summary"
    TOTAL=$((TESTS_PASSED + TESTS_FAILED))
    echo "Passed: ${TESTS_PASSED}/${TOTAL}"
    echo "Failed: ${TESTS_FAILED}/${TOTAL}"
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo "============================================================"
        print_success "All tests passed!"
        echo "============================================================"
        echo ""
        return 0
    else
        echo "============================================================"
        print_error "${TESTS_FAILED} test(s) failed"
        echo "============================================================"
        echo ""
        return 1
    fi
}

# Run main function
main "$@"

