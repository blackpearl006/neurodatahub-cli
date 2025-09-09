#!/usr/bin/env python3
"""Fix Unicode characters in source files for conda-forge compatibility."""

import os
import re

# Unicode character replacements
UNICODE_REPLACEMENTS = {
    # Emojis and symbols to ASCII equivalents
    '🔐': '[AUTH]',
    '✓': '[✓]',
    '✗': '[✗]', 
    '→': '->',
    '•': '*',
    '⚠': '[WARNING]',
    '️': '',  # Remove variation selectors
    '📊': '[STATS]',
    '📈': '[CHART]',
    '✅': '[✓]',
    '❌': '[✗]',
    '📂': '[FOLDER]',
    'ℹ': '[INFO]',
}

def fix_unicode_in_file(filepath):
    """Replace Unicode characters in a single file."""
    print(f"Processing {filepath}...")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace Unicode characters
        for unicode_char, replacement in UNICODE_REPLACEMENTS.items():
            content = content.replace(unicode_char, replacement)
        
        # Check if any changes were made
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ Updated {filepath}")
            return True
        else:
            print(f"  - No changes needed in {filepath}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error processing {filepath}: {e}")
        return False

def main():
    """Fix Unicode characters in all Python files."""
    print("Fixing Unicode characters in neurodatahub source files...")
    print("=" * 60)
    
    files_modified = 0
    total_files = 0
    
    # Process all Python files in neurodatahub directory
    for root, dirs, files in os.walk('neurodatahub'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                total_files += 1
                
                if fix_unicode_in_file(filepath):
                    files_modified += 1
    
    print("=" * 60)
    print(f"Summary: {files_modified}/{total_files} files modified")
    
    if files_modified > 0:
        print("\n✅ Unicode characters have been replaced with ASCII equivalents")
        print("📋 Next steps:")
        print("   1. Test the package locally")
        print("   2. Update version to 1.0.1 in pyproject.toml")
        print("   3. Rebuild and upload to PyPI")
        print("   4. Update conda recipe with new version/hash")
    else:
        print("\n✓ No Unicode characters found to fix")

if __name__ == "__main__":
    main()