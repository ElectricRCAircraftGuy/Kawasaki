#!/usr/bin/env python3
"""
Quick validation script for Kawasaki Downloader installation

This script checks if all components are properly installed and working.
"""

import sys
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    print("Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 6:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} is compatible")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} is too old (need 3.6+)")
        return False

def check_required_files():
    """Check if all required files are present."""
    print("\nChecking required files...")
    required_files = [
        'kawasaki_downloader.py',
        'requirements.txt',
        'setup.py',
        'README.md'
    ]
    
    all_present = True
    for file in required_files:
        if Path(file).exists():
            print(f"✓ {file}")
        else:
            print(f"✗ {file} missing")
            all_present = False
            
    return all_present

def check_dependencies():
    """Check if dependencies can be imported."""
    print("\nChecking dependencies...")
    dependencies = [
        ('requests', 'HTTP requests'),
        ('selenium', 'Web automation'),
        ('webdriver_manager', 'WebDriver management')
    ]
    
    all_available = True
    for module, description in dependencies:
        try:
            __import__(module)
            print(f"✓ {module} ({description})")
        except ImportError:
            print(f"✗ {module} ({description}) - run 'pip install -r requirements.txt'")
            all_available = False
            
    return all_available

def check_main_script():
    """Check if main script can be imported."""
    print("\nChecking main script...")
    try:
        from kawasaki_downloader import KawasakiDownloader
        print("✓ KawasakiDownloader class can be imported")
        
        # Test basic instantiation
        downloader = KawasakiDownloader(output_dir="/tmp/test_kawasaki")
        print("✓ KawasakiDownloader can be instantiated")
        return True
        
    except Exception as e:
        print(f"✗ Error with main script: {e}")
        return False

def check_chrome_availability():
    """Check if Chrome browser is available."""
    print("\nChecking Chrome browser...")
    
    # Common Chrome installation paths
    chrome_paths = [
        '/usr/bin/google-chrome',
        '/usr/bin/google-chrome-stable',
        '/usr/bin/chromium-browser',
        '/usr/bin/chromium',
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            print(f"✓ Chrome found at: {path}")
            return True
            
    # Try command line
    import subprocess
    try:
        result = subprocess.run(['which', 'google-chrome'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Chrome found at: {result.stdout.strip()}")
            return True
    except:
        pass
        
    try:
        result = subprocess.run(['which', 'chromium'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Chromium found at: {result.stdout.strip()}")
            return True
    except:
        pass
    
    print("! Chrome/Chromium not found - install Chrome browser")
    return False

def main():
    """Main validation function."""
    print("Kawasaki Downloader Installation Validation")
    print("=" * 45)
    
    checks = [
        ("Python Version", check_python_version),
        ("Required Files", check_required_files),
        ("Dependencies", check_dependencies),
        ("Main Script", check_main_script),
        ("Chrome Browser", check_chrome_availability),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ {name}: Error - {e}")
            results.append((name, False))
    
    print("\n" + "=" * 45)
    print("VALIDATION SUMMARY")
    print("=" * 45)
    
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{name:<20} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 45)
    if all_passed:
        print("✓ All checks passed! Ready to use Kawasaki Downloader.")
        print("\nQuick start:")
        print("  python kawasaki_downloader.py --help")
    else:
        print("✗ Some checks failed. See messages above for details.")
        print("\nTo fix issues:")
        print("  1. Run: pip install -r requirements.txt")
        print("  2. Run: python setup.py")
        print("  3. Install Chrome browser if needed")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)