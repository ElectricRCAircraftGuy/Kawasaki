#!/usr/bin/env python3
"""
Setup script for Kawasaki Downloader

This script helps set up the Chrome WebDriver automatically.
"""

import sys
import subprocess
from pathlib import Path

try:
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
except ImportError:
    print("Installing required packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service

def setup_chrome_driver():
    """Download and setup Chrome WebDriver."""
    try:
        print("Setting up Chrome WebDriver...")
        driver_path = ChromeDriverManager().install()
        print(f"Chrome WebDriver installed at: {driver_path}")
        
        # Test the driver
        print("Testing WebDriver...")
        service = Service(driver_path)
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(service=service, options=options)
        driver.get("https://www.google.com")
        print("WebDriver test successful!")
        driver.quit()
        
        return True
        
    except Exception as e:
        print(f"Error setting up WebDriver: {e}")
        return False

def main():
    """Main setup function."""
    print("Kawasaki Downloader Setup")
    print("=" * 25)
    
    # Check if requirements.txt exists
    if not Path("requirements.txt").exists():
        print("Error: requirements.txt not found!")
        return False
        
    # Install Python dependencies
    print("Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Dependencies installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False
        
    # Setup Chrome WebDriver
    if not setup_chrome_driver():
        print("Failed to setup Chrome WebDriver")
        return False
        
    print("\nSetup completed successfully!")
    print("\nUsage:")
    print("  python kawasaki_downloader.py <URL>")
    print("\nExample:")
    print("  python kawasaki_downloader.py https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)