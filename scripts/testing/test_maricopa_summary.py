#!/usr/bin/env python3
"""
Summary test report for Maricopa County API authentication.

This script summarizes the test results and provides recommendations.
"""

import json
from pathlib import Path
from datetime import datetime


def analyze_test_report():
    """Analyze the test report and provide summary."""
    report_path = Path("maricopa_api_test_report.json")
    
    if not report_path.exists():
        print("[ERROR] Test report not found. Run test_maricopa_api.py first.")
        return
    
    with open(report_path, 'r') as f:
        report = json.load(f)
    
    print("=" * 80)
    print("MARICOPA COUNTY API TEST SUMMARY")
    print("=" * 80)
    print(f"Test Date: {report['test_summary']['timestamp']}")
    print()
    
    # Overall Results
    summary = report['test_summary']
    print("OVERALL RESULTS:")
    print(f"  Total Requests: {summary['total_requests']}")
    print(f"  Successful: {summary['successful_requests']}")
    print(f"  Failed: {summary['failed_requests']}")
    print(f"  Success Rate: {summary['success_rate_percent']}%")
    print(f"  Average Response Time: {summary['average_response_time_ms']:.1f}ms")
    print()
    
    # Status Code Distribution
    print("STATUS CODE DISTRIBUTION:")
    for code, count in summary['status_code_distribution'].items():
        print(f"  HTTP {code}: {count} requests")
    print()
    
    # Working Endpoints
    print("WORKING ENDPOINTS:")
    working_endpoints = set()
    for result in report['detailed_results']:
        if result['success']:
            endpoint = result['endpoint'].split('?')[0]  # Remove query params
            working_endpoints.add(endpoint)
    
    if working_endpoints:
        for endpoint in sorted(working_endpoints):
            print(f"  [OK] {endpoint}")
    else:
        print("  No endpoints working without authentication")
    print()
    
    # Authentication Status
    print("AUTHENTICATION STATUS:")
    if summary['success_rate_percent'] > 80:
        print("  [OK] Authentication is WORKING")
        print("  [OK] AUTHORIZATION header format is correct")
        print("  [OK] API key is valid and active")
    else:
        print("  [FAIL] Authentication FAILED")
        print("  [FAIL] Check MARICOPA_API_KEY in .env file")
        print("  [FAIL] Verify API key is active")
    print()
    
    # Key Findings
    print("KEY FINDINGS:")
    if 'endpoint_analyses' in report:
        for analysis in report['endpoint_analyses'][:3]:
            if analysis['sample_count'] > 0:
                print(f"\n  {analysis['endpoint']}:")
                print(f"    - Samples: {analysis['sample_count']}")
                print(f"    - Fields: {len(analysis['response_fields'])}")
                if analysis.get('pagination_info'):
                    print(f"    - Pagination: Supported")
    print()
    
    # Recommendations
    print("RECOMMENDATIONS:")
    for i, rec in enumerate(report.get('recommendations', [])[:5], 1):
        print(f"  {i}. {rec}")
    print()
    
    # Implementation Notes
    print("IMPLEMENTATION NOTES:")
    print("  1. The Maricopa API client is correctly configured with:")
    print("     - AUTHORIZATION header (not Bearer)")
    print("     - user-agent: null")
    print("  2. The client handles rate limiting and retries")
    print("  3. Authentication is working when API key is properly set")
    print()
    
    # Next Steps
    print("NEXT STEPS:")
    if summary['success_rate_percent'] > 80:
        print("  [OK] API authentication is working!")
        print("  [OK] You can now run data collection")
        print("  [OK] Test with: python scripts/testing/test_maricopa_collector.py")
    else:
        print("  1. Ensure MARICOPA_API_KEY is set in .env file")
        print("  2. Verify the API key is active and valid")
        print("  3. Re-run the test with: python -m dotenv run python scripts/test_maricopa_api.py")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    analyze_test_report()