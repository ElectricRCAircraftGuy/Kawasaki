#!/usr/bin/env python3
"""
Test script for Kawasaki Downloader

This script tests the basic functionality without requiring the actual website.
"""

import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add the current directory to the path so we can import our module
sys.path.insert(0, str(Path(__file__).parent))

try:
    from kawasaki_downloader import KawasakiDownloader
except ImportError as e:
    print(f"Error importing kawasaki_downloader: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)


class TestKawasakiDownloader(unittest.TestCase):
    """Test cases for KawasakiDownloader class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.downloader = KawasakiDownloader(output_dir=self.temp_dir, headless=True)
        
    def tearDown(self):
        """Clean up after tests."""
        if self.downloader.driver:
            self.downloader.driver.quit()
            
    def test_init(self):
        """Test downloader initialization."""
        self.assertIsNotNone(self.downloader)
        self.assertEqual(str(self.downloader.output_dir), self.temp_dir)
        self.assertTrue(self.downloader.headless)
        self.assertIsNotNone(self.downloader.logger)
        
    def test_output_directory_creation(self):
        """Test that output directory is created."""
        self.assertTrue(self.downloader.output_dir.exists())
        self.assertTrue(self.downloader.output_dir.is_dir())
        
    @patch('requests.Session.get')
    def test_download_image_success(self, mock_get):
        """Test successful image download."""
        # Mock successful response
        mock_response = Mock()
        mock_response.content = b'fake image data'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.downloader.download_image('http://example.com/image.jpg', 'test.jpg')
        
        self.assertTrue(result)
        test_file = self.downloader.output_dir / 'test.jpg'
        self.assertTrue(test_file.exists())
        self.assertEqual(test_file.read_bytes(), b'fake image data')
        
    @patch('requests.Session.get')
    def test_download_image_failure(self, mock_get):
        """Test failed image download."""
        # Mock failed response
        mock_get.side_effect = Exception("Network error")
        
        result = self.downloader.download_image('http://example.com/image.jpg', 'test.jpg')
        
        self.assertFalse(result)
        test_file = self.downloader.output_dir / 'test.jpg'
        self.assertFalse(test_file.exists())
        
    def test_get_current_page_number_default(self):
        """Test default page number when no driver is available."""
        # Without a driver, should return default page 1
        page_num = self.downloader.get_current_page_number()
        self.assertEqual(page_num, 1)
        
    def test_logging_setup(self):
        """Test that logging is properly configured."""
        logger = self.downloader.logger
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, 'kawasaki_downloader')
        self.assertTrue(len(logger.handlers) > 0)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions and edge cases."""
    
    def test_file_extension_handling(self):
        """Test various file extension scenarios."""
        test_cases = [
            ('http://example.com/page1.jpg', '.jpg'),
            ('http://example.com/page1.png', '.png'),
            ('http://example.com/page1', ''),
            ('http://example.com/page1.PDF', '.PDF'),
        ]
        
        for url, expected_ext in test_cases:
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            extension = Path(parsed_url.path).suffix
            self.assertEqual(extension, expected_ext)
            
    def test_data_url_detection(self):
        """Test detection of data URLs."""
        data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        regular_url = "http://example.com/image.jpg"
        
        self.assertTrue(data_url.startswith('data:'))
        self.assertFalse(regular_url.startswith('data:'))


def run_basic_tests():
    """Run basic functionality tests."""
    print("Running Kawasaki Downloader Tests")
    print("=" * 35)
    
    # Test imports
    try:
        import requests
        import selenium
        from selenium import webdriver
        print("✓ All required modules imported successfully")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
        
    # Test basic class instantiation
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = KawasakiDownloader(output_dir=temp_dir)
            print("✓ KawasakiDownloader instantiated successfully")
            print(f"✓ Output directory created: {downloader.output_dir}")
    except Exception as e:
        print(f"✗ Error creating downloader: {e}")
        return False
        
    # Test Chrome WebDriver availability
    try:
        from selenium.webdriver.chrome.options import Options
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Try to create driver (will fail if Chrome/ChromeDriver not available)
        try:
            driver = webdriver.Chrome(options=options)
            driver.quit()
            print("✓ Chrome WebDriver available")
        except Exception as e:
            print(f"! Chrome WebDriver issue: {e}")
            print("  Run 'python setup.py' to install ChromeDriver")
            
    except Exception as e:
        print(f"✗ WebDriver setup error: {e}")
        return False
        
    print("\nBasic tests completed successfully!")
    return True


def main():
    """Main test function."""
    print("Kawasaki Downloader Test Suite")
    print("=" * 30)
    
    # Run basic tests first
    if not run_basic_tests():
        print("Basic tests failed!")
        return False
        
    # Run unit tests
    print("\nRunning unit tests...")
    unittest.main(verbosity=2, exit=False)
    
    return True


if __name__ == "__main__":
    main()