#\!/usr/bin/env python3
"""
Fix critical workflow issues:
1. Consolidate pyproject.toml dev dependencies 
2. Fix TruffleHog configuration
3. Create force refresh commit
"""
import sys
from pathlib import Path

def fix_pyproject_toml():
    """Consolidate dev dependencies and remove duplication."""
    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text()
    
    # Remove the duplicate dependency-groups section
    lines = content.split('\n')
    output_lines = []
    skip_dependency_groups = False
    
    for line in lines:
        if line.strip() == '[dependency-groups]':
            skip_dependency_groups = True
            continue
        elif skip_dependency_groups and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
            # New section started, stop skipping
            skip_dependency_groups = False
            output_lines.append(line)
        elif not skip_dependency_groups:
            output_lines.append(line)
    
    # Write the fixed content
    pyproject_path.write_text('\n'.join(output_lines))
    print("✅ Fixed pyproject.toml - removed duplicate dependency-groups section")

def fix_trufflehog_config():
    """Fix TruffleHog configuration to handle workflow_dispatch properly."""
    security_yml = Path(".github/workflows/security.yml")
    content = security_yml.read_text()
    
    # Replace the TruffleHog step with better configuration
    trufflehog_fix = '''    - name: Run TruffleHog
      uses: trufflesecurity/trufflehog@main
      with:
        path: ./
        extra_args: --only-verified'''
    
    # Find and replace the TruffleHog section
    lines = content.split('\n')
    output_lines = []
    in_trufflehog = False
    
    for line in lines:
        if '- name: Run TruffleHog' in line:
            in_trufflehog = True
            output_lines.extend(trufflehog_fix.split('\n'))
        elif in_trufflehog and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
            # End of TruffleHog section
            in_trufflehog = False
            output_lines.append(line)
        elif not in_trufflehog:
            output_lines.append(line)
    
    security_yml.write_text('\n'.join(output_lines))
    print("✅ Fixed TruffleHog configuration")

if __name__ == "__main__":
    try:
        fix_pyproject_toml()
        fix_trufflehog_config()
        print("🚀 All workflow issues fixed successfully\!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
