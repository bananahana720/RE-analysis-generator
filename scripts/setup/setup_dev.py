# \\!/usr/bin/env python3
"""Development Environment Setup Script for Phoenix Real Estate Project."""

import subprocess
import sys
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    BOLD = "\033[1m"
    CYAN = "[96m"
    ENDC = "\033[0m"


def print_header(title: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{title}{Colors.ENDC}")
    print(f"{Colors.BLUE}{'=' * len(title)}{Colors.ENDC}")


def print_status(success: bool, message: str) -> None:
    """Print status with color coding."""
    if success:
        print(f"{Colors.GREEN}[SUCCESS]{Colors.ENDC}: {message}")
    else:
        print(f"{Colors.RED}[FAILED]{Colors.ENDC}: {message}")


def run_command(cmd: str) -> bool:
    """Run command and return success status."""
    try:
        result = subprocess.run(cmd.split(), capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def print_info(message: str) -> None:
    """Print informational message."""
    print(f"{Colors.CYAN}[INFO]{Colors.ENDC}: {message}")


def run_uv_sync() -> bool:
    """Run uv sync commands."""
    Path(__file__).parent.parent
    commands = ["uv sync", "uv sync --extra dev"]

    for cmd in commands:
        print_info(f"Running: {cmd}")
        success = run_command(cmd)
        if success:
            print_status(True, f"Command: {cmd}")
        else:
            print_status(False, f"Command: {cmd}")
            return False
    return True


def validate_directories() -> bool:
    """Validate required directory structure."""
    project_root = Path(__file__).parent.parent

    required_dirs = [
        "src/phoenix_real_estate/foundation",
        "src/phoenix_real_estate/foundation/config",
        "src/phoenix_real_estate/foundation/database",
        "src/phoenix_real_estate/foundation/logging",
        "src/phoenix_real_estate/foundation/utils",
        "src/phoenix_real_estate/collectors",
        "src/phoenix_real_estate/processors",
        "src/phoenix_real_estate/api",
        "src/phoenix_real_estate/orchestration",
        "tests/foundation",
        "tests/integration",
        "scripts",
        "config",
        "docs",
        "PRPs/architecture",
        "PRPs/tasks",
        "PRPs/epics",
    ]

    all_exist = True
    for dir_path in required_dirs:
        path = project_root / dir_path
        exists = path.exists() and path.is_dir()
        print_status(exists, f"Directory: {dir_path}")
        if not exists:
            all_exist = False

    return all_exist


def validate_files() -> bool:
    """Validate required files exist."""
    project_root = Path(__file__).parent.parent

    required_files = [
        "pyproject.toml",
        "README.md",
        "Makefile",
        ".gitignore",
        "src/phoenix_real_estate/__init__.py",
        "src/phoenix_real_estate/foundation/__init__.py",
        "src/phoenix_real_estate/foundation/interfaces.py",
        "src/phoenix_real_estate/foundation/utils/exceptions.py",
        "src/phoenix_real_estate/foundation/utils/helpers.py",
        "tests/conftest.py",
    ]

    all_exist = True
    for file_path in required_files:
        path = project_root / file_path
        exists = path.exists() and path.is_file()
        print_status(exists, f"File: {file_path}")
        if not exists:
            all_exist = False

    return all_exist


def validate_package_imports() -> bool:
    """Validate that package imports work correctly."""
    import_tests = [
        ("phoenix_real_estate", lambda: __import__("phoenix_real_estate")),
        ("phoenix_real_estate.foundation", lambda: __import__("phoenix_real_estate.foundation")),
        ("foundation interfaces", lambda: __import__("phoenix_real_estate.foundation.interfaces")),
        (
            "foundation exceptions",
            lambda: __import__("phoenix_real_estate.foundation.utils.exceptions"),
        ),
        ("foundation helpers", lambda: __import__("phoenix_real_estate.foundation.utils.helpers")),
    ]

    all_passed = True
    for name, import_func in import_tests:
        try:
            import_func()
            print_status(True, f"Import: {name}")
        except Exception as e:
            print_status(False, f"Import: {name} - {e}")
            all_passed = False

    return all_passed


def validate_development_tools() -> bool:
    """Validate development tools are available."""
    tool_tests = [
        ("UV package manager", "uv --version"),
        ("Ruff linter/formatter", "uv run ruff --version"),
        ("MyPy type checker", "uv run mypy --version"),
        ("Pytest test runner", "uv run pytest --version"),
    ]

    all_available = True
    for tool_name, command in tool_tests:
        available = run_command(command)
        print_status(available, f"Tool: {tool_name}")
        if not available:
            all_available = False

    return all_available


def validate_functionality() -> bool:
    """Run basic functionality tests."""
    functionality_tests = [
        ("Syntax check", "uv run python -m py_compile src/phoenix_real_estate/__init__.py"),
        (
            "Package structure",
            'uv run python -c "import phoenix_real_estate; print(phoenix_real_estate.__version__)"',
        ),
        (
            "Foundation layer",
            "uv run python -c \"from phoenix_real_estate.foundation import get_logger; print('OK')\"",
        ),
    ]

    all_passed = True
    for test_name, command in functionality_tests:
        passed = run_command(command)
        print_status(passed, f"Functionality: {test_name}")
        if not passed:
            all_passed = False

    return all_passed


def main() -> int:
    """Main validation function."""
    print(f"{Colors.BOLD}{Colors.PURPLE}Phoenix Real Estate Development Setup{Colors.ENDC}")
    print(f"{Colors.PURPLE}{'=' * 40}{Colors.ENDC}")

    setup_sections = [
        ("UV Environment Setup", run_uv_sync),
        ("Directory Structure", validate_directories),
        ("Required Files", validate_files),
        ("Package Imports", validate_package_imports),
        ("Development Tools", validate_development_tools),
        ("Basic Functionality", validate_functionality),
    ]

    overall_success = True
    results = []

    for section_name, validation_func in setup_sections:
        print_header(section_name)
        try:
            success = validation_func()
            results.append((section_name, success))
            if not success:
                overall_success = False
        except Exception as e:
            print_status(False, f"Section failed with error: {e}")
            results.append((section_name, False))
            overall_success = False

    # Summary
    print_header("Validation Summary")
    for section_name, success in results:
        print_status(success, section_name)

    if overall_success:
        print(
            f"\n{Colors.GREEN}{Colors.BOLD}Development environment setup completed successfully\!{Colors.ENDC}"
        )
        return 0
    else:
        print(
            f"\n{Colors.RED}{Colors.BOLD}Some validations failed. Please fix the issues above.{Colors.ENDC}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
