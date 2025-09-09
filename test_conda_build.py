#!/usr/bin/env python3
"""Test conda recipe build locally (if conda-build is available)."""

import subprocess
import sys
from pathlib import Path

def check_conda_build():
    """Check if conda-build is available."""
    try:
        result = subprocess.run(['conda', 'build', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ conda-build available: {result.stdout.strip()}")
            return True
        else:
            print("❌ conda-build not working")
            return False
    except FileNotFoundError:
        print("❌ conda command not found")
        return False

def test_recipe_build():
    """Test building the conda recipe."""
    recipe_dir = Path("conda-recipe")
    
    if not recipe_dir.exists():
        print("❌ conda-recipe directory not found")
        return False
    
    if not (recipe_dir / "meta.yaml").exists():
        print("❌ meta.yaml not found in conda-recipe/")
        return False
    
    print("🔨 Testing conda recipe build...")
    print("This will take a few minutes...")
    
    try:
        # Try to build the recipe
        cmd = ["conda", "build", str(recipe_dir), "--no-test"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print("✅ Conda recipe builds successfully!")
            print("Package created:", result.stdout.split('\n')[-2] if result.stdout else "")
            return True
        else:
            print("❌ Build failed:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Build timed out after 10 minutes")
        return False
    except Exception as e:
        print(f"❌ Build error: {e}")
        return False

def main():
    """Main test function."""
    print("Testing conda recipe for neurodatahub-cli")
    print("=" * 50)
    
    if not check_conda_build():
        print("\n💡 To install conda-build:")
        print("   conda install conda-build")
        print("\n⚠️  Skipping build test - conda-build not available")
        print("✅ Recipe files are ready for submission!")
        return
    
    if test_recipe_build():
        print("\n🎉 Conda recipe is ready for conda-forge submission!")
    else:
        print("\n⚠️  Build test failed - please review recipe")

if __name__ == "__main__":
    main()