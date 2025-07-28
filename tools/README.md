# Tools Directory

Utility tools and validation scripts for the Phoenix Real Estate Data Collection system.

## Structure

### `/validation/`
- **validate_environment.py** - Comprehensive environment validation
- **run_benchmarks.py** - Performance benchmarking tools

### `/setup/`
*Note: Setup scripts are organized in the main `/scripts/` directory*

## Usage

These tools are designed for:
- System validation and health checks
- Performance testing and benchmarking
- Environment setup verification
- Development workflow automation

## Running Tools

```bash
# Environment validation
uv run tools/validation/validate_environment.py

# Performance benchmarks
uv run tools/validation/run_benchmarks.py
```

Most tools can be run directly and will generate reports in the `/reports/` directory.