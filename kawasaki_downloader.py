#!/usr/bin/env python3
"""
Kawasaki Manual Downloader

A program to download user manual pages from Kawasaki's interactive websites.
This script automates the process of navigating through manual pages and downloading
images one at a time.

Author: ElectricRCAircraftGuy
License: GPL-3.0
"""

import os
import re
import time
import argparse
import logging
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import Optional, List, Dict, Any

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class KawasakiDownloader:
    """Main class for downloading Kawasaki manual pages."""
    
    def __init__(self, output_dir: str = "manual_pages", headless: bool = True):
        """
        Initialize the downloader.
        
        Args:
            output_dir: Directory to save downloaded images
            headless: Whether to run browser in headless mode
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.headless = headless
        self.driver = None
        self.session = requests.Session()
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger('kawasaki_downloader')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    def _setup_driver(self) -> webdriver.Chrome:
        """Setup Chrome WebDriver with appropriate options."""
        options = Options()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Set user agent to appear more like a regular browser
        options.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        return driver
        
    def download_image(self, image_url: str, filename: str) -> bool:
        """
        Download an image from URL and save to file.
        
        Args:
            image_url: URL of the image to download
            filename: Local filename to save the image
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.session.get(image_url, timeout=30)
            response.raise_for_status()
            
            filepath = self.output_dir / filename
            with open(filepath, 'wb') as f:
                f.write(response.content)
                
            self.logger.info(f"Downloaded: {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to download {image_url}: {e}")
            return False
            
    def extract_page_image(self) -> Optional[str]:
        """
        Extract the main page image from the current page.
        
        Returns:
            URL of the page image if found, None otherwise
        """
        try:
            # Common selectors for manual page images
            image_selectors = [
                'img[src*="page"]',
                'img[src*="manual"]',
                'img[src*="pdf"]',
                '.page-image img',
                '.manual-page img',
                '#pageImage',
                '#page_image',
                'canvas',  # Some sites use canvas for PDF rendering
            ]
            
            for selector in image_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.tag_name == 'canvas':
                            # Handle canvas elements (convert to image)
                            canvas_data = self.driver.execute_script(
                                "return arguments[0].toDataURL('image/png');", element
                            )
                            return canvas_data
                        else:
                            src = element.get_attribute('src')
                            if src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.pdf']):
                                return src
                except NoSuchElementException:
                    continue
                    
            # Fallback: look for any image that might be the page
            all_images = self.driver.find_elements(By.TAG_NAME, 'img')
            for img in all_images:
                src = img.get_attribute('src')
                if src and img.size['width'] > 200 and img.size['height'] > 200:
                    return src
                    
        except Exception as e:
            self.logger.error(f"Error extracting page image: {e}")
            
        return None
        
    def find_navigation_buttons(self) -> Dict[str, Any]:
        """
        Find navigation buttons (next, previous) on the page.
        
        Returns:
            Dictionary with navigation elements
        """
        nav_elements = {'next': None, 'prev': None}
        
        # Common selectors for navigation buttons
        next_selectors = [
            'button[id*="next"]',
            'a[id*="next"]',
            'button[class*="next"]',
            'a[class*="next"]',
            'input[value*="next"]',
            'input[value*="Next"]',
            'button:contains("Next")',
            'a:contains("Next")',
            '.arrow-right',
            '.next-page',
            '[title*="next"]',
            '[title*="Next"]',
        ]
        
        prev_selectors = [
            'button[id*="prev"]',
            'a[id*="prev"]',
            'button[class*="prev"]',
            'a[class*="prev"]',
            'input[value*="prev"]',
            'input[value*="Prev"]',
            'button:contains("Previous")',
            'a:contains("Previous")',
            '.arrow-left',
            '.prev-page',
            '[title*="prev"]',
            '[title*="Previous"]',
        ]
        
        # Find next button
        for selector in next_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_enabled():
                    nav_elements['next'] = element
                    break
            except NoSuchElementException:
                continue
                
        # Find previous button
        for selector in prev_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_enabled():
                    nav_elements['prev'] = element
                    break
            except NoSuchElementException:
                continue
                
        return nav_elements
        
    def get_current_page_number(self) -> int:
        """
        Try to extract current page number from the page.
        
        Returns:
            Current page number if found, 1 otherwise
        """
        try:
            # Look for page number indicators
            page_selectors = [
                '.page-number',
                '#pageNumber',
                '#page_number',
                '.current-page',
                '[class*="page"][class*="current"]',
            ]
            
            for selector in page_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    text = element.text.strip()
                    # Extract number from text
                    match = re.search(r'\d+', text)
                    if match:
                        return int(match.group())
                except NoSuchElementException:
                    continue
                    
            # Fallback: look in URL or page title
            url = self.driver.current_url
            title = self.driver.title
            
            for text in [url, title]:
                match = re.search(r'page[=_\-\s]*(\d+)', text, re.IGNORECASE)
                if match:
                    return int(match.group(1))
                    
        except Exception as e:
            self.logger.warning(f"Could not determine page number: {e}")
            
        return 1
        
    def download_manual(self, start_url: str, max_pages: int = 100) -> None:
        """
        Download all pages of a manual starting from the given URL.
        
        Args:
            start_url: Starting URL of the manual
            max_pages: Maximum number of pages to download
        """
        self.logger.info(f"Starting download from: {start_url}")
        
        try:
            self.driver = self._setup_driver()
            self.driver.get(start_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            page_count = 0
            downloaded_images = set()
            
            while page_count < max_pages:
                try:
                    current_page = self.get_current_page_number()
                    self.logger.info(f"Processing page {current_page}")
                    
                    # Extract and download page image
                    image_url = self.extract_page_image()
                    if image_url:
                        # Handle data URLs (canvas images)
                        if image_url.startswith('data:'):
                            filename = f"page_{current_page:04d}.png"
                            import base64
                            header, data = image_url.split(',', 1)
                            image_data = base64.b64decode(data)
                            filepath = self.output_dir / filename
                            with open(filepath, 'wb') as f:
                                f.write(image_data)
                            self.logger.info(f"Saved canvas image: {filename}")
                        else:
                            # Regular URL
                            if image_url not in downloaded_images:
                                # Determine file extension
                                parsed_url = urlparse(image_url)
                                extension = Path(parsed_url.path).suffix or '.jpg'
                                filename = f"page_{current_page:04d}{extension}"
                                
                                # Make URL absolute if necessary
                                if not image_url.startswith('http'):
                                    image_url = urljoin(self.driver.current_url, image_url)
                                
                                if self.download_image(image_url, filename):
                                    downloaded_images.add(image_url)
                                    
                    # Find and click next button
                    nav_elements = self.find_navigation_buttons()
                    next_button = nav_elements.get('next')
                    
                    if next_button:
                        try:
                            # Scroll to button and click
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView(true);", next_button
                            )
                            time.sleep(1)
                            next_button.click()
                            
                            # Wait for new page to load
                            time.sleep(2)
                            WebDriverWait(self.driver, 10).until(
                                EC.staleness_of(next_button)
                            )
                            
                            page_count += 1
                            
                        except Exception as e:
                            self.logger.warning(f"Could not navigate to next page: {e}")
                            break
                    else:
                        self.logger.info("No next button found, reached end of manual")
                        break
                        
                except Exception as e:
                    self.logger.error(f"Error processing page {current_page}: {e}")
                    page_count += 1
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error during download: {e}")
            
        finally:
            if self.driver:
                self.driver.quit()
                
        self.logger.info(f"Download completed. Processed {page_count} pages.")
        self.logger.info(f"Images saved to: {self.output_dir.absolute()}")
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Download Kawasaki manual pages from interactive websites"
    )
    parser.add_argument(
        "url", 
        help="URL of the manual to download"
    )
    parser.add_argument(
        "-o", "--output", 
        default="manual_pages",
        help="Output directory for downloaded images (default: manual_pages)"
    )
    parser.add_argument(
        "-m", "--max-pages",
        type=int,
        default=100,
        help="Maximum number of pages to download (default: 100)"
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in visible mode (useful for debugging)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger('kawasaki_downloader').setLevel(logging.DEBUG)
        
    with KawasakiDownloader(
        output_dir=args.output, 
        headless=not args.no_headless
    ) as downloader:
        downloader.download_manual(args.url, args.max_pages)


if __name__ == "__main__":
    main()