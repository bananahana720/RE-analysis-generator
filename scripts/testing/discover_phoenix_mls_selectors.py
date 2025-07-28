#!/usr/bin/env python3
"""
Phoenix MLS Selector Discovery Script

This script automatically discovers CSS selectors from phoenixmlssearch.com
to help update the scraper when the website structure changes.

Usage:
    python scripts/discover_phoenix_mls_selectors.py [--headless] [--save-html]
"""

import asyncio
import argparse
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup, Tag


class SelectorDiscovery:
    """Discovers CSS selectors from Phoenix MLS website."""

    def __init__(self, headless: bool = False, save_html: bool = False):
        self.headless = headless
        self.save_html = save_html
        self.results = {
            "discovered_at": datetime.now().isoformat(),
            "url": "https://www.phoenixmlssearch.com",
            "selectors": {},
        }

    async def discover(self):
        """Main discovery process."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            )
            page = await context.new_page()

            try:
                # Discover search page selectors
                await self._discover_search_page(page)

                # Perform search and discover results
                await self._discover_results_page(page)

                # Discover property detail page
                await self._discover_detail_page(page)

            finally:
                await browser.close()

        return self.results

    async def _discover_search_page(self, page: Page):
        """Discover selectors on the search page."""
        print("🔍 Discovering search page selectors...")

        await page.goto("https://www.phoenixmlssearch.com")
        await page.wait_for_load_state("networkidle")

        html = await page.content()
        if self.save_html:
            self._save_html("search_page.html", html)

        soup = BeautifulSoup(html, "html.parser")

        # Find search inputs
        search_inputs = self._find_search_inputs(soup)

        # Find submit buttons
        submit_buttons = self._find_submit_buttons(soup)

        # Test selectors
        working_input = await self._test_selectors(page, search_inputs, "input")
        working_button = await self._test_selectors(page, submit_buttons, "button")

        self.results["selectors"]["search_page"] = {
            "search_input": {"working": working_input, "all_found": search_inputs},
            "submit_button": {"working": working_button, "all_found": submit_buttons},
        }

        print(f"  ✓ Found {len(search_inputs)} search inputs")
        print(f"  ✓ Found {len(submit_buttons)} submit buttons")

    async def _discover_results_page(self, page: Page):
        """Discover selectors on search results page."""
        print("\n🔍 Discovering results page selectors...")

        # Perform search
        search_selector = self.results["selectors"]["search_page"]["search_input"]["working"]
        button_selector = self.results["selectors"]["search_page"]["submit_button"]["working"]

        if search_selector and button_selector:
            await page.fill(search_selector, "85001")
            await page.click(button_selector)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)  # Extra wait for dynamic content

            html = await page.content()
            if self.save_html:
                self._save_html("results_page.html", html)

            soup = BeautifulSoup(html, "html.parser")

            # Find property containers
            containers = self._find_property_containers(soup)

            if containers:
                # Analyze first container for field selectors
                first_container = soup.select_one(containers[0])
                if first_container:
                    fields = self._analyze_property_fields(first_container)

                    self.results["selectors"]["results_page"] = {
                        "property_container": containers,
                        "fields": fields,
                    }

                    print(f"  ✓ Found {len(containers)} container patterns")
                    print(f"  ✓ Extracted {len(fields)} field types")

    async def _discover_detail_page(self, page: Page):
        """Discover selectors on property detail page."""
        print("\n🔍 Discovering detail page selectors...")

        # Click on first property
        containers = self.results["selectors"].get("results_page", {}).get("property_container", [])

        if containers:
            try:
                # Find first property link
                first_property = await page.query_selector(f"{containers[0]} a")
                if first_property:
                    await first_property.click()
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(2)

                    html = await page.content()
                    if self.save_html:
                        self._save_html("detail_page.html", html)

                    soup = BeautifulSoup(html, "html.parser")

                    # Find detail page elements
                    details = self._analyze_detail_page(soup)

                    self.results["selectors"]["detail_page"] = details

                    print(f"  ✓ Found {len(details)} detail elements")
            except Exception as e:
                print(f"  ⚠️  Could not navigate to detail page: {e}")

    def _find_search_inputs(self, soup: BeautifulSoup) -> List[str]:
        """Find potential search input selectors."""
        selectors = []

        # Look for input elements with search-related attributes
        for input_elem in soup.find_all("input"):
            # Check various attributes
            attrs = input_elem.attrs

            # ID-based selector
            if "id" in attrs:
                selectors.append(f"#{attrs['id']}")

            # Name-based selector
            if "name" in attrs:
                name = attrs["name"]
                if any(
                    keyword in name.lower() for keyword in ["search", "zip", "location", "address"]
                ):
                    selectors.append(f"input[name='{name}']")

            # Placeholder-based selector
            if "placeholder" in attrs:
                placeholder = attrs["placeholder"]
                if any(keyword in placeholder.lower() for keyword in ["search", "zip", "enter"]):
                    selectors.append(f"input[placeholder*='{placeholder[:20]}']")

            # Class-based selector
            if "class" in attrs:
                classes = attrs["class"]
                for cls in classes:
                    if any(keyword in cls.lower() for keyword in ["search", "input", "field"]):
                        selectors.append(f"input.{cls}")

        return list(set(selectors))  # Remove duplicates

    def _find_submit_buttons(self, soup: BeautifulSoup) -> List[str]:
        """Find potential submit button selectors."""
        selectors = []

        # Look for buttons and submit inputs
        for elem in soup.find_all(["button", "input"]):
            if elem.name == "input" and elem.get("type") != "submit":
                continue

            attrs = elem.attrs

            # ID-based selector
            if "id" in attrs:
                selectors.append(f"#{attrs['id']}")

            # Type-based selector
            if elem.get("type") == "submit":
                selectors.append(f"{elem.name}[type='submit']")

            # Text content (for buttons)
            if elem.name == "button":
                text = elem.get_text().strip().lower()
                if any(keyword in text for keyword in ["search", "find", "go", "submit"]):
                    # Class-based selector
                    if "class" in attrs:
                        classes = attrs["class"]
                        selectors.append(f"button.{classes[0]}")

                    # Aria-label selector
                    if "aria-label" in attrs:
                        selectors.append(f"button[aria-label*='{attrs['aria-label'][:20]}']")

        return list(set(selectors))

    def _find_property_containers(self, soup: BeautifulSoup) -> List[str]:
        """Find selectors for property listing containers."""
        selectors = []

        # Common patterns for property listings
        patterns = [
            ("class", ["property", "listing", "result", "card"]),
            ("data-", ["listing", "property", "result"]),
            ("itemtype", ["schema.org/Product", "schema.org/House"]),
        ]

        # Find elements that likely contain property listings
        for elem in soup.find_all(["div", "article", "section", "li"]):
            attrs = elem.attrs

            # Check class names
            if "class" in attrs:
                classes = " ".join(attrs["class"]).lower()
                for _, keywords in patterns:
                    if any(keyword in classes for keyword in keywords):
                        # Build selector
                        main_class = [
                            c for c in attrs["class"] if any(k in c.lower() for k in keywords)
                        ][0]
                        selectors.append(f".{main_class}")
                        break

            # Check data attributes
            for attr, value in attrs.items():
                if attr.startswith("data-") and any(
                    keyword in attr.lower() for _, keywords in patterns for keyword in keywords
                ):
                    selectors.append(f"[{attr}]")

        # Filter to most likely containers (appear multiple times)
        selector_counts = {}
        for selector in selectors:
            count = len(soup.select(selector))
            if count > 2:  # Likely a repeating pattern
                selector_counts[selector] = count

        # Return selectors sorted by frequency
        return sorted(selector_counts.keys(), key=lambda x: selector_counts[x], reverse=True)[:5]

    def _analyze_property_fields(self, container: Tag) -> Dict[str, List[str]]:
        """Analyze a property container for field selectors."""
        fields = {"address": [], "price": [], "beds": [], "baths": [], "sqft": [], "link": []}

        # Address patterns
        for elem in container.find_all(["h1", "h2", "h3", "h4", "span", "div"]):
            text = elem.get_text().strip()
            if re.search(r"\d+\s+\w+\s+(St|Street|Ave|Avenue|Rd|Road|Dr|Drive)", text):
                fields["address"].append(self._build_selector(elem))

        # Price patterns
        for elem in container.find_all(text=re.compile(r"\$[\d,]+", re.IGNORECASE)):
            parent = elem.parent
            if parent:
                fields["price"].append(self._build_selector(parent))

        # Beds/Baths/Sqft patterns
        for elem in container.find_all(
            text=re.compile(r"\d+\s*(bed|bd|bath|ba|sq\s*ft|sqft)", re.IGNORECASE)
        ):
            parent = elem.parent
            if parent:
                text = parent.get_text().lower()
                if "bed" in text or "bd" in text:
                    fields["beds"].append(self._build_selector(parent))
                elif "bath" in text or "ba" in text:
                    fields["baths"].append(self._build_selector(parent))
                elif "sq" in text or "ft" in text:
                    fields["sqft"].append(self._build_selector(parent))

        # Links
        for link in container.find_all("a", href=True):
            href = link.get("href", "")
            if "property" in href or "listing" in href or re.search(r"/\d+", href):
                fields["link"].append(self._build_selector(link))

        # Remove duplicates and limit to top 3
        for field in fields:
            fields[field] = list(set(fields[field]))[:3]

        return fields

    def _analyze_detail_page(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Analyze property detail page for selectors."""
        details = {
            "address": [],
            "price": [],
            "description": [],
            "features": [],
            "images": [],
            "details_table": [],
        }

        # Address - usually in h1 or prominent location
        for elem in soup.find_all(["h1", "h2"]):
            text = elem.get_text().strip()
            if re.search(r"\d+\s+\w+\s+(St|Street|Ave|Avenue|Rd|Road|Dr|Drive)", text):
                details["address"].append(self._build_selector(elem))

        # Price - large text with $
        for elem in soup.find_all(text=re.compile(r"\$[\d,]+", re.IGNORECASE)):
            parent = elem.parent
            if parent and parent.name in ["span", "div", "h2", "h3"]:
                # Check if it's likely the main price (not in a table)
                if not parent.find_parent("table"):
                    details["price"].append(self._build_selector(parent))

        # Description - long text blocks
        for elem in soup.find_all(["p", "div"]):
            text = elem.get_text().strip()
            if len(text) > 200 and not elem.find_parent("table"):
                details["description"].append(self._build_selector(elem))

        # Features - lists or feature sections
        for elem in soup.find_all(["ul", "div"]):
            if "feature" in str(elem.attrs).lower() or "amenity" in str(elem.attrs).lower():
                details["features"].append(self._build_selector(elem))

        # Images
        for img in soup.find_all("img"):
            src = img.get("src", "")
            # Filter out small images (likely icons)
            if not any(skip in src.lower() for skip in ["icon", "logo", "avatar"]):
                parent = img.find_parent(["div", "figure", "a"])
                if parent:
                    details["images"].append(self._build_selector(parent) + " img")

        # Details table
        for table in soup.find_all("table"):
            details["details_table"].append(self._build_selector(table))

        # Limit results
        for field in details:
            details[field] = list(set(details[field]))[:3]

        return details

    def _build_selector(self, elem: Tag) -> str:
        """Build a CSS selector for an element."""
        if elem.get("id"):
            return f"#{elem['id']}"

        selector = elem.name

        if elem.get("class"):
            # Use the most specific class
            classes = elem["class"]
            if isinstance(classes, list):
                # Filter out common/generic classes
                specific_classes = [
                    c for c in classes if len(c) > 3 and c not in ["col", "row", "container"]
                ]
                if specific_classes:
                    selector += f".{specific_classes[0]}"

        # Add data attributes if present
        for attr, value in elem.attrs.items():
            if attr.startswith("data-") and isinstance(value, str):
                selector = f"[{attr}='{value}']"
                break

        return selector

    async def _test_selectors(
        self, page: Page, selectors: List[str], element_type: str
    ) -> Optional[str]:
        """Test which selectors actually work on the page."""
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    # Additional validation based on element type
                    if element_type == "input":
                        # Check if it's visible and editable
                        is_visible = await element.is_visible()
                        is_editable = await element.is_editable()
                        if is_visible and is_editable:
                            return selector
                    elif element_type == "button":
                        # Check if it's visible and clickable
                        is_visible = await element.is_visible()
                        if is_visible:
                            return selector
                    else:
                        return selector
            except:
                continue

        return None

    def _save_html(self, filename: str, html: str):
        """Save HTML for manual inspection."""
        output_dir = Path("output/selector_discovery")
        output_dir.mkdir(parents=True, exist_ok=True)

        filepath = output_dir / filename
        filepath.write_text(html, encoding="utf-8")
        print(f"  💾 Saved HTML to {filepath}")

    def save_results(self, output_file: str = "phoenix_mls_selectors.json"):
        """Save discovery results to JSON file."""
        output_path = Path("output/selector_discovery") / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\n✅ Results saved to {output_path}")

        # Also create a YAML config
        self._create_yaml_config()

    def _create_yaml_config(self):
        """Create a YAML configuration file from results."""
        yaml_content = f"""# Phoenix MLS Selectors Configuration
# Generated: {self.results["discovered_at"]}
# URL: {self.results["url"]}

search_page:
  search_input:
    primary: "{self.results["selectors"]["search_page"]["search_input"]["working"] or "UPDATE_ME"}"
    fallbacks:
"""

        for selector in self.results["selectors"]["search_page"]["search_input"]["all_found"][:3]:
            yaml_content += f'      - "{selector}"\n'

        yaml_content += f"""
  submit_button:
    primary: "{self.results["selectors"]["search_page"]["submit_button"]["working"] or "UPDATE_ME"}"
    fallbacks:
"""

        for selector in self.results["selectors"]["search_page"]["submit_button"]["all_found"][:3]:
            yaml_content += f'      - "{selector}"\n'

        if "results_page" in self.results["selectors"]:
            yaml_content += f"""
results_page:
  property_container:
    primary: "{self.results["selectors"]["results_page"]["property_container"][0] if self.results["selectors"]["results_page"]["property_container"] else "UPDATE_ME"}"
    fallbacks:
"""
            for selector in self.results["selectors"]["results_page"]["property_container"][1:4]:
                yaml_content += f'      - "{selector}"\n'

            yaml_content += "\n  fields:\n"

            for field, selectors in self.results["selectors"]["results_page"]["fields"].items():
                if selectors:
                    yaml_content += f"""    {field}:
      primary: "{selectors[0]}"
      fallbacks:
"""
                    for selector in selectors[1:3]:
                        yaml_content += f'        - "{selector}"\n'

        if "detail_page" in self.results["selectors"]:
            yaml_content += "\ndetail_page:\n"

            for field, selectors in self.results["selectors"]["detail_page"].items():
                if selectors:
                    yaml_content += f"""  {field}:
    primary: "{selectors[0]}"
    fallbacks:
"""
                    for selector in selectors[1:3]:
                        yaml_content += f'      - "{selector}"\n'

        output_path = Path("output/selector_discovery/phoenix_mls_selectors.yaml")
        output_path.write_text(yaml_content)
        print(f"✅ YAML config saved to {output_path}")


async def main():
    parser = argparse.ArgumentParser(description="Discover Phoenix MLS selectors")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--save-html", action="store_true", help="Save HTML files for inspection")

    args = parser.parse_args()

    print("🚀 Starting Phoenix MLS Selector Discovery")
    print("=" * 50)

    discovery = SelectorDiscovery(headless=args.headless, save_html=args.save_html)

    try:
        await discovery.discover()
        discovery.save_results()

        print("\n📊 Summary:")
        print("  - Search page selectors: ✓")
        if "results_page" in discovery.results["selectors"]:
            print("  - Results page selectors: ✓")
        if "detail_page" in discovery.results["selectors"]:
            print("  - Detail page selectors: ✓")

    except Exception as e:
        print(f"\n❌ Error during discovery: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
