"""Test module imports for LLM processing components."""



def test_module_imports():
    """Test all LLM processing modules can be imported."""
    # These will fail initially (Red phase)
    from phoenix_real_estate.collectors.processing import OllamaClient
    from phoenix_real_estate.collectors.processing import PropertyDataExtractor
    from phoenix_real_estate.collectors.processing import ProcessingValidator
    from phoenix_real_estate.collectors.processing import DataProcessingPipeline
    
    assert OllamaClient is not None
    assert PropertyDataExtractor is not None
    assert ProcessingValidator is not None
    assert DataProcessingPipeline is not None


def test_module_version():
    """Test module has version info."""
    from phoenix_real_estate.collectors import processing
    
    assert hasattr(processing, "__version__")
    assert processing.__version__ == "0.1.0"