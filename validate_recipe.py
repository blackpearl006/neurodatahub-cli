#!/usr/bin/env python3
"""Validate conda recipe by checking key components."""

import re
from pathlib import Path

def validate_conda_recipe():
    """Validate the conda recipe meta.yaml file."""
    recipe_path = Path("conda-recipe/meta.yaml")
    
    if not recipe_path.exists():
        print("❌ meta.yaml not found")
        return False
    
    with open(recipe_path) as f:
        content = f.read()
    
    checks = [
        (r"name:\s*\{\{.*name.*\}\}", "Package name template"),
        (r"version:\s*\{\{.*version.*\}\}", "Version template"),
        (r"url:.*pypi\.io", "PyPI source URL"),
        (r"sha256:\s*[a-f0-9]{64}", "SHA256 hash"),
        (r"script:\s*\{\{.*PYTHON.*\}\}", "Build script"),
        (r"entry_points:", "Entry points section"),
        (r"neurodatahub\s*=", "CLI entry point"),
        (r"python\s*>=3\.8", "Python version requirement"),
        (r"click\s*>=8\.0", "Click dependency"),
        (r"requests\s*>=", "Requests dependency"),
        (r"rich\s*>=", "Rich dependency"),
        (r"test:", "Test section"),
        (r"imports:", "Import tests"),
        (r"commands:", "Command tests"),
        (r"license:\s*MIT", "License specification"),
        (r"summary:", "Package summary"),
        (r"recipe-maintainers:", "Maintainers section"),
    ]
    
    print("Validating conda recipe...")
    print("=" * 40)
    
    passed = 0
    for pattern, description in checks:
        if re.search(pattern, content, re.IGNORECASE):
            print(f"✅ {description}")
            passed += 1
        else:
            print(f"❌ {description}")
    
    print("=" * 40)
    print(f"Validation: {passed}/{len(checks)} checks passed")
    
    if passed == len(checks):
        print("🎉 Recipe validation successful!")
        return True
    else:
        print("⚠️  Some checks failed - review recipe")
        return False

if __name__ == "__main__":
    validate_conda_recipe()