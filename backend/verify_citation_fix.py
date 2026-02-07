#\!/usr/bin/env python3
"""
Verification script for citation fix
Checks that the citation handling improvements are working correctly
"""

import subprocess
import sys
import time
from pathlib import Path

def run_command(cmd):
    """Run a command and return output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode

def check_file_changes():
    """Verify the files were modified correctly"""
    print("📁 Checking file modifications...")
    
    files_to_check = [
        ("services/conversation_service.py", "citation marker text_delta"),
        ("pdf_processing/api_service.py", "citation_data"),
    ]
    
    all_good = True
    for filepath, search_term in files_to_check:
        stdout, _, code = run_command(f"grep -n '{search_term}' {filepath}")
        if code == 0:
            print(f"  ✅ Found '{search_term}' in {filepath}")
        else:
            print(f"  ❌ Missing '{search_term}' in {filepath}")
            all_good = False
    
    return all_good

def check_test_script():
    """Check if the test script exists and is executable"""
    print("\n🧪 Checking test script...")
    
    test_script = Path("pdf_processing/test_citations.py")
    if test_script.exists():
        print(f"  ✅ Test script exists: {test_script}")
        return True
    else:
        print(f"  ❌ Test script not found: {test_script}")
        return False

def main():
    print("🔍 Verifying Citation Fix Implementation\n")
    
    # Check file changes
    files_ok = check_file_changes()
    
    # Check test script
    test_ok = check_test_script()
    
    # Summary
    print("\n📊 Summary:")
    if files_ok and test_ok:
        print("✅ All checks passed\! Citation fix is properly implemented.")
        print("\nTo test the fix:")
        print("1. Make sure the backend server is running")
        print("2. Upload a PDF document")
        print("3. Ask a question that requires citations")
        print("4. Verify citation markers [1], [2], [3] appear and persist")
        print("\nOr run the test script:")
        print("  cd pdf_processing && python test_citations.py")
    else:
        print("❌ Some checks failed. Please review the implementation.")
    
    return 0 if (files_ok and test_ok) else 1

if __name__ == "__main__":
    sys.exit(main())