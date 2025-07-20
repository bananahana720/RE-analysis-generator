#!/usr/bin/env python
"""Project Structure Validation Script."""

from pathlib import Path

def validate_structure():
    """Validate project structure."""
    project_root = Path(__file__).parent.parent
    
    print("Phoenix Real Estate Project Validation")
    print("=" * 40)
    
    # Check directories
    dirs = [
        "src/phoenix_real_estate/foundation",
        "tests/foundation",
        "scripts",
        "PRPs/architecture"
    ]
    
    for d in dirs:
        path = project_root / d
        if path.exists():
            print(f"[OK] {d}")
        else:
            print(f"[MISSING] {d} MISSING")
    
    # Check key files
    files = [
        "pyproject.toml",
        "README.md",
        ".gitignore",
        "Makefile"
    ]
    
    print("\nKey Files:")
    for f in files:
        path = project_root / f
        if path.exists():
            print(f"[OK] {f}")
        else:
            print(f"[MISSING] {f} MISSING")
    
    print("\nValidation complete!")

if __name__ == "__main__":
    validate_structure()
