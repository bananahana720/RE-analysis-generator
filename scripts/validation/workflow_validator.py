"""GitHub Actions workflow validator.

Validates YAML syntax, secrets, dependencies, and action versions.
"""

import yaml
import re
from typing import Dict, Any, List, Set, Optional

from phoenix_real_estate.foundation import ConfigProvider, get_logger
from phoenix_real_estate.foundation.utils.exceptions import ValidationError


class WorkflowValidator:
    """GitHub Actions workflow validator."""

    def __init__(self, config_provider: Optional[ConfigProvider] = None):
        """Initialize workflow validator."""
        self.config = config_provider or ConfigProvider()
        self.logger = get_logger(__name__)
        self.validation_errors = []
        self.required_secrets = []

    def validate_yaml_syntax(self, workflow_content: str) -> Dict[str, Any]:
        """Validate YAML syntax and structure."""
        try:
            workflow_data = yaml.safe_load(workflow_content)
            if not isinstance(workflow_data, dict):
                raise ValidationError("Workflow must be a YAML object")

            # Validate required top-level fields
            if "name" not in workflow_data:
                raise ValidationError("Missing required field: name")
            if "jobs" not in workflow_data:
                raise ValidationError("Missing required field: jobs")

            # Check for 'on' field (YAML converts 'on:' to boolean True)
            if "on" not in workflow_data and True not in workflow_data:
                raise ValidationError("Missing required field: on")

            self.logger.info("YAML syntax validation passed")
            return {"status": "valid", "data": workflow_data}

        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML syntax: {e}"
            self.validation_errors.append(error_msg)
            raise ValidationError(error_msg)

    def validate_required_secrets(
        self, workflow_data: Dict[str, Any], available_secrets: List[str]
    ) -> List[str]:
        """Validate required secrets are available."""
        missing_secrets = []

        # Extract secrets from workflow
        secrets_used = self._extract_secrets_from_workflow(workflow_data)
        self.required_secrets = list(secrets_used)

        # Check if all required secrets are available
        for secret in secrets_used:
            if secret not in available_secrets:
                missing_secrets.append(secret)

        if missing_secrets:
            error_msg = f"Missing required secrets: {missing_secrets}"
            self.validation_errors.append(error_msg)
            self.logger.error(error_msg)
        else:
            self.logger.info(f"All {len(secrets_used)} required secrets are available")

        return missing_secrets

    def validate_job_dependencies(self, workflow_data: Dict[str, Any]) -> List[str]:
        """Validate job dependency chains."""
        errors = []
        jobs = workflow_data.get("jobs", {})

        # Build dependency graph
        dependencies = {}
        for job_name, job_config in jobs.items():
            needs = job_config.get("needs", [])
            if isinstance(needs, str):
                needs = [needs]
            dependencies[job_name] = needs

        # Check for circular dependencies
        circular_deps = self._find_circular_dependencies(dependencies)
        if circular_deps:
            error_msg = f"Circular dependencies detected: {circular_deps}"
            errors.append(error_msg)
            self.validation_errors.append(error_msg)

        if not errors:
            self.logger.info("Job dependency validation passed")

        return errors

    def validate_action_versions(self, workflow_data: Dict[str, Any]) -> List[str]:
        """Validate GitHub Actions versions are compatible."""
        warnings = []
        deprecated_actions = {
            "actions/checkout@v2": "actions/checkout@v4",
            "actions/setup-python@v1": "actions/setup-python@v4",
        }

        # Extract all actions from workflow
        actions_used = self._extract_actions_from_workflow(workflow_data)

        for action in actions_used:
            if action in deprecated_actions:
                warning_msg = f"Deprecated action: {action}"
                warnings.append(warning_msg)
                self.logger.warning(warning_msg)

        return warnings

    def _extract_secrets_from_workflow(self, workflow_data: Dict[str, Any]) -> Set[str]:
        """Extract all secrets referenced in workflow."""
        secrets = set()

        # Convert workflow to string and find secret references
        workflow_str = yaml.dump(workflow_data)
        secret_pattern = r"$\{\{\s*secrets\.([A-Z_][A-Z0-9_]*)\s*\}\}"
        matches = re.findall(secret_pattern, workflow_str, re.IGNORECASE)

        for match in matches:
            secrets.add(match.upper())

        return secrets

    def _extract_actions_from_workflow(self, workflow_data: Dict[str, Any]) -> Set[str]:
        """Extract all GitHub Actions from workflow."""
        actions = set()

        for job_name, job_config in workflow_data.get("jobs", {}).items():
            for step in job_config.get("steps", []):
                if "uses" in step:
                    actions.add(step["uses"])

        return actions

    def _find_circular_dependencies(self, dependencies: Dict[str, List[str]]) -> List[str]:
        """Find circular dependencies in job graph using DFS."""
        visited = set()
        rec_stack = set()
        circular_deps = []

        def dfs(node: str, path: List[str]) -> bool:
            if node in rec_stack:
                # Found cycle - extract the cycle path
                cycle_start = path.index(node)
                cycle_path = path[cycle_start:] + [node]
                circular_deps.append(" -> ".join(cycle_path))
                return True

            if node in visited:
                return False

            visited.add(node)
            rec_stack.add(node)

            for neighbor in dependencies.get(node, []):
                if dfs(neighbor, path + [node]):
                    return True

            rec_stack.remove(node)
            return False

        for job in dependencies:
            if job not in visited:
                dfs(job, [])

        return circular_deps

    def validate_workflow(self, workflow_path: str) -> Dict[str, Any]:
        """Validate complete workflow file."""
        try:
            with open(workflow_path, "r") as f:
                content = f.read()

            # Validate YAML syntax
            syntax_result = self.validate_yaml_syntax(content)
            workflow_data = syntax_result["data"]

            # Validate job dependencies
            dep_errors = self.validate_job_dependencies(workflow_data)

            # Validate action versions
            action_warnings = self.validate_action_versions(workflow_data)

            # Extract required secrets for validation
            secrets_used = self._extract_secrets_from_workflow(workflow_data)

            return {
                "status": "valid" if not dep_errors else "invalid",
                "syntax": syntax_result["status"],
                "dependency_errors": dep_errors,
                "action_warnings": action_warnings,
                "required_secrets": list(secrets_used),
                "validation_errors": self.validation_errors,
            }

        except Exception as e:
            error_msg = f"Workflow validation failed: {e}"
            self.logger.error(error_msg)
            return {
                "status": "invalid",
                "error": error_msg,
                "validation_errors": self.validation_errors + [error_msg],
            }


def main():
    """CLI interface for workflow validation."""
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Validate GitHub Actions workflows")
    parser.add_argument("command", choices=["validate"], help="Command to execute")
    parser.add_argument("workflow", help="Workflow name (e.g., 'data-collection')")
    parser.add_argument(
        "--workflow-dir", default=".github/workflows", help="Directory containing workflow files"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    # Determine workflow file path
    workflow_file = f"{args.workflow}.yml"
    workflow_path = Path(args.workflow_dir) / workflow_file

    if not workflow_path.exists():
        print(f"ERROR: Workflow file not found: {workflow_path}")
        sys.exit(1)

    # Initialize validator
    try:
        from phoenix_real_estate.foundation.config import EnvironmentConfigProvider

        validator = WorkflowValidator(EnvironmentConfigProvider())
    except ImportError:
        validator = WorkflowValidator()

    # Validate workflow
    result = validator.validate_workflow(str(workflow_path))

    # Output results
    if args.verbose:
        print(f"Validating workflow: {workflow_path}")
        print(f"Status: {result['status']}")

        if result.get("dependency_errors"):
            print("Dependency Errors:")
            for error in result["dependency_errors"]:
                print(f"  - {error}")

        if result.get("action_warnings"):
            print("Action Warnings:")
            for warning in result["action_warnings"]:
                print(f"  - {warning}")

        if result.get("required_secrets"):
            secrets_count = len(result["required_secrets"])
            print(f"Required Secrets ({secrets_count}):")
            for secret in sorted(result["required_secrets"]):
                print(f"  - {secret}")

    # Exit with appropriate code
    if result["status"] == "valid":
        print(f"[OK] Workflow {args.workflow} is valid")
        sys.exit(0)
    else:
        print(f"[FAIL] Workflow {args.workflow} validation failed")
        if result.get("validation_errors"):
            for error in result["validation_errors"]:
                print(f"  ERROR: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
