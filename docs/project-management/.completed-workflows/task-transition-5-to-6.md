# Task Transition: From Collection (Task 5) to Processing (Task 6)
*Date: January 23, 2025*

## Current State Summary

### Completed Infrastructure (Tasks 1-5) ✅
- **MongoDB**: v8.1.2 running with all collections created
- **Maricopa API**: Configured with 84% success rate
- **Phoenix MLS Scraper**: Fully implemented with anti-detection
- **WebShare Proxy**: 10 working proxies verified
- **2captcha**: $10 balance loaded for CAPTCHA solving

### Data Flow Status
```
[Maricopa API] ─┐
                 ├─→ [MongoDB: raw_properties] → [Processing Queue] → [Task 6: LLM Processing]
[Phoenix MLS]  ─┘
```

## Data Available for Processing

### Sample Raw Property (Maricopa)
```json
{
    "_id": "maricopa_502234567",
    "source": "maricopa_api",
    "collected_at": "2025-01-23T10:00:00Z",
    "data": {
        "parcel_number": "502-23-456-7",
        "address": "1234 E WASHINGTON ST PHOENIX AZ 85034",
        "sale_date": "2023-11-15",
        "sale_price": 385000,
        "assessed_value": 342000,
        "property_type": "SINGLE FAMILY",
        "bedrooms": 3,
        "bathrooms": 2,
        "living_area": 1654,
        "lot_size": 7841,
        "year_built": 1998,
        "pool": false,
        "garage_spaces": 2
    },
    "status": "pending_processing"
}
```

### Sample Raw Property (Phoenix MLS)
```json
{
    "_id": "phoenix_mls_5487239",
    "source": "phoenix_mls",
    "collected_at": "2025-01-23T14:30:00Z",
    "data": {
        "mls_number": "5487239",
        "address": "4567 N 45TH AVE, PHOENIX, AZ 85031",
        "list_price": 425000,
        "property_type": "Single Family - Detached",
        "bedrooms": 4,
        "bathrooms": 2.5,
        "square_feet": 2100,
        "lot_sqft": 8500,
        "year_built": 2005,
        "days_on_market": 12,
        "listing_description": "Beautiful home in established neighborhood...",
        "features": [
            "Granite Countertops",
            "Stainless Appliances",
            "Pool/Spa"
        ],
        "raw_html": "<div class='property-details'>...</div>"
    },
    "status": "pending_processing"
}
```

## Task 6 Integration Requirements

### 1. Data Normalization Needs
- **Address Standardization**: Convert various formats to consistent structure
- **Property Type Mapping**: Harmonize "SINGLE FAMILY" vs "Single Family - Detached"
- **Missing Data Handling**: Phoenix MLS has features Maricopa lacks (and vice versa)
- **Price Reconciliation**: Sale price vs list price vs assessed value

### 2. LLM Processing Opportunities
- **Description Generation**: Create compelling descriptions for Maricopa properties (no description)
- **Feature Enhancement**: Extract implicit features from raw data
- **Investment Analysis**: Calculate ROI, rental estimates, market positioning
- **Quality Assessment**: Score property attractiveness and value

### 3. Database Schema Updates
```python
# New collection: processed_properties
{
    "_id": "processed_502234567",
    "raw_property_id": "maricopa_502234567",
    "processed_date": "2025-01-23T20:00:00Z",
    "normalized_data": {
        # Standardized fields
    },
    "llm_enrichment": {
        "description": "...",
        "key_features": [...],
        "investment_analysis": {...}
    },
    "quality_score": 0.85,
    "ready_for_api": true
}
```

## Implementation Bridge

### Step 1: Create Processing Queue Manager
```python
class ProcessingQueueManager:
    """Manages the flow from raw to processed properties."""
    
    async def get_next_batch(self, size: int = 50) -> List[dict]:
        """Get next batch of unprocessed properties."""
        return await self.db.raw_properties.find(
            {"status": "pending_processing"},
            limit=size
        ).to_list()
    
    async def mark_processed(self, property_id: str, processed_id: str):
        """Update raw property as processed."""
        await self.db.raw_properties.update_one(
            {"_id": property_id},
            {
                "$set": {
                    "status": "processed",
                    "processed_id": processed_id,
                    "processed_at": datetime.utcnow()
                }
            }
        )
```

### Step 2: Connect to Existing Infrastructure
```python
# Reuse existing database connection
from phoenix_real_estate.foundation.database import DatabaseManager

# Reuse configuration system
from phoenix_real_estate.foundation.config import ConfigProvider

# Reuse logging
from phoenix_real_estate.utils.logging import get_logger
```

### Step 3: Implement Data Flow
```python
async def process_properties():
    """Main processing loop."""
    db = DatabaseManager()
    processor = LLMProcessor()
    queue = ProcessingQueueManager(db)
    
    while True:
        # Get batch
        batch = await queue.get_next_batch(50)
        if not batch:
            await asyncio.sleep(300)  # Wait 5 minutes
            continue
        
        # Process each property
        for raw_property in batch:
            try:
                # Normalize
                normalized = normalizer.normalize(raw_property)
                
                # Enrich with LLM
                enriched = await processor.process(normalized)
                
                # Save
                processed_id = await db.save_processed(enriched)
                
                # Update queue
                await queue.mark_processed(raw_property['_id'], processed_id)
                
            except Exception as e:
                logger.error(f"Failed to process {raw_property['_id']}: {e}")
```

## Testing Integration

### End-to-End Test
```python
async def test_full_pipeline():
    """Test from raw collection to processed output."""
    
    # 1. Collect a property (using existing collectors)
    maricopa = MaricopaAPIClient()
    raw_data = await maricopa.get_property("502-23-456-7")
    
    # 2. Save to raw collection
    raw_id = await db.save_raw_property(raw_data)
    
    # 3. Process with LLM
    processor = BatchProcessor()
    await processor.process_batch(1)
    
    # 4. Verify processed output
    processed = await db.get_processed_by_raw_id(raw_id)
    assert processed is not None
    assert processed['quality_score'] >= 0.7
    assert 'description' in processed['llm_enrichment']
```

## Migration Checklist

### Before Starting Task 6
- [x] Verify MongoDB is running and accessible
- [x] Confirm raw_properties collection has data
- [x] Test database connections work
- [x] Ensure configuration system is operational
- [ ] Set up LLM API credentials (OpenAI/Anthropic)
- [ ] Create processed_properties collection
- [ ] Design prompt templates
- [ ] Set up cost tracking

### Task 6 Dependencies
- **From Task 2**: Database schemas and connections
- **From Task 3**: Configuration management system
- **From Task 4**: Property data models
- **From Task 5**: Raw property data format

### Backwards Compatibility
- Task 6 must not modify raw_properties schema
- Processing should be idempotent (re-runnable)
- Failed processing should not block collection
- API (Task 7) will read from processed_properties

## Success Metrics

### Technical Transition
- [ ] Raw properties flow to processing queue
- [ ] Processed properties saved correctly
- [ ] Error handling preserves data integrity
- [ ] Performance meets targets (<5s per property)

### Data Quality
- [ ] 90%+ properties successfully processed
- [ ] Average quality score >0.8
- [ ] No data loss during processing
- [ ] Consistent output format

### System Integration
- [ ] Works with existing database
- [ ] Uses established configuration
- [ ] Follows project patterns
- [ ] Maintains test coverage

## Risk Mitigation

### Potential Issues
1. **LLM API Failures**: Implement retry with exponential backoff
2. **Cost Overruns**: Daily budget limits and monitoring
3. **Data Quality**: Validation and manual review queue
4. **Performance**: Batch processing and caching

### Rollback Plan
- Processing is additive (doesn't modify raw data)
- Can pause processing without affecting collection
- Processed data can be regenerated if needed
- Each property processed independently

---
*This document bridges the completed collection infrastructure (Tasks 1-5) with the upcoming LLM processing implementation (Task 6)*