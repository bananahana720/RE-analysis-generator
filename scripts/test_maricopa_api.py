#!/usr/bin/env python3
"""
Comprehensive test script for actual Maricopa County API endpoints.

This script tests the real Maricopa County Assessor API at https://mcassessor.maricopa.gov
with documented endpoints and proper authentication format.

Key Features:
- Tests actual API endpoints from official documentation
- Uses AUTHORIZATION header (not Bearer) as documented
- Comprehensive error handling for 401, 403, 404, 429 responses
- Rate limiting compliance (25 results per page)
- Pagination handling for search results
- Detailed test reporting with API response structure analysis
- Sample Phoenix ZIP codes and APNs for testing

Usage:
    python scripts/test_maricopa_api.py [--api-key YOUR_API_KEY] [--output-file report.json]
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import argparse
import sys
import os

# Sample data for testing
PHOENIX_ZIP_CODES = ["85031", "85033", "85035", "85048", "85083", "85254"]
PHOENIX_ADDRESSES = [
    "1234 N Central Ave Phoenix AZ",
    "5678 E Indian School Rd Phoenix AZ", 
    "9012 W Thomas Rd Phoenix AZ",
    "3456 S 7th St Phoenix AZ"
]
SAMPLE_APNS = [
    "101-01-001",    # Common APN format
    "101-01-001A",   # Variant with letter
    "101.01.001",    # Dot format
    "101 01 001",    # Space format
    "217-12-345",    # Different book/map
    "308-45-678"     # Another sample
]


@dataclass
class TestResult:
    """Test result data structure."""
    endpoint: str
    method: str
    url: str
    status_code: Optional[int]
    response_time_ms: float
    success: bool
    error_message: Optional[str]
    response_data: Optional[Dict[str, Any]]
    headers: Dict[str, str]
    timestamp: str


@dataclass
class EndpointAnalysis:
    """Analysis of API endpoint response structure."""
    endpoint: str
    sample_count: int
    response_fields: List[str]
    data_types: Dict[str, str]
    nested_structures: List[str]
    pagination_info: Optional[Dict[str, Any]]
    common_errors: List[str]


class MaricopaAPITester:
    """Comprehensive tester for Maricopa County API endpoints."""
    
    BASE_URL = "https://mcassessor.maricopa.gov"
    
    # Real API endpoints from documentation
    ENDPOINTS = {
        "search_property": "/search/property/?q={query}",
        "search_property_paged": "/search/property/?q={query}&page={page}",
        "search_subdivisions": "/search/sub/?q={query}",
        "search_rentals": "/search/rental/?q={query}",
        "parcel_details": "/parcel/{apn}",
        "property_info": "/parcel/{apn}/propertyinfo",
        "property_address": "/parcel/{apn}/address",
        "property_valuations": "/parcel/{apn}/valuations",
        "residential_details": "/parcel/{apn}/residential-details",
        "owner_details": "/parcel/{apn}/owner-details",
        "parcel_mcr": "/parcel/mcr/{mcr}",
        "parcel_str": "/parcel/str/{str}",
        "mapid_parcel": "/mapid/parcel/{apn}",
        "bpp_account": "/bpp/{type}/{acct}",
        "mobile_home": "/mh/{acct}",
        "mobile_home_vin": "/mh/vin/{vin}"
    }
    
    def __init__(self, api_key: Optional[str] = None, max_concurrent: int = 3):
        """Initialize the API tester.
        
        Args:
            api_key: API authentication token
            max_concurrent: Maximum concurrent requests
        """
        self.api_key = api_key
        self.max_concurrent = max_concurrent
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Test results storage
        self.test_results: List[TestResult] = []
        self.endpoint_analyses: List[EndpointAnalysis] = []
        
        # Rate limiting (25 results per page as documented)
        self.request_delay = 1.0  # 1 second between requests
        self.last_request_time = 0.0
        
        # Metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        print("[INIT] Initialized Maricopa API Tester")
        print(f"   Base URL: {self.BASE_URL}")
        print(f"   API Key: {'[PROVIDED]' if api_key else '[MISSING]'}")
        print(f"   Max Concurrent: {max_concurrent}")
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self._initialize_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._cleanup_session()
        
    async def _initialize_session(self):
        """Initialize aiohttp session with proper headers."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Phoenix-RE-API-Tester/1.0"
        }
        
        # Use AUTHORIZATION header as documented (not Bearer)
        if self.api_key:
            headers["AUTHORIZATION"] = self.api_key
            
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent,
            limit_per_host=2,
            enable_cleanup_closed=True
        )
        
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout,
            connector=connector
        )
        
    async def _cleanup_session(self):
        """Cleanup aiohttp session."""
        if self.session:
            await self.session.close()
            
    async def _rate_limit(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            wait_time = self.request_delay - time_since_last
            await asyncio.sleep(wait_time)
            
        self.last_request_time = time.time()
        
    async def _make_request(self, method: str, url: str, **kwargs) -> TestResult:
        """Make HTTP request and return detailed test result.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL to request
            **kwargs: Additional request parameters
            
        Returns:
            TestResult with comprehensive response analysis
        """
        await self._rate_limit()
        start_time = time.time()
        
        self.total_requests += 1
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                response_time_ms = (time.time() - start_time) * 1000
                
                # Get response data
                try:
                    response_data = await response.json()
                except Exception:
                    response_data = {"raw_text": await response.text()}
                    
                # Determine success based on status code
                success = 200 <= response.status < 300
                if success:
                    self.successful_requests += 1
                else:
                    self.failed_requests += 1
                    
                error_message = None
                if not success:
                    error_message = f"HTTP {response.status}: {response.reason}"
                    if isinstance(response_data, dict) and "error" in response_data:
                        error_message += f" - {response_data['error']}"
                        
                return TestResult(
                    endpoint=url.replace(self.BASE_URL, ""),
                    method=method,
                    url=url,
                    status_code=response.status,
                    response_time_ms=response_time_ms,
                    success=success,
                    error_message=error_message,
                    response_data=response_data,
                    headers=dict(response.headers),
                    timestamp=datetime.now().isoformat()
                )
                
        except Exception as e:
            self.failed_requests += 1
            response_time_ms = (time.time() - start_time) * 1000
            
            return TestResult(
                endpoint=url.replace(self.BASE_URL, ""),
                method=method,
                url=url,
                status_code=None,
                response_time_ms=response_time_ms,
                success=False,
                error_message=f"Request failed: {str(e)}",
                response_data=None,
                headers={},
                timestamp=datetime.now().isoformat()
            )
            
    async def test_search_endpoints(self) -> List[TestResult]:
        """Test all search-related endpoints."""
        print("\n[SEARCH] Testing Search Endpoints")
        results = []
        
        # Test property search with ZIP codes
        for zipcode in PHOENIX_ZIP_CODES[:3]:  # Test first 3 ZIP codes
            print(f"   Testing property search for ZIP {zipcode}...")
            url = f"{self.BASE_URL}{self.ENDPOINTS['search_property'].format(query=zipcode)}"
            result = await self._make_request("GET", url)
            results.append(result)
            
            # Test pagination if successful
            if result.success and result.response_data:
                total_results = result.response_data.get("total", 0)
                if total_results > 25:  # More than one page
                    print(f"   Testing pagination for ZIP {zipcode} (page 2)...")
                    page_url = f"{self.BASE_URL}{self.ENDPOINTS['search_property_paged'].format(query=zipcode, page=2)}"
                    page_result = await self._make_request("GET", page_url)
                    results.append(page_result)
                    
        # Test address search
        for address in PHOENIX_ADDRESSES[:2]:  # Test first 2 addresses
            print("   Testing property search for address...")
            url = f"{self.BASE_URL}{self.ENDPOINTS['search_property'].format(query=address.replace(' ', '%20'))}"
            result = await self._make_request("GET", url)
            results.append(result)
            
        # Test subdivision search
        print("   Testing subdivision search...")
        url = f"{self.BASE_URL}{self.ENDPOINTS['search_subdivisions'].format(query='Ahwatukee')}"
        result = await self._make_request("GET", url)
        results.append(result)
        
        # Test rental search
        print("   Testing rental search...")
        url = f"{self.BASE_URL}{self.ENDPOINTS['search_rentals'].format(query='85031')}"
        result = await self._make_request("GET", url)
        results.append(result)
        
        return results
        
    async def test_parcel_endpoints(self) -> List[TestResult]:
        """Test all parcel-related endpoints."""
        print("\n[PARCEL] Testing Parcel Endpoints")
        results = []
        
        for apn in SAMPLE_APNS[:3]:  # Test first 3 APNs
            print(f"   Testing parcel endpoints for APN {apn}...")
            
            # Test each parcel endpoint
            parcel_endpoints = [
                ("parcel_details", "Parcel Details"),
                ("property_info", "Property Info"),
                ("property_address", "Property Address"),
                ("property_valuations", "Property Valuations"),
                ("residential_details", "Residential Details"),
                ("owner_details", "Owner Details")
            ]
            
            for endpoint_key, description in parcel_endpoints:
                print(f"     -> {description}...")
                url = f"{self.BASE_URL}{self.ENDPOINTS[endpoint_key].format(apn=apn)}"
                result = await self._make_request("GET", url)
                results.append(result)
                
                # Break if authentication fails to avoid spam
                if result.status_code == 401:
                    print("     [WARNING] Authentication failed, stopping parcel tests")
                    return results
                    
        return results
        
    async def test_mapping_endpoints(self) -> List[TestResult]:
        """Test mapping and ID-related endpoints."""
        print("\n[MAPPING] Testing Mapping Endpoints")
        results = []
        
        for apn in SAMPLE_APNS[:2]:  # Test first 2 APNs
            print(f"   Testing map ID for APN {apn}...")
            url = f"{self.BASE_URL}{self.ENDPOINTS['mapid_parcel'].format(apn=apn)}"
            result = await self._make_request("GET", url)
            results.append(result)
            
        return results
        
    async def test_error_conditions(self) -> List[TestResult]:
        """Test various error conditions and edge cases."""
        print("\n[ERROR] Testing Error Conditions")
        results = []
        
        error_tests = [
            ("Invalid APN", "/parcel/INVALID-APN"),
            ("Non-existent property", "/search/property/?q=NONEXISTENT12345"),
            ("Empty query", "/search/property/?q="),
            ("Invalid endpoint", "/invalid/endpoint"),
            ("Malformed APN", "/parcel/123-abc-xyz"),
        ]
        
        for description, endpoint in error_tests:
            print(f"   Testing {description}...")
            url = f"{self.BASE_URL}{endpoint}"
            result = await self._make_request("GET", url)
            results.append(result)
            
        return results
        
    def _analyze_response_structure(self, results: List[TestResult]) -> List[EndpointAnalysis]:
        """Analyze response structures from test results."""
        print("\n[ANALYSIS] Analyzing Response Structures")
        
        analyses = []
        endpoint_groups = {}
        
        # Group results by endpoint pattern
        for result in results:
            if not result.success or not result.response_data:
                continue
                
            # Extract endpoint pattern
            endpoint_pattern = result.endpoint.split('?')[0]  # Remove query params
            if '/' in endpoint_pattern and len(endpoint_pattern.split('/')) > 2:
                # Replace specific IDs with placeholders
                parts = endpoint_pattern.split('/')
                for i, part in enumerate(parts):
                    if part.isdigit() or '-' in part or '.' in part:
                        parts[i] = '{id}'
                endpoint_pattern = '/'.join(parts)
                
            if endpoint_pattern not in endpoint_groups:
                endpoint_groups[endpoint_pattern] = []
            endpoint_groups[endpoint_pattern].append(result)
            
        # Analyze each endpoint group
        for endpoint_pattern, group_results in endpoint_groups.items():
            print(f"   Analyzing {endpoint_pattern}...")
            
            all_fields = set()
            data_types = {}
            nested_structures = []
            pagination_info = None
            common_errors = []
            
            for result in group_results:
                if result.response_data:
                    # Extract field names and types
                    self._extract_fields(result.response_data, all_fields, data_types, nested_structures)
                    
                    # Check for pagination
                    if any(key in result.response_data for key in ['total', 'page', 'per_page', 'pages']):
                        pagination_info = {
                            k: v for k, v in result.response_data.items() 
                            if k in ['total', 'page', 'per_page', 'pages', 'next_page', 'prev_page']
                        }
                        
                # Collect error patterns
                if not result.success and result.error_message:
                    common_errors.append(result.error_message)
                    
            analysis = EndpointAnalysis(
                endpoint=endpoint_pattern,
                sample_count=len(group_results),
                response_fields=sorted(all_fields),
                data_types=data_types,
                nested_structures=nested_structures,
                pagination_info=pagination_info,
                common_errors=list(set(common_errors))
            )
            analyses.append(analysis)
            
        return analyses
        
    def _extract_fields(self, data: Any, fields: set, types: dict, nested: list, prefix: str = ""):
        """Recursively extract field names and types from response data."""
        if isinstance(data, dict):
            for key, value in data.items():
                field_name = f"{prefix}.{key}" if prefix else key
                fields.add(field_name)
                
                if isinstance(value, (dict, list)):
                    nested.append(field_name)
                    self._extract_fields(value, fields, types, nested, field_name)
                else:
                    types[field_name] = type(value).__name__
                    
        elif isinstance(data, list) and data:
            # Analyze first item if list is not empty
            self._extract_fields(data[0], fields, types, nested, prefix)
            
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        print("\n[REPORT] Generating Test Report")
        
        # Calculate metrics
        success_rate = (self.successful_requests / max(1, self.total_requests)) * 100
        avg_response_time = sum(r.response_time_ms for r in self.test_results) / max(1, len(self.test_results))
        
        # Group results by status code
        status_codes = {}
        for result in self.test_results:
            if result.status_code:
                status_codes[result.status_code] = status_codes.get(result.status_code, 0) + 1
                
        # Generate endpoint analyses
        analyses = self._analyze_response_structure(self.test_results)
        
        report = {
            "test_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "success_rate_percent": round(success_rate, 2),
                "average_response_time_ms": round(avg_response_time, 2),
                "status_code_distribution": status_codes
            },
            "api_analysis": {
                "base_url": self.BASE_URL,
                "authentication_method": "AUTHORIZATION header",
                "tested_endpoints": len(set(r.endpoint for r in self.test_results)),
                "response_formats": "JSON",
                "pagination_supported": any(a.pagination_info for a in analyses)
            },
            "endpoint_analyses": [asdict(analysis) for analysis in analyses],
            "detailed_results": [asdict(result) for result in self.test_results],
            "recommendations": self._generate_recommendations()
        }
        
        return report
        
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        if not self.api_key:
            recommendations.append(
                "[AUTH] Obtain valid API key from Maricopa County (contact via website form)"
            )
            
        auth_failures = sum(1 for r in self.test_results if r.status_code == 401)
        if auth_failures > 0:
            recommendations.append(
                f"[AUTH] {auth_failures} authentication failures detected - verify API key and AUTHORIZATION header format"
            )
            
        rate_limit_hits = sum(1 for r in self.test_results if r.status_code == 429)
        if rate_limit_hits > 0:
            recommendations.append(
                f"[RATE] {rate_limit_hits} rate limit violations - implement proper rate limiting"
            )
            
        high_response_times = [r for r in self.test_results if r.response_time_ms > 5000]
        if high_response_times:
            recommendations.append(
                f"[PERF] {len(high_response_times)} requests took >5s - consider implementing timeouts and retries"
            )
            
        successful_endpoints = [r.endpoint for r in self.test_results if r.success]
        if successful_endpoints:
            recommendations.append(
                f"[SUCCESS] {len(set(successful_endpoints))} endpoints working - focus implementation on these first"
            )
            
        # API-specific recommendations
        recommendations.extend([
            "[IMPL] Implement pagination handling for search results (25 results per page)",
            "[RETRY] Add retry logic with exponential backoff for 5xx errors",
            "[CONFIG] Update client implementation to use correct base URL: https://mcassessor.maricopa.gov",
            "[AUTH] Fix authentication to use AUTHORIZATION header instead of Bearer token",
            "[ENDPOINTS] Update endpoint URLs to match documented API paths"
        ])
        
        return recommendations
        
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run complete test suite and generate report."""
        print("[START] Starting Comprehensive Maricopa County API Test")
        print("=" * 60)
        
        try:
            # Run all test categories
            search_results = await self.test_search_endpoints()
            self.test_results.extend(search_results)
            
            parcel_results = await self.test_parcel_endpoints()
            self.test_results.extend(parcel_results)
            
            mapping_results = await self.test_mapping_endpoints()
            self.test_results.extend(mapping_results)
            
            error_results = await self.test_error_conditions()
            self.test_results.extend(error_results)
            
            # Generate comprehensive report
            report = self.generate_test_report()
            
            print("\n[COMPLETE] Test Suite Complete!")
            print(f"   Total Requests: {self.total_requests}")
            print(f"   Success Rate: {report['test_summary']['success_rate_percent']}%")
            print(f"   Avg Response Time: {report['test_summary']['average_response_time_ms']:.1f}ms")
            
            return report
            
        except Exception as e:
            print(f"\n[ERROR] Test suite failed: {str(e)}")
            raise


async def main():
    """Main function to run API tests."""
    parser = argparse.ArgumentParser(description="Test Maricopa County API endpoints")
    parser.add_argument("--api-key", type=str, help="API authentication key")
    parser.add_argument("--output-file", type=str, default="maricopa_api_test_report.json", 
                       help="Output file for test report")
    parser.add_argument("--max-concurrent", type=int, default=3,
                       help="Maximum concurrent requests")
    
    args = parser.parse_args()
    
    # Check for API key in environment if not provided
    api_key = args.api_key or os.getenv("MARICOPA_API_KEY")
    
    if not api_key:
        print("[WARNING] No API key provided. Tests will likely fail with 401 errors.")
        print("   Use --api-key argument or set MARICOPA_API_KEY environment variable")
        print("   Contact Maricopa County for API access")
    
    try:
        async with MaricopaAPITester(api_key, args.max_concurrent) as tester:
            report = await tester.run_comprehensive_test()
            
            # Save report to file
            output_path = Path(args.output_file)
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
                
            print(f"\n[REPORT] Test report saved to: {output_path.absolute()}")
            
            # Print summary and recommendations
            print("\n[FINDINGS] Key Findings:")
            for rec in report['recommendations'][:5]:  # Show first 5 recommendations
                print(f"   {rec}")
                
            if len(report['recommendations']) > 5:
                print(f"   ... and {len(report['recommendations']) - 5} more (see full report)")
                
            # Return appropriate exit code
            success_rate = report['test_summary']['success_rate_percent']
            if success_rate > 50:
                print("\n[SUCCESS] Test suite completed successfully!")
                return 0
            else:
                print(f"\n[WARNING] Low success rate ({success_rate}%) - check authentication and network")
                return 1
                
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Test suite interrupted by user")
        return 130
    except Exception as e:
        print(f"\n[FAILURE] Test suite failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)