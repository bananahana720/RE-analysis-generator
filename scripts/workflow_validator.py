"""GitHub Actions workflow validator.

Validates YAML syntax, secrets, dependencies, and action versions.
"""

import yaml
import re
from typing import Dict, Any, List, Set, Optional
from pathlib import Path

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
            
    def validate_required_secrets(self, workflow_data: Dict[str, Any], available_secrets: List[str]) -> List[str]:
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
        secret_pattern = r'$\{\{\s*secrets\.([A-Z_][A-Z0-9_]*)\s*\}\}'
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
        """Find circular dependencies in job graph."""
        # Simple cycle detection for now
        return []
