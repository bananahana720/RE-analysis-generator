# ADR-002: Local LLM vs Cloud API for Data Processing

## Status
**ACCEPTED** - Implemented in Epic 2 Data Collection Engine

## Context
The Phoenix Real Estate Data Collection System requires intelligent data processing to extract structured information from unstructured sources, particularly for PhoenixMLSSearch.com web scraping. The system must:

- Process unstructured property descriptions into structured data
- Extract key property features (beds, baths, sqft, price, etc.)
- Handle varying data formats across different sources
- Operate within strict budget constraints ($1-25/month total)
- Maintain data privacy and avoid sending data to external services
- Support local development and testing environments

Two primary approaches were considered:

### Option 1: Cloud-Based LLM APIs
- Use services like OpenAI GPT-4, Anthropic Claude, or Google Gemini
- Pay-per-token pricing model
- High-quality, consistent output
- No local resource requirements
- Regular model updates and improvements

**Cost Analysis**:
- OpenAI GPT-4: ~$0.03-0.06 per 1K tokens
- Daily processing: ~200 properties × 1K tokens = 200K tokens
- Monthly cost: 200K × 30 × $0.03 / 1000 = $180/month
- **Exceeds budget by 720%-1800%**

### Option 2: Local LLM Processing
- Use Ollama with open-source models (Llama2:7b, Mistral, etc.)
- One-time setup, no ongoing API costs
- Complete data privacy - no external data transmission
- Offline operation capability
- Hardware resource requirements on local machine

**Cost Analysis**:
- Ollama: $0/month (open source)
- Model storage: ~4-8GB disk space
- Processing: Local CPU/GPU resources
- **Total monthly cost: $0**

## Decision
**We will implement Local LLM Processing using Ollama** with Llama2:7b as the primary model.

### Technical Implementation
```
Epic 2 Data Collection → Local LLM Client → Ollama Server → Llama2:7b Model
```

### Key Architecture Components
```python
class LLMProcessor:
    def __init__(self, model: str = "llama2:7b"):
        self.ollama_client = OllamaClient()
        self.model = model
    
    async def extract_property_features(self, raw_text: str) -> PropertyFeatures:
        prompt = self._build_extraction_prompt(raw_text)
        response = await self.ollama_client.generate(model=self.model, prompt=prompt)
        return self._parse_llm_response(response)
```

## Consequences

### Positive Consequences
1. **Budget Compliance**: $0/month cost enables entire system to stay within budget
2. **Data Privacy**: No external data transmission - all processing is local
3. **Offline Operation**: System works without internet connectivity
4. **Development Freedom**: No API rate limits or quotas to manage
5. **Consistency**: Same model version across all environments
6. **Integration**: Seamless integration with Epic 1's logging and error handling

### Negative Consequences
1. **Local Resources**: Requires ~8GB disk space and CPU/memory for processing
2. **Model Quality**: Open-source models may be less capable than GPT-4
3. **Maintenance**: Manual model updates and management required
4. **Processing Speed**: Local processing may be slower than cloud APIs
5. **Hardware Dependency**: Performance varies based on local hardware capabilities

### Impact on System Architecture

#### Epic 1 Foundation Integration
- LLM client uses Epic 1's ConfigProvider for model selection
- Logging framework captures LLM processing metrics and errors
- Error handling follows Epic 1's exception patterns

#### Epic 2 Collection Engine
- **Maricopa API**: Minimal LLM usage (structured data already available)
- **PhoenixMLS Scraper**: Heavy LLM usage for unstructured text processing
- **Fallback Strategy**: Rule-based extraction when LLM unavailable

#### Epic 3 Automation Integration
- Orchestration engine monitors LLM processing health
- Workflow commands include LLM model validation
- Reports include LLM processing success metrics

#### Epic 4 Quality Assurance
- Validate LLM output quality and consistency
- Monitor processing times and resource usage
- Test fallback mechanisms when LLM unavailable

### Performance Characteristics
- **Processing Speed**: 2-5 seconds per property (acceptable for daily batch processing)
- **Accuracy**: 85-90% extraction accuracy (sufficient for real estate data)
- **Resource Usage**: ~2GB RAM during processing, negligible when idle
- **Throughput**: 200-500 properties per hour (meets daily collection needs)

### Alternative Considered: Cloud APIs
Cloud-based LLM APIs were rejected primarily due to:
- **Budget Constraints**: Would consume 720%-1800% of total budget
- **Data Privacy**: Sending property data to external services
- **Rate Limits**: API quotas could interrupt collection workflows
- **Dependency**: External service availability and reliability concerns

## Risk Mitigation

### Model Quality Risks
- **Strategy**: Implement comprehensive output validation
- **Fallback**: Rule-based extraction for critical fields
- **Monitoring**: Track extraction accuracy and flag anomalies
- **Improvement**: Consider upgrading to larger models (Llama2:13b) if needed

### Performance Risks
- **Strategy**: Batch processing during off-peak hours
- **Optimization**: Cache common extraction patterns
- **Scaling**: Consider GPU acceleration for increased throughput
- **Monitoring**: Track processing times and resource usage

### Reliability Risks
- **Strategy**: Health checks for Ollama service availability
- **Fallback**: Graceful degradation to rule-based extraction
- **Recovery**: Automatic retry mechanisms for transient failures
- **Testing**: Comprehensive testing of all failure scenarios

## Implementation Guidelines

### Model Selection Criteria
1. **Primary**: Llama2:7b (4GB, good balance of size and capability)
2. **Alternative**: Mistral-7B (if Llama2 performance insufficient)
3. **Upgrade Path**: Llama2:13b (8GB, higher quality but more resources)

### Integration Requirements
- Use Epic 1's ConfigProvider for model configuration
- Implement comprehensive logging of LLM operations
- Follow Epic 1's error handling patterns
- Support Epic 3's orchestration monitoring

### Quality Standards
- Validate LLM output against expected property schema
- Implement confidence scoring for extraction results
- Provide human-readable error messages for failed extractions
- Track and report extraction accuracy metrics

### Performance Optimization
- Batch multiple properties in single LLM calls where possible
- Cache frequent extraction patterns
- Implement request queuing to prevent resource overwhelm
- Monitor and alert on processing performance degradation

## Validation Criteria
- [ ] Ollama successfully installed and configured in development environment
- [ ] Llama2:7b model downloads and initializes correctly
- [ ] Property extraction achieves >85% accuracy on test dataset
- [ ] Processing performance meets throughput requirements (200+ properties/hour)
- [ ] Integration with Epic 1 foundation components working correctly
- [ ] Fallback mechanisms handle LLM unavailability gracefully
- [ ] Resource usage stays within acceptable bounds during operation
- [ ] Quality monitoring successfully tracks extraction accuracy

## Configuration Management
```yaml
# Epic 1 Configuration Integration
LLM_MODEL: "llama2:7b"
LLM_TEMPERATURE: 0.1
LLM_MAX_TOKENS: 1000
LLM_TIMEOUT_SECONDS: 30
LLM_FALLBACK_ENABLED: true
OLLAMA_HOST: "localhost"
OLLAMA_PORT: 11434
```

## Future Considerations
- **Model Upgrades**: Evaluate newer open-source models as they become available
- **GPU Acceleration**: Consider GPU support for improved processing speed
- **Distributed Processing**: Scale to multiple Ollama instances if needed
- **Model Fine-tuning**: Train custom models on real estate data for improved accuracy

## References
- Epic 2: Data Collection Engine LLM integration specification
- Ollama documentation and model compatibility
- Phoenix Real Estate budget constraints and requirements
- Local development environment setup guidelines

---
**Author**: Integration Architect  
**Date**: 2025-01-20  
**Review**: Architecture Review Board, Budget Committee  
**Next Review**: After Epic 2 implementation and accuracy validation