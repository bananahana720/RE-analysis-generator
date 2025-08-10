#\!/bin/bash
set -e

echo "🚨 CRITICAL: Production Restoration Test Suite"
echo "🕒 System has been DOWN for 2+ days"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results directory
RESULTS_DIR="test_results/production_restoration_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo "📊 Results will be saved to: $RESULTS_DIR"

# Function to run test and capture results
run_test() {
    local test_name="$1"
    local test_command="$2"
    local output_file="$RESULTS_DIR/${test_name}.json"
    
    echo -e "\n🔄 Running: $test_name"
    echo "Command: $test_command"
    
    if eval "$test_command" > "$output_file" 2>&1; then
        echo -e "✅ ${GREEN}$test_name PASSED${NC}"
        return 0
    else
        echo -e "❌ ${RED}$test_name FAILED${NC}"
        return 1
    fi
}

# Initialize test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test 1: Secrets Configuration Validation
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if run_test "secrets_validation" "python scripts/validation/validate_secrets.py validate"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test 2: Production Restoration Validation
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if run_test "production_restoration" "python scripts/testing/production/production_restoration_validator.py --full"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test 3: Performance Validation
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if run_test "performance_validation" "python scripts/testing/production/performance_validator.py --performance"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Generate summary report
echo -e "\n================================================"
echo "🏁 PRODUCTION RESTORATION TEST SUMMARY"
echo "================================================"
echo "📊 Total Tests: $TOTAL_TESTS"
echo -e "✅ ${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "❌ ${RED}Failed: $FAILED_TESTS${NC}"
echo "📁 Results saved in: $RESULTS_DIR"

# Generate JSON summary
cat > "$RESULTS_DIR/summary.json" << EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "test_suite": "Production Restoration",
    "total_tests": $TOTAL_TESTS,
    "passed_tests": $PASSED_TESTS,
    "failed_tests": $FAILED_TESTS,
    "success_rate": $(echo "scale=2; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l),
    "overall_status": "$([ $FAILED_TESTS -eq 0 ] && echo "PRODUCTION_READY" || echo "PRODUCTION_NOT_READY")",
    "results_directory": "$RESULTS_DIR"
}
EOF

# Final determination
if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n🎉 ${GREEN}PRODUCTION RESTORATION SUCCESSFUL${NC}"
    echo "✅ All tests passed - system is ready for production use"
    echo "🚀 Proceed with production workload testing"
    exit 0
else
    echo -e "\n🚨 ${RED}PRODUCTION RESTORATION INCOMPLETE${NC}"
    echo "❌ $FAILED_TESTS test(s) failed - system is NOT ready for production"
    echo "🔧 Address all failures before declaring production ready"
    echo "⚠️  System has been down 2+ days - prioritize resolution"
    exit 1
fi
BASH_END < /dev/null
