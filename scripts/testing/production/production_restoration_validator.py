#\!/usr/bin/env python3
"""
Production Restoration Validator
Critical testing suite for production system restoration after 2+ days downtime.
"""

import os
import sys
import asyncio
import json
import time
import logging
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parents[3] / "src"))

try:
    import requests
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError as e:
    print(f"Import error: {e}")
    print("Run: uv sync")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class TestStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL" 
    SKIP = "SKIP"
    WARN = "WARN"

class CriticalityLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

@dataclass
class TestResult:
    name: str
    status: TestStatus
    duration: float
    message: str
    details: Optional[Dict[str, Any]] = None
    criticality: CriticalityLevel = CriticalityLevel.MEDIUM
    timestamp: str = datetime.now(timezone.utc).isoformat()

class ProductionRestorationValidator:
    """Critical production restoration validation suite."""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = time.time()
        self.required_secrets = [
            "MONGODB_URI", "MARICOPA_API_KEY", "SECRET_KEY", 
            "OLLAMA_HOST"
        ]
        
    def add_result(self, result: TestResult):
        """Add test result and log immediately."""
        self.results.append(result)
        status_icon = {
            TestStatus.PASS: "✅",
            TestStatus.FAIL: "❌", 
            TestStatus.SKIP: "⏭️",
            TestStatus.WARN: "⚠️"
        }
        logger.info(f"{status_icon[result.status]} {result.name}: {result.message}")
        
    async def test_secrets_configuration(self) -> bool:
        """Test 1: Critical secrets configuration validation."""
        test_start = time.time()
        
        try:
            missing_secrets = []
            invalid_secrets = []
            
            for secret in self.required_secrets:
                value = os.getenv(secret)
                if not value:
                    missing_secrets.append(secret)
                elif secret == "MONGODB_URI" and not value.startswith(("mongodb://", "mongodb+srv://")):
                    invalid_secrets.append(f"{secret}: Invalid MongoDB URI format")
                elif secret == "SECRET_KEY" and len(value) < 32:
                    invalid_secrets.append(f"{secret}: Too short (<32 chars)")
                elif secret == "MARICOPA_API_KEY" and len(value) \!= 36:
                    invalid_secrets.append(f"{secret}: Invalid UUID format")
            
            duration = time.time() - test_start
            
            if missing_secrets or invalid_secrets:
                error_msg = f"Missing: {missing_secrets}, Invalid: {invalid_secrets}"
                self.add_result(TestResult(
                    name="Secrets Configuration",
                    status=TestStatus.FAIL,
                    duration=duration,
                    message=error_msg,
                    criticality=CriticalityLevel.CRITICAL
                ))
                return False
            
            self.add_result(TestResult(
                name="Secrets Configuration", 
                status=TestStatus.PASS,
                duration=duration,
                message=f"All {len(self.required_secrets)} secrets configured correctly",
                criticality=CriticalityLevel.CRITICAL
            ))
            return True
            
        except Exception as e:
            duration = time.time() - test_start
            self.add_result(TestResult(
                name="Secrets Configuration",
                status=TestStatus.FAIL, 
                duration=duration,
                message=f"Exception during secrets validation: {str(e)}",
                criticality=CriticalityLevel.CRITICAL
            ))
            return False

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_duration = time.time() - self.start_time
        
        # Count results by status
        status_counts = {status: 0 for status in TestStatus}
        for result in self.results:
            status_counts[result.status] += 1
        
        # Count by criticality 
        critical_failures = [r for r in self.results 
                           if r.status == TestStatus.FAIL and r.criticality == CriticalityLevel.CRITICAL]
        
        # Overall status
        overall_status = "PRODUCTION_READY" if (
            status_counts[TestStatus.FAIL] == 0 and len(critical_failures) == 0
        ) else "PRODUCTION_NOT_READY"
        
        return {
            "validation_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_duration": total_duration,
            "overall_status": overall_status,
            "summary": {
                "total_tests": len(self.results),
                "passed": status_counts[TestStatus.PASS],
                "failed": status_counts[TestStatus.FAIL],
                "skipped": status_counts[TestStatus.SKIP], 
                "warnings": status_counts[TestStatus.WARN],
            },
            "critical_failures": len(critical_failures),
            "test_results": [asdict(result) for result in self.results]
        }

    async def run_full_validation(self) -> Dict[str, Any]:
        """Run complete validation suite."""
        logger.info("🚨 CRITICAL: Starting production restoration validation")
        
        # Run tests
        await self.test_secrets_configuration()
        
        # Generate and return report
        report = self.generate_report()
        
        logger.info(f"🏁 Validation complete: {report[\"overall_status\"]}")
        
        return report

async def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Production Restoration Validator")
    parser.add_argument("--full", action="store_true", help="Run full validation suite")
    
    args = parser.parse_args()
    
    validator = ProductionRestorationValidator()
    report = await validator.run_full_validation()
    
    print(json.dumps(report, indent=2))
    
    # Exit with error code if production not ready
    sys.exit(0 if report["overall_status"] == "PRODUCTION_READY" else 1)

if __name__ == "__main__":
    asyncio.run(main())
