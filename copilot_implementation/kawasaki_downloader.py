#!/usr/bin/env python3
"""
Kawasaki Manual Downloader

A program to download user manual pages from Kawasaki's interactive websites.
This script drives a real (headless) Chrome browser through the manual like a
user would: it opens the manual, flips through it page by page with the
viewer's own "next page" button, saves each page image the viewer displays,
and assembles all pages into a single PDF.

Author: ElectricRCAircraftGuy
License: GPL-3.0
"""

import argparse
import logging
import os
import re
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from selenium import webdriver
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Default output folder: copilot_implementation/output/ (next to this script),
# so this implementation never writes into the repo's manuals/ folder.
DEFAULT_OUTPUT_DIR = str(Path(__file__).resolve().parent / "output")

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0 Safari/537.36"
)

# Matches the page images the viewer displays, e.g. ".../pageLLUL46TJ29M4J/x2/x2.jpg?c=..."
# and captures (page folder, zoom factor).
PAGE_IMG_RE = re.compile(r"/page([^/]+)/(?:x(\d+)/x\d+|x(\d+))\.(?:jpe?g|png)", re.IGNORECASE)


class KawasakiDownloader:
    """Main class for downloading Kawasaki manual pages."""

    def __init__(self, output_dir: str = DEFAULT_OUTPUT_DIR, headless: bool = True,
                 zoom: bool = True, delay: float = 1.0, retries: int = 3,
                 retry_delay: float = 1.0, restart_every: int = 25,
                 watchdog_timeout: float = 180, max_restarts: int = 10):
        """
        Initialize the downloader.

        Args:
            output_dir: Directory to save downloaded images (and the PDF by default)
            headless: Whether to run browser in headless mode
            zoom: Use the viewer's zoom button so it loads its highest-resolution
                page images (otherwise the normal-view images are saved)
            delay: Seconds to wait after each page flip / zoom click
            retries: Download attempts per image
            retry_delay: Base delay (seconds) between download attempts
            restart_every: Restart the browser every N spreads (0 = never)
            watchdog_timeout: Kill and restart a browser that makes no
                progress for this many seconds
            max_restarts: Give up after this many restarts caused by errors
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.zoom = zoom
        self.delay = delay
        self.retries = max(1, retries)
        self.retry_delay = retry_delay
        self.restart_every = restart_every
        self.watchdog_timeout = watchdog_timeout
        self.max_restarts = max_restarts
        self._progress = time.time()
        self._stop_watchdog = threading.Event()
        self.driver = None
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.logger = self._setup_logging()
        self.saved_pages: List[Path] = []
        self.low_res_pages: List[int] = []

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
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        # A landscape window makes the viewer show two-page spreads.
        options.add_argument('--window-size=1600,1100')
        options.add_argument(f'--user-agent={USER_AGENT}')

        # Run ChromeDriver (and so Chrome) in its own process group, so a hung
        # browser can be killed completely.
        service = Service(popen_kw={'start_new_session': True}) if os.name == 'posix' else Service()
        driver = webdriver.Chrome(options=options, service=service)
        # No implicit wait: missing elements are handled with explicit waits,
        # so lookups that fail don't each cost 10 seconds.
        driver.implicitly_wait(0)
        driver.set_script_timeout(60)
        driver.set_page_load_timeout(120)
        return driver

    def download_image(self, image_url: str, filename: str) -> bool:
        """
        Download an image from URL and save to file (with retries).

        Args:
            image_url: URL of the image to download
            filename: Local filename to save the image

        Returns:
            True if successful, False otherwise
        """
        for attempt in range(1, self.retries + 1):
            try:
                response = self.session.get(image_url, timeout=(15, 30))
                response.raise_for_status()

                filepath = self.output_dir / filename
                with open(filepath, 'wb') as f:
                    f.write(response.content)

                self.logger.info(f"Downloaded: {filename} ({len(response.content) // 1024} KiB)")
                return True

            except Exception as e:
                if attempt == self.retries:
                    self.logger.error(f"Failed to download {image_url}: {e}")
                    return False
                wait = self.retry_delay * 2 ** (attempt - 1)
                self.logger.warning(f"Download failed ({e}); retrying in {wait:.0f} s")
                time.sleep(wait)
        return False

    def fetch_via_browser(self, image_url: str, filename: str) -> bool:
        """
        Save an image the viewer has already loaded by reading it from inside
        the browser (fetch() with the browser cache), so no extra download is
        usually needed. Returns False if that fails (the caller then falls
        back to download_image()).
        """
        import base64
        script = """
            const url = arguments[0], done = arguments[arguments.length - 1];
            fetch(url, {cache: 'force-cache', credentials: 'include'})
              .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.blob(); })
              .then(b => { const fr = new FileReader();
                           fr.onload = () => done(fr.result.split(',')[1]);
                           fr.onerror = () => done(null);
                           fr.readAsDataURL(b); })
              .catch(e => done(null));
        """
        try:
            data_b64 = self.driver.execute_async_script(script, image_url)
        except WebDriverException as e:
            self.logger.warning(f"Browser fetch failed for {image_url}: {e.msg if hasattr(e, 'msg') else e}")
            return False
        if not data_b64:
            return False
        data = base64.b64decode(data_b64)
        (self.output_dir / filename).write_bytes(data)
        self.logger.info(f"Saved from browser: {filename} ({len(data) // 1024} KiB)")
        return True

    # ------------------------------------------------------------ viewer access

    def switch_to_viewer_frame(self, timeout: int = 60) -> None:
        """
        The dispeBook page loads the flip-book viewer in an <iframe>. Switch
        into the frame that contains the viewer's page-flip buttons.
        """
        self.driver.switch_to.default_content()
        WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "iframe"))
        )
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.driver.switch_to.default_content()
            for frame in self.driver.find_elements(By.TAG_NAME, "iframe"):
                try:
                    self.driver.switch_to.frame(frame)
                    if self.driver.find_elements(By.ID, "flipr-btn"):
                        return
                except WebDriverException:
                    pass
                self.driver.switch_to.default_content()
            time.sleep(1)
        raise TimeoutException("Could not find the flip-book viewer frame")

    def find_navigation_buttons(self) -> Dict[str, Any]:
        """
        Find navigation buttons (next, previous) on the page.

        Returns:
            Dictionary with navigation elements
        """
        nav_elements = {'next': None, 'prev': None}

        # Valid CSS / XPath selectors (the viewer's own buttons first).
        next_selectors = [
            (By.ID, 'flipr-btn'),
            (By.CSS_SELECTOR, 'button[id*="next"], a[id*="next"]'),
            (By.CSS_SELECTOR, 'button[class*="next"], a[class*="next"]'),
            (By.CSS_SELECTOR, '.arrow-right, .next-page, [title*="next" i]'),
            (By.XPATH, '//button[contains(normalize-space(.), "Next")]'
                       ' | //a[contains(normalize-space(.), "Next")]'),
        ]
        prev_selectors = [
            (By.ID, 'flipl-btn'),
            (By.CSS_SELECTOR, 'button[id*="prev"], a[id*="prev"]'),
            (By.CSS_SELECTOR, 'button[class*="prev"], a[class*="prev"]'),
            (By.CSS_SELECTOR, '.arrow-left, .prev-page, [title*="prev" i]'),
            (By.XPATH, '//button[contains(normalize-space(.), "Previous")]'
                       ' | //a[contains(normalize-space(.), "Previous")]'),
        ]

        for key, selectors in (('next', next_selectors), ('prev', prev_selectors)):
            for by, selector in selectors:
                try:
                    elements = self.driver.find_elements(by, selector)
                except WebDriverException:
                    continue
                if elements:
                    nav_elements[key] = elements[0]
                    break

        return nav_elements

    @staticmethod
    def is_disabled(element) -> bool:
        """True if a viewer button is disabled (the viewer adds a 'disabled' class)."""
        try:
            classes = (element.get_attribute('class') or '').split()
            return 'disabled' in classes or element.get_attribute('disabled') is not None
        except StaleElementReferenceException:
            return False

    def get_current_page_number(self) -> int:
        """
        Try to extract current page number from the page.

        Returns:
            Current page number if found, 1 otherwise
        """
        if self.driver is None:
            return 1
        try:
            for by, selector in ((By.ID, 'flippage-word'), (By.CSS_SELECTOR, '.page-number'),
                                 (By.CSS_SELECTOR, '#pageNumber, #page_number, .current-page')):
                for element in self.driver.find_elements(by, selector):
                    text = (element.get_attribute('value') or element.text or
                            element.get_attribute('title') or '').strip()
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        return max(int(n) for n in numbers)
        except Exception as e:
            self.logger.warning(f"Could not determine page number: {e}")
        return 1

    def visible_page_images(self) -> List[Tuple[float, str, str, int]]:
        """
        Return the page images currently shown by the viewer as a list of
        (x position, page folder id, absolute URL, zoom factor), left to right.
        For each visible page, only its highest-resolution image is kept.
        """
        best: Dict[str, Tuple[float, str, str, int]] = {}
        for img in self.driver.find_elements(By.CSS_SELECTOR, 'img'):
            try:
                src = img.get_attribute('src') or ''
                m = PAGE_IMG_RE.search(src)
                if not m or not img.is_displayed():
                    continue
                size = img.size
                if size['width'] <= 0 or size['height'] <= 0:
                    continue
                page_id = m.group(1)
                factor = int(m.group(2) or m.group(3) or 1)
                x = img.rect['x']
            except StaleElementReferenceException:
                continue
            url = urljoin(self.driver.current_url, src)
            cur = best.get(page_id)
            if cur is None:
                best[page_id] = (x, page_id, url, factor)
            elif factor > cur[3]:
                best[page_id] = (min(x, cur[0]), page_id, url, factor)
            else:
                best[page_id] = (min(x, cur[0]), cur[1], cur[2], cur[3])
        return sorted(best.values(), key=lambda t: t[0])

    def click(self, element) -> None:
        self.driver.execute_script("arguments[0].click();", element)

    def zoom_in_fully(self) -> None:
        """Click the viewer's zoom-in button until it is disabled (max zoom),
        so the viewer loads its highest-resolution page images."""
        for _ in range(6):
            buttons = self.driver.find_elements(By.ID, 'zoomin-btn')
            if not buttons or self.is_disabled(buttons[0]):
                return
            self.click(buttons[0])
            time.sleep(self.delay)

    def zoom_out_fully(self) -> None:
        for _ in range(6):
            buttons = self.driver.find_elements(By.ID, 'zoomout-btn')
            if not buttons or self.is_disabled(buttons[0]):
                return
            self.click(buttons[0])
            time.sleep(self.delay / 2)

    def wait_for_images(self, want_factor: int, timeout: float = 20) -> List[Tuple[float, str, str, int]]:
        """Wait until at least one page is visible (and, if zooming, until
        every visible page shows an image of at least `want_factor`)."""
        deadline = time.time() + timeout
        pages = []
        while time.time() < deadline:
            pages = self.visible_page_images()
            if pages and all(p[3] >= want_factor for p in pages):
                return pages
            time.sleep(0.5)
        return pages

    # ------------------------------------------------------------ main loop

    # ------------------------------------------------------------ browser lifecycle

    def _kill_browser(self) -> None:
        """Forcefully stop ChromeDriver and its Chrome processes (they run in
        their own process group), e.g. when the browser has hung."""
        driver, self.driver = self.driver, None
        if driver is None:
            return
        try:
            pid = driver.service.process.pid
            if os.name == "posix":
                os.killpg(pid, signal.SIGKILL)
            else:
                driver.service.process.kill()
        except Exception:
            pass

    def _quit_browser(self) -> None:
        driver, self.driver = self.driver, None
        if driver is None:
            return
        try:
            driver.quit()
        except Exception:
            pass
        # Make sure no Chrome processes are left behind.
        try:
            if os.name == "posix":
                os.killpg(driver.service.process.pid, signal.SIGKILL)
        except Exception:
            pass

    def _watchdog(self) -> None:
        """Background thread: if no progress is made for `watchdog_timeout`
        seconds (a hung browser), kill the browser so the blocked call fails
        and the main loop can restart it."""
        while not self._stop_watchdog.wait(5):
            if self.driver is not None and time.time() - self._progress > self.watchdog_timeout:
                self.logger.warning(f"No progress for {self.watchdog_timeout:.0f} s: "
                                    "killing the browser so it can be restarted")
                self._progress = time.time()
                self._kill_browser()

    def _start_browser(self, start_url: str) -> None:
        """Start Chrome, open the manual, and switch into the viewer frame."""
        self._progress = time.time()
        self.driver = self._setup_driver()
        self.driver.get(start_url)
        WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        self.switch_to_viewer_frame()
        # Give the viewer time to load its first page.
        self.wait_for_images(1, timeout=30)
        # Copy the browser's cookies so fallback downloads look like the viewer's.
        for c in self.driver.get_cookies():
            self.session.cookies.set(c['name'], c['value'], domain=c.get('domain'))
        self.session.headers['Referer'] = self.driver.current_url

    def jump_to_page(self, page: int) -> None:
        """Go to a page by typing its number into the viewer's page box."""
        if page <= 1:
            return
        box = self.driver.find_element(By.ID, 'flippage-word')
        box.clear()
        box.send_keys(str(page), Keys.ENTER)
        deadline = time.time() + 20
        while time.time() < deadline:
            if abs(self.get_current_page_number() - page) <= 1:
                break
            time.sleep(0.5)
        time.sleep(self.delay)
        self.logger.info(f"Jumped to viewer page {self.get_current_page_number()}")

    # ------------------------------------------------------------ main loop

    def _capture_spread(self, want: int, max_pages: int, seen: set) -> int:
        """Save every not-yet-saved page in the currently displayed spread.
        Returns the viewer page number."""
        current_page = self.get_current_page_number()
        if self.zoom:
            self.zoom_in_fully()
        pages = self.wait_for_images(want)
        # Sometimes the viewer hasn't loaded the zoomed images yet; zoom
        # out and in again (up to 3 more times) before settling for less.
        for attempt in range(1, 4):
            if not self.zoom or (pages and all(p[3] >= want for p in pages)):
                break
            self.logger.warning(f"Viewer page {current_page}: zoomed images not loaded "
                                f"yet; retrying zoom ({attempt}/3)")
            self.zoom_out_fully()
            time.sleep(self.delay)
            self.zoom_in_fully()
            pages = self.wait_for_images(want, timeout=30)
        if not pages:
            raise RuntimeError(f"No page image visible at viewer page {current_page}")
        for _, page_id, url, factor in pages:
            if page_id in seen or len(self.saved_pages) >= max_pages:
                continue
            n = len(self.saved_pages) + 1
            ext = Path(urlparse(url).path).suffix or '.jpg'
            filename = f"page_{n:04d}{ext}"
            if not (self.fetch_via_browser(url, filename)
                    or self.download_image(url, filename)):
                raise RuntimeError(f"Could not download page {n} ({url})")
            seen.add(page_id)
            self.saved_pages.append(self.output_dir / filename)
            if factor < want:
                self.low_res_pages.append(n)
                self.logger.warning(f"Page {n} saved at only {factor}x (wanted {want}x)")
            self.logger.info(f"Saved page {n} (viewer page {current_page}, {factor}x)")
        if self.zoom:
            self.zoom_out_fully()
        return current_page

    def _flip_next(self) -> bool:
        """Click the next-page button. Returns False at the last page."""
        nav = self.find_navigation_buttons()
        next_button = nav.get('next')
        if next_button is None or self.is_disabled(next_button):
            return False
        before = self.get_current_page_number()
        self.click(next_button)
        # Wait for the page counter to change (the flip animation).
        deadline = time.time() + 15
        while time.time() < deadline and self.get_current_page_number() == before:
            time.sleep(0.25)
        time.sleep(self.delay)
        if self.get_current_page_number() == before:
            raise RuntimeError(f"Page did not change after clicking next (at page {before})")
        return True

    def download_manual(self, start_url: str, max_pages: int = 1000) -> int:
        """
        Download all pages of a manual starting from the given URL.

        The browser is restarted every `restart_every` spreads (Chrome's memory
        grows with every zoomed page) and whenever it hangs or fails; after a
        restart it jumps back to the next unsaved page.

        Args:
            start_url: Starting URL of the manual
            max_pages: Maximum number of pages to download

        Returns:
            Number of pages saved
        """
        self.logger.info(f"Starting download from: {start_url}")
        self.saved_pages = []
        self.low_res_pages = []
        seen = set()
        last_page_number = 0
        restarts = 0
        self._progress = time.time()
        self._stop_watchdog = threading.Event()
        watchdog = threading.Thread(target=self._watchdog, daemon=True)
        watchdog.start()

        try:
            self._start_browser(start_url)

            # Learn which zoom factor the viewer uses at max zoom (from the first page).
            want = 1
            if self.zoom:
                self.zoom_in_fully()
                pages = self.wait_for_images(2, timeout=20)
                want = max((p[3] for p in pages), default=1)
                self.zoom_out_fully()
                self.logger.info(f"Viewer's highest zoom loads {want}x page images")

            spreads = 0
            while len(self.saved_pages) < max_pages:
                try:
                    if self.driver is None or (self.restart_every and spreads >= self.restart_every):
                        if self.driver is not None:
                            self.logger.info(f"Restarting the browser after {spreads} spreads "
                                             "(to free its memory)")
                        self._quit_browser()
                        self._start_browser(start_url)
                        self.jump_to_page(len(self.saved_pages) + 1)
                        spreads = 0
                    current_page = self._capture_spread(want, max_pages, seen)
                    last_page_number = max(last_page_number, current_page)
                    spreads += 1
                    self._progress = time.time()
                    if len(self.saved_pages) >= max_pages:
                        break
                    if not self._flip_next():
                        self.logger.info("Next button is disabled: reached the last page")
                        break
                    self._progress = time.time()
                except Exception as e:
                    restarts += 1
                    msg = getattr(e, 'msg', None) or str(e)
                    if restarts > self.max_restarts:
                        self.logger.error(f"Giving up after {self.max_restarts} browser "
                                          f"restarts. Last error: {msg}")
                        break
                    self.logger.warning(f"Error ({msg.splitlines()[0] if msg else type(e).__name__}); "
                                        f"restarting the browser ({restarts}/{self.max_restarts}) "
                                        f"and resuming at page {len(self.saved_pages) + 1}")
                    self._kill_browser()
                    spreads = 0

        except Exception as e:
            self.logger.error(f"Error during download: {e}")

        finally:
            self._stop_watchdog.set()
            self._quit_browser()

        self.last_viewer_page = last_page_number
        self.logger.info(f"Download finished. Saved {len(self.saved_pages)} pages "
                         f"(last viewer page number seen: {last_page_number}, "
                         f"browser restarts after errors: {restarts}).")
        if self.low_res_pages:
            self.logger.warning(f"{len(self.low_res_pages)} page(s) saved below the highest "
                                f"resolution: {self.low_res_pages}")
        self.logger.info(f"Images saved to: {self.output_dir.absolute()}")
        return len(self.saved_pages)

    def build_pdf(self, pdf_path: Path) -> Path:
        """Assemble the saved page images, in order, into one PDF (lossless:
        JPEGs are embedded as-is by img2pdf)."""
        import img2pdf
        if not self.saved_pages:
            raise ValueError("No pages to put into a PDF")
        pdf_path = Path(pdf_path)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert([str(p) for p in self.saved_pages]))
        self.logger.info(f"PDF written: {pdf_path} ({len(self.saved_pages)} pages, "
                         f"{pdf_path.stat().st_size / 1e6:.1f} MB)")
        return pdf_path

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stop_watchdog.set()
        self._quit_browser()


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the script. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        description="Download Kawasaki manual pages from interactive websites "
                    "and assemble them into a PDF"
    )
    parser.add_argument(
        "url",
        help="URL of the manual to download"
    )
    parser.add_argument(
        "-o", "--output",
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for downloaded images "
             "(default: copilot_implementation/output/)"
    )
    parser.add_argument(
        "--pdf",
        help="Path of the PDF to create (default: <output>/manual.pdf)"
    )
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Only save the page images; don't build a PDF"
    )
    parser.add_argument(
        "-m", "--max-pages",
        type=int,
        default=1000,
        help="Maximum number of pages to download (default: 1000)"
    )
    parser.add_argument(
        "--no-zoom",
        action="store_true",
        help="Don't use the viewer's zoom; save the normal-view page images "
             "(smaller, lower resolution)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait after each page flip / zoom click (default: 1.0)"
    )
    parser.add_argument(
        "--restart-every",
        type=int,
        default=25,
        help="Restart the browser every N two-page spreads to limit its memory "
             "use (default: 25; 0 = never)"
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

    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger('kawasaki_downloader').setLevel(logging.DEBUG)

    with KawasakiDownloader(
        output_dir=args.output,
        headless=not args.no_headless,
        zoom=not args.no_zoom,
        delay=args.delay,
        restart_every=args.restart_every,
    ) as downloader:
        count = downloader.download_manual(args.url, args.max_pages)
        if count == 0:
            downloader.logger.error("No pages were saved.")
            return 1
        if not args.no_pdf:
            pdf_path = Path(args.pdf) if args.pdf else Path(args.output) / "manual.pdf"
            downloader.build_pdf(pdf_path)
        last = getattr(downloader, 'last_viewer_page', 0)
        if count < args.max_pages and last and count != last:
            downloader.logger.error(f"Saved {count} pages, but the viewer's last page "
                                    f"number was {last}: the download is incomplete.")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
