# Phoenix MLS Selector Update Guide

## Current CSS Selector Analysis

The Phoenix MLS scraper uses CSS selectors to extract property data from phoenixmlssearch.com. These selectors need periodic updates as the website's HTML structure changes.

### Current Selector Categories

#### Search Page Selectors
- **Search Input**: `input[name="search"], input[placeholder*="zip"], #zipcode-input`
- **Submit Button**: `button[type="submit"], button[aria-label*="Search"]`
- **Result Container**: `.property-card, .listing-item, .search-result`

#### Search Results Page Selectors
- **Property Cards**: `.property-card, .listing-item`
- **Property Link**: `a[href*="property"], a.property-link`
- **Address**: `.address, .property-address`
- **Price**: `.price, .listing-price`
- **Beds**: `.beds, [data-testid="beds"]`
- **Baths**: `.baths, [data-testid="baths"]`
- **Sqft**: `.sqft, [data-testid="sqft"]`

#### Property Detail Page Selectors
- **Address**: `h1.address, .property-address, [data-testid="address"]`
- **Price**: `.price, .listing-price, [data-testid="price"]`
- **Description**: `.description, .property-description, [data-testid="description"]`
- **Features**: `.feature-item, .amenity`
- **Images**: `.property-image img, .gallery img`

## Methods for Obtaining Updated Selectors

### Method 1: Manual Browser Inspection (Most Accurate)

1. **Navigate to phoenixmlssearch.com**
   ```
   1. Open Chrome or Firefox
   2. Go to https://www.phoenixmlssearch.com
   3. Clear cookies/cache for fresh session
   ```

2. **Inspect Search Page**
   ```
   1. Right-click on search input field
   2. Select "Inspect Element"
   3. Note the element's:
      - ID (if present)
      - Class names
      - Name attribute
      - Placeholder text
      - Parent container structure
   ```

3. **Perform a Search**
   ```
   1. Enter a Phoenix zipcode (e.g., 85001)
   2. Submit the search
   3. Wait for results to load
   ```

4. **Inspect Search Results**
   ```
   For each property card:
   1. Right-click → Inspect
   2. Record selectors for:
      - Container element
      - Property link
      - Address text
      - Price
      - Beds/Baths/Sqft
   ```

5. **Inspect Property Detail Page**
   ```
   1. Click on a property
   2. Inspect each data element
   3. Look for:
      - Consistent class patterns
      - Data attributes (data-testid, data-field)
      - ARIA labels
      - Semantic HTML elements
   ```

### Method 2: Automated Selector Discovery Script

Create this script to automatically discover selectors:

```python
# selector_discovery.py
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json

async def discover_selectors():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Visit search page
        await page.goto("https://www.phoenixmlssearch.com")
        
        # Get page HTML
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find potential search inputs
        search_inputs = []
        for input_elem in soup.find_all('input'):
            attrs = input_elem.attrs
            if any(key in str(attrs).lower() for key in ['search', 'zip', 'location']):
                selector = f"input"
                if attrs.get('id'):
                    selector = f"#{attrs['id']}"
                elif attrs.get('name'):
                    selector = f"input[name='{attrs['name']}']"
                elif attrs.get('class'):
                    selector = f"input.{'.'.join(attrs['class'])}"
                search_inputs.append({
                    'selector': selector,
                    'attributes': attrs
                })
        
        # Find potential submit buttons
        buttons = []
        for button in soup.find_all(['button', 'input']):
            if button.get('type') in ['submit', 'button']:
                text = button.get_text().strip().lower()
                if any(word in text for word in ['search', 'find', 'go']):
                    selector = self._build_selector(button)
                    buttons.append({
                        'selector': selector,
                        'text': text,
                        'attributes': button.attrs
                    })
        
        # Perform search
        await page.fill(search_inputs[0]['selector'], "85001")
        await page.click(buttons[0]['selector'])
        await page.wait_for_load_state('networkidle')
        
        # Analyze results page
        results_html = await page.content()
        results_soup = BeautifulSoup(results_html, 'html.parser')
        
        # Find property containers
        property_patterns = self._find_property_patterns(results_soup)
        
        print(json.dumps({
            'search_inputs': search_inputs,
            'buttons': buttons,
            'property_patterns': property_patterns
        }, indent=2))
        
        await browser.close()

def _build_selector(element):
    """Build a CSS selector for an element."""
    if element.get('id'):
        return f"#{element['id']}"
    
    selector = element.name
    if element.get('class'):
        selector += '.' + '.'.join(element['class'])
    
    return selector

def _find_property_patterns(soup):
    """Find patterns in property listings."""
    patterns = {
        'containers': [],
        'prices': [],
        'addresses': [],
        'details': []
    }
    
    # Look for repeating structures
    for elem in soup.find_all(['div', 'article', 'section']):
        children = elem.find_all(recursive=False)
        if len(children) > 3:  # Likely a container
            # Check if contains price-like text
            text = elem.get_text()
            if '$' in text and any(str(i) in text for i in range(10)):
                patterns['containers'].append(_build_selector(elem))
    
    return patterns

if __name__ == "__main__":
    asyncio.run(discover_selectors())
```

### Method 3: Playwright Codegen

Use Playwright's built-in code generator:

```bash
# Install Playwright
pip install playwright
playwright install chromium

# Run codegen
playwright codegen https://www.phoenixmlssearch.com

# This opens a browser where you can:
# 1. Perform searches
# 2. Click on properties
# 3. Playwright records selectors used
```

## Selector Update Process

### 1. Create Selector Configuration File

Create `config/selectors/phoenix_mls.yaml`:

```yaml
# Phoenix MLS Selectors Configuration
# Last updated: [DATE]
# Website: https://www.phoenixmlssearch.com

search_page:
  search_input:
    primary: "#zipcode-search"  # Update with actual selector
    fallbacks:
      - "input[name='zipcode']"
      - "input[placeholder*='zip']"
      - ".search-input"
  
  submit_button:
    primary: "#search-submit"  # Update with actual selector
    fallbacks:
      - "button[type='submit']"
      - ".search-button"
      - "button:contains('Search')"

results_page:
  property_container:
    primary: ".property-listing"  # Update with actual selector
    fallbacks:
      - "article.listing"
      - "[data-listing-id]"
      - ".search-result-item"
  
  property_link:
    primary: "a.property-link"  # Update with actual selector
    fallbacks:
      - ".listing-title a"
      - "a[href*='/property/']"
  
  fields:
    address:
      primary: ".listing-address"  # Update with actual selector
      fallbacks:
        - ".property-location"
        - "[itemprop='address']"
    
    price:
      primary: ".listing-price"  # Update with actual selector
      fallbacks:
        - ".price-display"
        - "[data-price]"
    
    beds:
      primary: ".bed-count"  # Update with actual selector
      fallbacks:
        - "[data-beds]"
        - ".beds"
    
    baths:
      primary: ".bath-count"  # Update with actual selector
      fallbacks:
        - "[data-baths]"
        - ".baths"
    
    sqft:
      primary: ".sqft-display"  # Update with actual selector
      fallbacks:
        - "[data-sqft]"
        - ".square-feet"

detail_page:
  address:
    primary: "h1.property-address"  # Update with actual selector
    fallbacks:
      - ".detail-address"
      - "[itemprop='streetAddress']"
  
  price:
    primary: ".detail-price"  # Update with actual selector
    fallbacks:
      - ".asking-price"
      - "[data-price]"
  
  description:
    primary: ".property-description"  # Update with actual selector
    fallbacks:
      - ".listing-remarks"
      - "[itemprop='description']"
  
  images:
    primary: ".gallery-image img"  # Update with actual selector
    fallbacks:
      - ".photo-carousel img"
      - "[data-image-gallery] img"
```

### 2. Update Scraper to Use Configuration

Modify the scraper to load selectors from configuration:

```python
# In scraper.py
import yaml
from pathlib import Path

class PhoenixMLSScraper:
    def __init__(self, config, proxy_config):
        # ... existing init code ...
        
        # Load selectors
        selector_path = Path("config/selectors/phoenix_mls.yaml")
        with open(selector_path) as f:
            self.selectors = yaml.safe_load(f)
    
    async def _try_selector(self, selector_config, timeout=5000):
        """Try primary selector, fall back if needed."""
        primary = selector_config.get('primary')
        fallbacks = selector_config.get('fallbacks', [])
        
        # Try primary selector
        try:
            element = await self.page.wait_for_selector(
                primary, 
                timeout=timeout
            )
            if element:
                return element
        except:
            pass
        
        # Try fallbacks
        for fallback in fallbacks:
            try:
                element = await self.page.query_selector(fallback)
                if element:
                    logger.warning(
                        f"Primary selector '{primary}' failed, "
                        f"using fallback '{fallback}'"
                    )
                    return element
            except:
                continue
        
        raise Exception(
            f"No working selector found. "
            f"Tried: {primary}, {fallbacks}"
        )
```

### 3. Testing Selector Updates

Create a test script to validate selectors:

```python
# test_selectors.py
import asyncio
from phoenix_real_estate.collectors.phoenix_mls.scraper import PhoenixMLSScraper

async def test_selectors():
    config = {"base_url": "https://www.phoenixmlssearch.com"}
    scraper = PhoenixMLSScraper(config, {})
    
    try:
        await scraper.initialize_browser()
        
        # Test search page
        print("Testing search page selectors...")
        await scraper.page.goto(scraper.base_url)
        
        search_input = await scraper._try_selector(
            scraper.selectors['search_page']['search_input']
        )
        print("✓ Search input found")
        
        # Test with actual search
        results = await scraper.search_properties_by_zipcode("85001")
        print(f"✓ Found {len(results)} properties")
        
        # Test property detail
        if results:
            prop = await scraper.scrape_property_details(results[0]['url'])
            print("✓ Property details extracted")
        
    finally:
        await scraper.close_browser()

if __name__ == "__main__":
    asyncio.run(test_selectors())
```

## Troubleshooting Common Issues

### Dynamic Content Loading
- Use `wait_for_selector` with appropriate timeout
- Check for lazy-loaded content
- Monitor network requests for AJAX calls

### Shadow DOM Elements
- Some sites use Shadow DOM
- Requires special handling in Playwright
- Look for custom elements

### Anti-Scraping Measures
- Randomized class names
- Dynamic selector generation
- Honeypot elements

### Best Practices
1. Always use multiple fallback selectors
2. Prefer data attributes over classes
3. Use semantic HTML elements when possible
4. Test selectors regularly
5. Log selector performance metrics
6. Document any special cases

## Maintenance Schedule

1. **Weekly**: Run automated selector tests
2. **Monthly**: Manual inspection of key pages
3. **On Failure**: Immediate selector update
4. **Quarterly**: Full selector audit

## Emergency Selector Fix Process

1. **Detection**: Scraper fails with selector errors
2. **Diagnosis**: Run selector discovery script
3. **Update**: Modify selector configuration
4. **Test**: Validate with test script
5. **Deploy**: Update production configuration
6. **Monitor**: Watch for continued issues