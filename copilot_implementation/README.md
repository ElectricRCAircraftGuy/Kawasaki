# Copilot implementation: backup and cross-check (from PR #1, fixed)

A program to download the user manuals page by page from their interactive websites, and assemble them into a PDF.

> **This is the backup and cross-check implementation, not the primary tool.** Use the root implementation ([`../kawasaki_manual_downloader.py`](../kawasaki_manual_downloader.py)) normally: it is faster (431 s for the 2x KX450 PDF from scratch, vs 1043 s for this one at 4x; the root tool's 4x-from-scratch time wasn't measured), more robust, and its PDFs are text-searchable and have bookmarks. This browser-based version is a fallback in case the viewer's internal file layout (`book.xml`, `page<ID>/...`) changes and the root implementation stops working. It is also a cross-check: on the KX450 manual, all 212 page images it saved are byte-identical to the root implementation's 4x pages.

This folder contains the implementation GitHub Copilot wrote in PR #1, fixed so it now works. It is kept separate from the root implementation (`../kawasaki_manual_downloader.py`) so the two can be run and compared independently. It uses a different approach on purpose: it drives a real browser like a person, rather than reading the viewer's data files. It has its own `requirements.txt` and writes to its own output folder, `copilot_implementation/output/`, so it never touches the root implementation's files. See the main [README](../README.md) for a comparison of the two.

## How it works

It drives a real browser like a person would:

1. Opens the manual in headless Chrome (Selenium), then switches into the `<iframe>` that holds the flip-book viewer.
2. For each two-page spread, it clicks the viewer's zoom-in button until it's disabled, so the viewer loads its sharpest page images (4x for the KX450 manual). If the zoomed images haven't loaded, it zooms out and in again, up to 3 more times.
3. It reads which page images (`<img>` elements) the viewer is displaying, left page first, and saves them. It takes the image the browser already loaded, using `fetch()` inside the page with the browser cache, so usually no extra download is needed. If that fails, it downloads the image with `requests`, with up to 3 attempts and 1 s / 2 s backoff.
4. It zooms back out and clicks the viewer's next-page button. It stops when that button is disabled (the last page).
5. Chrome's memory grows with every zoomed page, and in long runs the browser hung after about 85 pages. So it restarts the browser every 25 spreads (`--restart-every`), and a watchdog thread kills a browser that makes no progress for 180 s. After a restart, or after any error, it reopens the manual, types the next unsaved page number into the viewer's page box (`#flippage-word`), and carries on. Pages it already saved are skipped. It gives up after 10 restarts caused by errors.
6. It assembles the saved images into a PDF with `img2pdf`. JPEGs are embedded unchanged (no re-compression). There's no searchable text layer and no bookmarks.

Tradeoffs: it's slower than reading the files directly, and more fragile. It waits after every flip and zoom, and it breaks if the viewer's buttons or layout change. But it doesn't depend on the viewer's internal file layout (`book.xml` etc.); it only uses what the viewer shows.

## What was fixed (2026-10-20)

The original PR #1 version ran on the KX450 URL for minutes, reported success, and saved **0 pages**. Fixes:

- **Invalid selectors:** `button:contains("Next")` etc. (`:contains()` is jQuery-only, not CSS) raised an "invalid selector" error on every loop. They're replaced with valid CSS/XPath, and the viewer's own buttons (`#flipr-btn`, `#flipl-btn`) are tried first.
- **iframe:** the flip-book is in an `<iframe>`, which the old code never entered. It now switches into the frame that contains the viewer.
- **Page capture:** it saves every page the viewer displays in each spread (left to right, with no duplicates), at the highest zoom the viewer offers. Before, it saved at most one image per click.
- **Navigation and end detection:** it clicks next, waits for the page number to change, and stops when the next button is disabled. The old loop could not move forward, and stopped only at `--max-pages` (default 100, now 1000).
- **No more 10 s waits:** the 10 s implicit wait made every missing selector take 10 s (2.5 to 3.5 minutes per loop). It's now off, and explicit waits are used instead.
- **Downloads hanging:** in one test run, a direct `requests` download hung for more than 8 minutes. Page images are now read from the browser (see How it works), and the `requests` fallback has connect/read timeouts and retries.
- **Browser hangs in long runs:** two full runs stalled for good after about 85 pages, inside a Selenium call to Chrome. ChromeDriver now runs in its own process group, the browser is restarted every 25 spreads, a watchdog kills a hung browser, and the run resumes at the next unsaved page (see How it works).
- **Exit codes:** the program exits **1** if 0 pages were saved, or if the number of saved pages doesn't match the viewer's last page number. Before, it exited 0 even with 0 pages.
- **PDF output:** new `--pdf` / `--no-pdf` options. `img2pdf` is added to `requirements.txt`.
- **Tests:** new tests for the page-image URL parsing, the PDF assembly, and the non-zero exit when 0 pages are saved (11 tests total).

## Test results (KX450 manual, 2026-10-20)

`python copilot_implementation/kawasaki_downloader.py "https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN"` (default settings) exited 0 after **1043.3 s** (17.4 min). It saved **212 of 212 pages** in order, at 4x (3600 x 2540 px JPEGs, 110,403,121 bytes in total), restarted the browser 4 times as planned (0 restarts after errors), and wrote a 212-page PDF, `output/manual.pdf`, of 110,509,380 bytes (110.5 MB).

**Cross-check:** all 212 page images are byte-identical (same SHA-256) to the page JPEGs in the root implementation's 4x PDF. `pdf_diff.py` reports differences only in page size and text, because this PDF has no text layer. Because the pages are identical, this PDF isn't committed. The verification record, with the per-page hash list and the commands to re-check, is in [`../manuals/copilot_implementation/`](../manuals/copilot_implementation/).

Earlier runs before the browser-restart fix stalled for good after about 85 pages.

## Installation

```bash
git clone https://github.com/ElectricRCAircraftGuy/Kawasaki.git
cd Kawasaki/copilot_implementation
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt      # requests, selenium, webdriver-manager, img2pdf
python validate_installation.py      # checks Python, files, dependencies, Chrome
```

You also need the Google Chrome (or Chromium) browser. Selenium finds a matching ChromeDriver automatically. `python setup.py` also installs the dependencies and tests the WebDriver.

## Usage

Run it from this folder, or give the path from the repo root (`python copilot_implementation/kawasaki_downloader.py ...`):

```bash
# Whole manual -> page images + PDF in copilot_implementation/output/ (manual.pdf)
python kawasaki_downloader.py "https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN"

# Choose the PDF path
python kawasaki_downloader.py "<URL>" --pdf /tmp/KX450_copilot.pdf

# Faster and smaller: skip the zoom and save the normal-view images (2x on a 1600 px wide window)
python kawasaki_downloader.py "<URL>" --no-zoom

# First 10 pages only, with a visible browser for debugging
python kawasaki_downloader.py "<URL>" -m 10 --no-headless -v
```

Options:

```
  url                   URL of the manual to download
  -o, --output DIR      Output directory for images (default: copilot_implementation/output/)
  --pdf PDF             Path of the PDF to create (default: <output>/manual.pdf)
  --no-pdf              Only save the page images; don't build a PDF
  -m, --max-pages NUM   Maximum number of pages to download (default: 1000)
  --no-zoom             Don't use the viewer's zoom; save the normal-view images
  --delay SECONDS       Wait after each page flip / zoom click (default: 1.0)
  --restart-every N     Restart the browser every N two-page spreads to limit its memory use (default: 25; 0 = never)
  --no-headless         Run the browser in visible mode
  -v, --verbose         Verbose logging
```

Output: `copilot_implementation/output/page_0001.jpg`, `page_0002.jpg`, ..., plus `manual.pdf`. The `output/` folder is ignored by git (see this folder's `.gitignore`). Its KX450 PDF is not committed (its pages are identical to the root implementation's 4x PDF). [`../manuals/copilot_implementation/`](../manuals/copilot_implementation/) has the verification record and per-page hashes.

## Tests

```bash
python -m unittest test_kawasaki     # from this folder (11 tests; no network needed)
python validate_installation.py
python example_usage.py --examples   # usage examples; `python example_usage.py` downloads 10 pages
```

## Remaining limitations

- **Slow:** 1043 s for the KX450 manual at 4x, vs 431 s for the root implementation at 2x from scratch (its 4x-from-scratch time wasn't measured). Every flip and zoom waits for the viewer.
- **Fragile:** it depends on the viewer's button IDs (`flipr-btn`, `zoomin-btn`, `flippage-word`), the iframe, and the page-image URL pattern (`page<ID>/x<N>.jpg`). If the viewer changes, it may stop working. The generic fallback selectors aren't tested on other sites.
- **No searchable text** (no OCR) and no bookmarks.
- **Page size:** the PDF's pages are sized from the image pixels at img2pdf's default 72 dpi (3600 x 2540 pt for 4x), not the paper size. Viewers scale them fine. When printing, use "fit to page".
- **Page order** comes from the left-to-right position of the displayed pages in each spread. It was correct for the KX450 manual. It may need changes for a viewer in single-page mode.
- **Not tested** on manuals other than KX450.

## Additional Scripts

- `validate_installation.py`: checks that all components are installed and working.
- `example_usage.py`: usage examples and programmatic use (`KawasakiDownloader(...).download_manual(url)`, then `.build_pdf(path)`).
- `setup.py`: installs the dependencies and tests the Chrome WebDriver.

## Requirements

- Python 3.8+
- Chrome browser
- Internet connection

## License

This code is licensed under the GPL-3.0 License - see the repo's [LICENSE](../LICENSE) file for details. Downloaded manuals and pages are copyrighted by Kawasaki and are not covered by that license (see the main [README](../README.md)).

## Legal Notice

This tool is for personal use and educational purposes. Please respect website terms of service and copyright laws. Only download content you have permission to access.
