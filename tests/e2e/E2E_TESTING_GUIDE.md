# E2E Testing Guide for LLM Processing Pipeline

## Overview

This guide describes the end-to-end testing approach for the Phoenix Real Estate LLM processing pipeline (Task 6). The tests validate the complete data flow from raw HTML/JSON input through LLM extraction, validation, and database storage.

## Test Modes

### 1. Mock Mode (Default)
- Uses mocked Ollama client for fast, deterministic tests
- No external dependencies required
- Ideal for CI/CD pipelines
- Run time: ~5-10 seconds for full suite

```bash
# Run in mock mode (default)
pytest tests/e2e/test_processing_pipeline_e2e.py -v
```

### 2. Real Mode
- Uses actual Ollama service with llama3.2:latest model
- Requires Ollama running locally
- Validates real LLM integration
- Run time: ~30-60 seconds for full suite

```bash
# Run in real mode
E2E_MODE=real pytest tests/e2e/test_processing_pipeline_e2e.py -v
```

## Test Structure

### 1. Pipeline Tests (`TestProcessingPipelineE2E`)
- Single property processing (HTML/JSON)
- Batch processing with concurrency control
- Mixed content type processing
- Error handling and recovery
- Performance benchmarks
- Metrics tracking

### 2. Integration Tests (`TestProcessingIntegratorE2E`)
- Complete flow from collection to storage
- Database persistence validation
- Multi-source data processing
- Error recovery in production scenarios

### 3. Workflow Tests
- Full end-to-end production simulation
- Multiple data sources
- Database queries and searches
- Performance metrics collection

## Test Data

### Sample Properties
Located in `tests/e2e/fixtures/property_samples.py`:
- Phoenix MLS HTML samples (3 properties)
- Maricopa County JSON samples (3 properties)
- Edge cases (5 scenarios)
- Invalid data samples (4 scenarios)

### Test Data Factory
Dynamic test data generation for:
- Custom property attributes
- Batch testing scenarios
- Performance benchmarks
- Edge case validation

## Configuration

### Environment Variables
```bash
# E2E test mode
E2E_MODE=mock|real

# Ollama configuration (for real mode)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest

# Test database
MONGODB_DATABASE=phoenix_real_estate_e2e_test

# Processing configuration
PROCESSING_TIMEOUT=60
BATCH_SIZE=5
MAX_CONCURRENT_PROCESSING=3
STRICT_VALIDATION=true
```

### Test Markers
- `@pytest.mark.e2e` - E2E tests
- `@pytest.mark.slow` - Tests taking >5 seconds
- `@pytest.mark.asyncio` - Async tests
- `@pytest.mark.parametrize` - Parameterized tests

## Running Tests

### Full E2E Suite
```bash
# Mock mode (fast)
pytest tests/e2e/ -v -m e2e

# Real mode (comprehensive)
E2E_MODE=real pytest tests/e2e/ -v -m e2e

# With performance benchmarks
pytest tests/e2e/ -v -m "e2e and slow"
```

### Specific Test Categories
```bash
# Pipeline tests only
pytest tests/e2e/test_processing_pipeline_e2e.py::TestProcessingPipelineE2E -v

# Integration tests only
pytest tests/e2e/test_processing_pipeline_e2e.py::TestProcessingIntegratorE2E -v

# Workflow test
pytest tests/e2e/test_processing_pipeline_e2e.py::test_complete_e2e_workflow -v
```

### Performance Testing
```bash
# Run performance benchmarks
pytest tests/e2e/ -v -k "performance" --tb=short

# With detailed output
pytest tests/e2e/ -v -k "performance" -s
```

## Validation Points

### 1. Data Extraction
- Correct field extraction from HTML/JSON
- Handling of missing/optional fields
- Special character and encoding support
- Edge case handling

### 2. Validation
- Required field presence
- Data type correctness
- Value range validation
- Confidence score thresholds

### 3. Database Storage
- Successful persistence
- Data integrity
- Search functionality
- Update handling

### 4. Performance
- Processing time < 2s per property (mock)
- Batch processing efficiency
- Concurrent processing limits
- Memory usage constraints

## Troubleshooting

### Common Issues

1. **Ollama not running (real mode)**
   ```bash
   # Start Ollama
   ollama serve
   
   # Verify model
   ollama pull llama3.2:latest
   ```

2. **MongoDB connection errors**
   ```bash
   # Start MongoDB (Windows, as admin)
   net start MongoDB
   
   # Verify connection
   mongosh --eval "db.version()"
   ```

3. **Test timeouts**
   - Increase `PROCESSING_TIMEOUT` environment variable
   - Check Ollama service health
   - Verify network connectivity

4. **Low success rates**
   - Check LLM model is loaded
   - Verify extraction prompts
   - Review validation thresholds

## Performance Metrics

The test suite tracks and reports:
- Total operations and success rate
- Average processing time per property
- Min/max processing durations
- Concurrent processing efficiency
- Database operation performance

Performance summary is printed after test completion.

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run E2E Tests (Mock)
  run: |
    pytest tests/e2e/ -v -m e2e --junit-xml=e2e-results.xml
  
- name: Run E2E Tests (Real)
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  run: |
    docker run -d -p 11434:11434 ollama/ollama
    sleep 10
    docker exec ollama ollama pull llama3.2:latest
    E2E_MODE=real pytest tests/e2e/ -v -m e2e
```

## Best Practices

1. **Always run mock tests first** - Quick validation before real tests
2. **Use test data factory** - Consistent, reproducible test data
3. **Check performance metrics** - Monitor for regressions
4. **Test error scenarios** - Ensure graceful failure handling
5. **Validate database state** - Confirm data persistence
6. **Review test logs** - Check for warnings or issues

## Future Enhancements

1. **Visual regression testing** - Screenshot comparison for UI
2. **Load testing** - High-volume property processing
3. **Multi-model testing** - Different LLM models
4. **Cross-platform testing** - Windows/Linux/Mac
5. **API contract testing** - Validate collector interfaces