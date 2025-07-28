# LLM Real Estate Data Processing Research Summary

## Executive Summary

This research document provides comprehensive recommendations for implementing LLM-based data processing in the Phoenix Real Estate project. Based on current best practices (2024), the document covers structured output generation, cost optimization strategies, prompt engineering templates, and data chunking approaches specifically tailored for real estate applications.

## 1. Best Practices for LLM Real Estate Data Processing

### 1.1 Core Implementation Principles

1. **Structured Output with JSON Schema**
   - Use Pydantic models for schema validation
   - Implement strict JSON output formatting for downstream processing
   - Leverage provider-specific structured output features (OpenAI, Anthropic, etc.)

2. **Domain-Specific Fine-Tuning**
   - Semantic parsing for contract language interpretation
   - Property attribute extraction with real estate ontology
   - Multi-task learning for various document types

3. **Retrieval-Augmented Generation (RAG)**
   - Implement vector database for context retrieval
   - Optimize for property-specific queries
   - Cache frequently accessed property data

### 1.2 Quality Assurance Framework

- **Validation Pipeline**: Schema validation → Content verification → Accuracy checks
- **Automated Evaluation**: Implement metrics for extraction accuracy
- **Error Handling**: Graceful degradation for hallucination detection

## 2. Structured Output Generation

### 2.1 Recommended JSON Schema for Property Data

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "property_id": {"type": "string"},
    "address": {
      "type": "object",
      "properties": {
        "street": {"type": "string"},
        "city": {"type": "string"},
        "state": {"type": "string"},
        "zip": {"type": "string"}
      },
      "required": ["street", "city", "state", "zip"]
    },
    "details": {
      "type": "object",
      "properties": {
        "bedrooms": {"type": "integer"},
        "bathrooms": {"type": "number"},
        "square_feet": {"type": "integer"},
        "lot_size": {"type": "number"},
        "year_built": {"type": "integer"},
        "property_type": {"type": "string", "enum": ["single_family", "condo", "townhouse", "multi_family"]}
      }
    },
    "financial": {
      "type": "object",
      "properties": {
        "list_price": {"type": "number"},
        "assessed_value": {"type": "number"},
        "tax_amount": {"type": "number"},
        "hoa_fee": {"type": "number", "nullable": true}
      }
    },
    "description": {
      "type": "object",
      "properties": {
        "summary": {"type": "string", "maxLength": 500},
        "features": {"type": "array", "items": {"type": "string"}},
        "upgrades": {"type": "array", "items": {"type": "string"}}
      }
    },
    "market_analysis": {
      "type": "object",
      "properties": {
        "comparable_sales": {"type": "array", "items": {"type": "object"}},
        "market_trend": {"type": "string", "enum": ["appreciating", "stable", "declining"]},
        "investment_score": {"type": "number", "minimum": 0, "maximum": 100}
      }
    }
  },
  "required": ["property_id", "address", "details", "financial"]
}
```

### 2.2 Implementation Approach

1. **Use Provider Structured Output APIs**
   - OpenAI: `response_format={"type": "json_schema", "json_schema": schema}`
   - Anthropic: Similar structured output features
   - Implement fallback parsing for non-structured responses

2. **Error Correction Pipeline**
   - Parse with generous error handling
   - Apply schema-aware corrections
   - Validate against business rules

## 3. Prompt Engineering Templates

### 3.1 Property Analysis Prompt

```python
PROPERTY_ANALYSIS_PROMPT = """
You are a real estate analysis expert. Analyze the following property data and extract structured information.

Property Data:
{property_raw_data}

Extract and structure the following information:
1. Basic property details (bedrooms, bathrooms, square footage)
2. Financial information (price, taxes, assessments)
3. Property features and upgrades
4. Market positioning and investment potential

Return the data in the following JSON format:
{json_schema}

Important:
- Use null for missing values, never omit fields
- Ensure all numeric values are properly typed
- Summarize descriptions to under 500 characters
- List features as an array of strings
"""
```

### 3.2 Comparative Market Analysis (CMA) Prompt

```python
CMA_PROMPT = """
Perform a comparative market analysis for the subject property using the provided comparable sales data.

Subject Property:
{subject_property}

Comparable Properties:
{comparable_properties}

Analyze:
1. Price per square foot comparison
2. Feature adjustments (bedrooms, bathrooms, upgrades)
3. Location and neighborhood factors
4. Market trend indicators

Provide a structured analysis with:
- Adjusted sale prices for comparables
- Recommended list price range
- Market positioning strategy
- Investment score (0-100)

Format output as JSON matching the provided schema.
"""
```

### 3.3 Property Description Generation

```python
DESCRIPTION_PROMPT = """
Create an engaging property description for online listings.

Property Details:
- Address: {address}
- Bedrooms: {bedrooms}, Bathrooms: {bathrooms}
- Square Feet: {square_feet}
- Key Features: {features}
- Recent Upgrades: {upgrades}

Generate:
1. Compelling headline (max 100 chars)
2. Overview paragraph highlighting best features
3. Detailed description of interior and exterior
4. Neighborhood benefits
5. Call-to-action

Style: Professional yet warm, emphasize lifestyle benefits, use sensory language.
"""
```

## 4. Cost-Effective Processing Strategies

### 4.1 Batch Processing Implementation

```python
# Use OpenAI Batch API for 50% cost savings
batch_config = {
    "model": "gpt-4o-mini",  # Cost-effective model
    "endpoint": "/v1/chat/completions",
    "method": "POST",
    "requests": [
        {
            "custom_id": f"property-{property_id}",
            "body": {
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_schema", "json_schema": schema}
            }
        }
        for property_id, prompt in property_prompts
    ]
}
# Process within 24 hours for 50% discount
```

### 4.2 Cost Optimization Strategies

1. **Model Selection**
   - Use GPT-4o-mini for basic extraction ($0.15/1M tokens)
   - Reserve GPT-4o for complex analysis ($5/1M tokens)
   - Consider Claude 3 Haiku for high-volume processing

2. **Caching Strategy**
   - Cache property templates and common patterns
   - Store processed comparable sales data
   - Implement 24-hour cache for market analysis

3. **Token Optimization**
   - Remove unnecessary whitespace and formatting
   - Use abbreviations in prompts where clarity permits
   - Batch similar properties together

### 4.3 Monthly Budget Allocation ($25 limit)

```
Suggested allocation:
- Property data extraction: $10 (≈66,000 properties with GPT-4o-mini batch)
- Market analysis: $8 (≈1,600 detailed analyses)
- Description generation: $5 (≈33,000 descriptions)
- Testing/development: $2
```

## 5. Data Chunking Strategies

### 5.1 Property Document Chunking

```python
class PropertyChunker:
    def __init__(self, chunk_size=2000, overlap=200):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_property_document(self, document):
        """Chunk property documents while preserving context"""
        chunks = []
        
        # Separate by logical sections
        sections = {
            "header": self._extract_header(document),
            "details": self._extract_property_details(document),
            "financial": self._extract_financial_info(document),
            "description": self._extract_description(document),
            "legal": self._extract_legal_info(document)
        }
        
        # Create semantic chunks
        for section_name, content in sections.items():
            if len(content) > self.chunk_size:
                # Split large sections with overlap
                section_chunks = self._split_with_overlap(content)
                for i, chunk in enumerate(section_chunks):
                    chunks.append({
                        "chunk_id": f"{section_name}_{i}",
                        "content": chunk,
                        "metadata": {
                            "section": section_name,
                            "chunk_index": i,
                            "total_chunks": len(section_chunks)
                        }
                    })
            else:
                chunks.append({
                    "chunk_id": section_name,
                    "content": content,
                    "metadata": {"section": section_name}
                })
        
        return chunks
```

### 5.2 Optimal Chunk Sizes

- **Property Listings**: 1,500-2,000 tokens (captures full listing)
- **Legal Documents**: 3,000-4,000 tokens (preserves clause context)
- **Market Reports**: 2,500-3,000 tokens (maintains analytical flow)
- **Image Descriptions**: 500-750 tokens (focused content)

### 5.3 Context Window Management

```python
def prepare_llm_context(property_data, max_tokens=8000):
    """Prepare context within token limits"""
    essential_fields = ["address", "price", "bedrooms", "bathrooms", "square_feet"]
    context = {
        "essential": extract_fields(property_data, essential_fields),
        "additional": {}
    }
    
    # Add additional context within token budget
    token_count = count_tokens(context["essential"])
    
    for field in ["description", "features", "comparables", "history"]:
        field_content = property_data.get(field, "")
        field_tokens = count_tokens(field_content)
        
        if token_count + field_tokens < max_tokens:
            context["additional"][field] = field_content
            token_count += field_tokens
        else:
            # Truncate or summarize to fit
            available_tokens = max_tokens - token_count - 100  # Buffer
            context["additional"][field] = truncate_to_tokens(field_content, available_tokens)
            break
    
    return context
```

## 6. Implementation Recommendations

### 6.1 Phase 1: Basic Extraction (Month 1)
1. Implement structured output for Maricopa API data
2. Create property JSON schemas
3. Set up batch processing pipeline
4. Budget: $5-8

### 6.2 Phase 2: Enhanced Analysis (Month 2)
1. Add comparative market analysis
2. Implement description generation
3. Integrate Phoenix MLS data processing
4. Budget: $10-15

### 6.3 Phase 3: Optimization (Month 3)
1. Fine-tune prompts based on results
2. Implement advanced caching
3. Add market trend analysis
4. Budget: $15-20

### 6.4 Tools and Libraries

```python
# Recommended stack
dependencies = {
    "openai": "^1.0.0",  # For GPT models
    "anthropic": "^0.2.0",  # For Claude models  
    "pydantic": "^2.0.0",  # For schema validation
    "tiktoken": "^0.5.0",  # For token counting
    "tenacity": "^8.0.0",  # For retry logic
    "redis": "^5.0.0",  # For caching
}
```

## 7. Error Handling and Validation

### 7.1 Common Issues and Solutions

1. **Hallucination Detection**
   ```python
   def validate_extraction(extracted_data, source_data):
       """Validate LLM extraction against source"""
       validations = {
           "address_match": fuzzy_match(extracted_data["address"], source_data["address"]) > 0.9,
           "price_reasonable": 10000 < extracted_data["price"] < 10000000,
           "rooms_valid": 0 < extracted_data["bedrooms"] < 20,
       }
       return all(validations.values()), validations
   ```

2. **Schema Validation**
   ```python
   from pydantic import BaseModel, validator
   
   class PropertyData(BaseModel):
       address: str
       price: float
       bedrooms: int
       
       @validator('price')
       def price_must_be_positive(cls, v):
           if v <= 0:
               raise ValueError('Price must be positive')
           return v
   ```

### 7.2 Monitoring and Logging

```python
import logging
from datetime import datetime

class LLMProcessingLogger:
    def __init__(self):
        self.logger = logging.getLogger("llm_processing")
        
    def log_extraction(self, property_id, success, tokens_used, cost):
        self.logger.info({
            "timestamp": datetime.utcnow().isoformat(),
            "property_id": property_id,
            "success": success,
            "tokens_used": tokens_used,
            "estimated_cost": cost,
            "model": "gpt-4o-mini"
        })
```

## 8. Conclusion

The Phoenix Real Estate project can effectively leverage LLMs for data processing within the $25/month budget by:

1. Using batch APIs for 50% cost savings
2. Implementing structured output with JSON schemas
3. Applying semantic chunking strategies
4. Starting with cost-effective models (GPT-4o-mini)
5. Caching frequently used data
6. Monitoring usage to optimize costs

This approach can process approximately 60,000+ property records per month while maintaining high quality and staying well within budget constraints.