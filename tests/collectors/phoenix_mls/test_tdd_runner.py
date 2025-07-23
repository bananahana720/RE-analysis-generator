"""TDD Runner and verification for Phoenix MLS Scraper.

This module ensures TDD compliance and tracks Red-Green-Refactor cycles.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime


class TDDTracker:
    """Track TDD cycles and ensure compliance."""

    def __init__(self):
        self.cycle_file = Path(".claude/tdd-guard/data/cycles.json")
        self.cycle_file.parent.mkdir(parents=True, exist_ok=True)
        self.current_cycle = {"component": None, "phase": "RED", "start_time": None, "tests": []}

    def start_red_phase(self, component: str, test_name: str):
        """Start a new RED phase for TDD cycle."""
        self.current_cycle = {
            "component": component,
            "phase": "RED",
            "start_time": datetime.now().isoformat(),
            "test_name": test_name,
            "tests": [],
        }
        self._save_cycle()

    def transition_to_green(self):
        """Transition from RED to GREEN phase."""
        if self.current_cycle["phase"] != "RED":
            raise ValueError("Can only transition to GREEN from RED phase")
        self.current_cycle["phase"] = "GREEN"
        self.current_cycle["green_time"] = datetime.now().isoformat()
        self._save_cycle()

    def transition_to_refactor(self):
        """Transition from GREEN to REFACTOR phase."""
        if self.current_cycle["phase"] != "GREEN":
            raise ValueError("Can only transition to REFACTOR from GREEN phase")
        self.current_cycle["phase"] = "REFACTOR"
        self.current_cycle["refactor_time"] = datetime.now().isoformat()
        self._save_cycle()

    def complete_cycle(self):
        """Complete the current TDD cycle."""
        self.current_cycle["phase"] = "COMPLETED"
        self.current_cycle["end_time"] = datetime.now().isoformat()
        self._save_cycle()

    def _save_cycle(self):
        """Save current cycle to file."""
        cycles = []
        if self.cycle_file.exists():
            cycles = json.loads(self.cycle_file.read_text())

        # Update or append current cycle
        cycle_exists = False
        for i, cycle in enumerate(cycles):
            if cycle.get("component") == self.current_cycle["component"] and cycle.get(
                "test_name"
            ) == self.current_cycle.get("test_name"):
                cycles[i] = self.current_cycle
                cycle_exists = True
                break

        if not cycle_exists:
            cycles.append(self.current_cycle)

        self.cycle_file.write_text(json.dumps(cycles, indent=2))


# Global TDD tracker instance
tdd_tracker = TDDTracker()


def test_tdd_compliance():
    """Verify TDD compliance for the project."""
    cycle_file = Path(".claude/tdd-guard/data/cycles.json")

    if not cycle_file.exists():
        pytest.skip("No TDD cycles recorded yet")

    cycles = json.loads(cycle_file.read_text())

    # Check that all cycles follow RED-GREEN-REFACTOR
    for cycle in cycles:
        if cycle.get("phase") == "COMPLETED":
            assert "red_time" in cycle or "start_time" in cycle, f"Cycle missing RED phase: {cycle}"
            assert "green_time" in cycle, f"Cycle missing GREEN phase: {cycle}"
            assert "refactor_time" in cycle, f"Cycle missing REFACTOR phase: {cycle}"


def test_mutation_score_threshold():
    """Verify mutation testing score meets threshold."""
    # This will be implemented after we have actual code to mutate
    pytest.skip("Mutation testing will be enabled after implementation")


@pytest.fixture(scope="session")
def tdd_compliance_report():
    """Generate TDD compliance report at end of test session."""
    yield

    # Generate report after all tests
    cycle_file = Path(".claude/tdd-guard/data/cycles.json")
    if cycle_file.exists():
        cycles = json.loads(cycle_file.read_text())

        print("\n" + "=" * 60)
        print("TDD COMPLIANCE REPORT")
        print("=" * 60)

        components = {}
        for cycle in cycles:
            comp = cycle.get("component", "Unknown")
            if comp not in components:
                components[comp] = {"total": 0, "completed": 0}
            components[comp]["total"] += 1
            if cycle.get("phase") == "COMPLETED":
                components[comp]["completed"] += 1

        for comp, stats in components.items():
            completion_rate = (stats["completed"] / stats["total"]) * 100
            print(
                f"{comp}: {stats['completed']}/{stats['total']} cycles completed ({completion_rate:.1f}%)"
            )

        print("=" * 60)
