#!/usr/bin/env python3
"""
Test Phoenix MLS Selectors

This script tests the CSS selectors configured for the Phoenix MLS scraper
to ensure they are working correctly.

Usage:
    python scripts/test_phoenix_mls_selectors.py [--headless] [--config path/to/selectors.yaml]
"""

import asyncio
import argparse
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from playwright.async_api import async_playwright, Page
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class SelectorTester:
    """Tests Phoenix MLS selectors for validity."""

    def __init__(self, config_path: str, headless: bool = True):
        self.config_path = Path(config_path)
        self.headless = headless
        self.results = {
            "tested_at": datetime.now().isoformat(),
            "config_file": str(self.config_path),
            "tests": {},
        }

        # Load selector configuration
        with open(self.config_path) as f:
            self.selectors = yaml.safe_load(f)

    async def test_all(self):
        """Run all selector tests."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            )
            page = await context.new_page()

            try:
                # Test search page
                await self._test_search_page(page)

                # Test results page
                await self._test_results_page(page)

                # Test detail page
                await self._test_detail_page(page)

            finally:
                await browser.close()

        return self.results

    async def _test_search_page(self, page: Page):
        """Test search page selectors."""
        print("\n🔍 Testing search page selectors...")

        # Navigate to search page
        await page.goto("https://www.phoenixmlssearch.com")
        await page.wait_for_load_state("networkidle")

        search_tests = {}

        # Test search input
        input_config = self.selectors["search_page"]["search_input"]
        input_result = await self._test_selector(
            page, input_config["primary"], input_config["fallbacks"], "search input"
        )
        search_tests["search_input"] = input_result

        # Test submit button
        button_config = self.selectors["search_page"]["submit_button"]
        button_result = await self._test_selector(
            page, button_config["primary"], button_config["fallbacks"], "submit button"
        )
        search_tests["submit_button"] = button_result

        self.results["tests"]["search_page"] = search_tests

        # Print results
        self._print_test_results("Search Page", search_tests)

    async def _test_results_page(self, page: Page):
        """Test results page selectors."""
        print("\n🔍 Testing results page selectors...")

        # First, perform a search
        search_input = self.results["tests"]["search_page"]["search_input"]["working_selector"]
        submit_button = self.results["tests"]["search_page"]["submit_button"]["working_selector"]

        if not search_input or not submit_button:
            print("  ⚠️  Cannot test results page - search page selectors not working")
            return

        # Perform search
        await page.fill(search_input, "85001")
        await page.click(submit_button)

        # Wait for results
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
            await asyncio.sleep(2)  # Extra wait for dynamic content
        except:
            print("  ⚠️  Search did not complete successfully")
            return

        results_tests = {}

        # Test property container
        container_config = self.selectors["results_page"]["property_container"]
        container_result = await self._test_selector(
            page,
            container_config["primary"],
            container_config["fallbacks"],
            "property container",
            expect_multiple=True,
        )
        results_tests["property_container"] = container_result

        # If we found containers, test field selectors
        if container_result["working_selector"]:
            container_selector = container_result["working_selector"]

            # Test each field type
            for field_name, field_config in self.selectors["results_page"]["fields"].items():
                field_selector = f"{container_selector} {field_config['primary']}"
                field_fallbacks = [f"{container_selector} {fb}" for fb in field_config["fallbacks"]]

                field_result = await self._test_selector(
                    page, field_selector, field_fallbacks, f"{field_name} field"
                )
                results_tests[f"field_{field_name}"] = field_result

        self.results["tests"]["results_page"] = results_tests

        # Print results
        self._print_test_results("Results Page", results_tests)

    async def _test_detail_page(self, page: Page):
        """Test detail page selectors."""
        print("\n🔍 Testing detail page selectors...")

        # Get first property link from results
        link_selector = (
            self.results["tests"]
            .get("results_page", {})
            .get("field_link", {})
            .get("working_selector")
        )

        if not link_selector:
            print("  ⚠️  Cannot test detail page - no property links found")
            return

        # Click first property
        try:
            first_link = await page.query_selector(link_selector)
            if first_link:
                await first_link.click()
                await page.wait_for_load_state("networkidle", timeout=10000)
                await asyncio.sleep(2)
            else:
                print("  ⚠️  No property link found to click")
                return
        except Exception as e:
            print(f"  ⚠️  Could not navigate to detail page: {e}")
            return

        detail_tests = {}

        # Test main elements
        for element_name in ["address", "price", "description"]:
            if element_name in self.selectors["detail_page"]:
                element_config = self.selectors["detail_page"][element_name]
                element_result = await self._test_selector(
                    page, element_config["primary"], element_config["fallbacks"], element_name
                )
                detail_tests[element_name] = element_result

        # Test detail fields
        if "details" in self.selectors["detail_page"]:
            for field_name, field_config in self.selectors["detail_page"]["details"].items():
                field_result = await self._test_selector(
                    page, field_config["primary"], field_config["fallbacks"], f"detail {field_name}"
                )
                detail_tests[f"detail_{field_name}"] = field_result

        # Test features
        if "features" in self.selectors["detail_page"]:
            features_config = self.selectors["detail_page"]["features"]
            if "container" in features_config:
                features_result = await self._test_selector(
                    page,
                    features_config["container"]["primary"],
                    features_config["container"]["fallbacks"],
                    "features container",
                )
                detail_tests["features_container"] = features_result

        # Test images
        if "images" in self.selectors["detail_page"]:
            images_config = self.selectors["detail_page"]["images"]
            if "image" in images_config:
                images_result = await self._test_selector(
                    page,
                    images_config["image"]["primary"],
                    images_config["image"]["fallbacks"],
                    "property images",
                    expect_multiple=True,
                )
                detail_tests["images"] = images_result

        self.results["tests"]["detail_page"] = detail_tests

        # Print results
        self._print_test_results("Detail Page", detail_tests)

    async def _test_selector(
        self,
        page: Page,
        primary: str,
        fallbacks: List[str],
        element_name: str,
        expect_multiple: bool = False,
    ) -> Dict[str, Any]:
        """Test a selector with fallbacks."""
        result = {
            "element": element_name,
            "primary_selector": primary,
            "working_selector": None,
            "status": "failed",
            "count": 0,
            "sample_text": None,
            "errors": [],
        }

        # Try primary selector
        try:
            elements = await page.query_selector_all(primary)
            if elements:
                result["working_selector"] = primary
                result["status"] = "primary"
                result["count"] = len(elements)

                # Get sample text from first element
                if elements[0]:
                    try:
                        text = await elements[0].text_content()
                        result["sample_text"] = text[:100] if text else None
                    except:
                        pass

                return result
        except Exception as e:
            result["errors"].append(f"Primary selector error: {str(e)}")

        # Try fallbacks
        for fallback in fallbacks:
            try:
                elements = await page.query_selector_all(fallback)
                if elements:
                    result["working_selector"] = fallback
                    result["status"] = "fallback"
                    result["count"] = len(elements)

                    # Get sample text
                    if elements[0]:
                        try:
                            text = await elements[0].text_content()
                            result["sample_text"] = text[:100] if text else None
                        except:
                            pass

                    return result
            except Exception as e:
                result["errors"].append(f"Fallback '{fallback}' error: {str(e)}")

        return result

    def _print_test_results(self, section: str, tests: Dict[str, Any]):
        """Print test results for a section."""
        print(f"\n{section} Results:")
        print("-" * 50)

        for test_name, result in tests.items():
            status_icon = "✅" if result["status"] != "failed" else "❌"
            status_text = (
                "PRIMARY"
                if result["status"] == "primary"
                else "FALLBACK"
                if result["status"] == "fallback"
                else "FAILED"
            )

            print(f"{status_icon} {result['element']}: {status_text}")

            if result["working_selector"]:
                print(f"   Selector: {result['working_selector']}")
                print(f"   Count: {result['count']}")
                if result["sample_text"]:
                    print(f"   Sample: {result['sample_text'][:50]}...")
            else:
                print("   ⚠️  No working selector found")
                if result["errors"]:
                    print(f"   Errors: {result['errors'][0]}")

    def generate_report(self):
        """Generate a summary report of test results."""
        print("\n" + "=" * 60)
        print("SELECTOR TEST SUMMARY")
        print("=" * 60)

        total_tests = 0
        passed_tests = 0
        primary_working = 0
        fallback_working = 0

        for page_name, page_tests in self.results["tests"].items():
            for test_name, test_result in page_tests.items():
                total_tests += 1
                if test_result["status"] != "failed":
                    passed_tests += 1
                    if test_result["status"] == "primary":
                        primary_working += 1
                    else:
                        fallback_working += 1

        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests} ({passed_tests / total_tests * 100:.1f}%)")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"\nPrimary Selectors Working: {primary_working}")
        print(f"Using Fallback Selectors: {fallback_working}")

        # Save detailed report
        report_path = Path("output/selector_tests/test_report.yaml")
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, "w") as f:
            yaml.dump(self.results, f, default_flow_style=False)

        print(f"\nDetailed report saved to: {report_path}")

        # Generate update recommendations
        self._generate_recommendations()

    def _generate_recommendations(self):
        """Generate recommendations for selector updates."""
        print("\n" + "-" * 60)
        print("RECOMMENDATIONS")
        print("-" * 60)

        updates_needed = []

        for page_name, page_tests in self.results["tests"].items():
            for test_name, test_result in page_tests.items():
                if test_result["status"] == "failed":
                    updates_needed.append(
                        f"- {page_name}.{test_result['element']}: No working selector found"
                    )
                elif test_result["status"] == "fallback":
                    updates_needed.append(
                        f"- {page_name}.{test_result['element']}: "
                        f"Update primary selector to: {test_result['working_selector']}"
                    )

        if updates_needed:
            print("\nSelectors that need updating:")
            for update in updates_needed:
                print(update)
        else:
            print("\n✅ All primary selectors are working correctly!")

        print("\nNext steps:")
        print("1. Run selector discovery: python scripts/discover_phoenix_mls_selectors.py")
        print("2. Update config/selectors/phoenix_mls.yaml with new selectors")
        print("3. Re-run this test to verify updates")


async def main():
    parser = argparse.ArgumentParser(description="Test Phoenix MLS selectors")
    parser.add_argument(
        "--config",
        default="config/selectors/phoenix_mls.yaml",
        help="Path to selector configuration file",
    )
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")

    args = parser.parse_args()

    print("🚀 Starting Phoenix MLS Selector Tests")
    print("=" * 60)
    print(f"Config file: {args.config}")
    print(f"Headless: {args.headless}")

    tester = SelectorTester(args.config, headless=args.headless)

    try:
        await tester.test_all()
        tester.generate_report()
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
