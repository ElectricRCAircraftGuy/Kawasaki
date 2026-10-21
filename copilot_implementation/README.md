# Copilot implementation: backup and cross-check (from PR #1, fixed)

A program to download the user manuals page by page from their interactive websites, and assemble them into a PDF.

> **This is the backup and cross-check implementation, not the primary tool.** Use the root implementation ([`../kawasaki_manual_downloader.py`](../kawasaki_manual_downloader.py)) normally: it is faster (431 s for the 2x KX450 PDF from scratch, vs 1043 s for this one at 4x; the root tool's 4x-from-scratch time wasn't measured), more robust, and its PDFs are text-searchable and have bookmarks. This browser-based version is a fallback in case the viewer's internal file layout (`book.xml`, `page<ID>/...`) changes and the root implementation stops working. It is also a cross-check: on the KX450 manual, all 212 page images it saved are byte-identical to the root implementation's 4x pages.

This folder contains the implementation GitHub Copilot wrote in PR #1, fixed so it now works. It is kept separate from the root implementation (`../kawasaki_manual_downloader.py`) so the two can be run and compared independently. It uses a different approach on purpose: it drives a real browser like a person, rather than reading the viewer's data files. It has its own `requirements.txt` and writes to its own output folder, `copilot_implementation/output/`, so it never touches the root implementation's files. See the main [README](../README.md#comparison-of-implementations) for a comparison of the two, and [Fixes and test results](#fixes-and-test-results-2026-10-20) below for what was fixed and measured.

## How it works

It drives a real browser like a person would:

1. Opens the manual in headless Chrome (Selenium), then switches into the `<iframe>` that holds the flip-book viewer.
2. For each two-page spread, it clicks the viewer's zoom-in button until it's disabled, so the viewer loads its sharpest page images (4x for the KX450 manual). If the zoomed images haven't loaded, it zooms out and in again, up to 3 more times.
3. It reads which page images (`<img>` elements) the viewer is displaying, left page first, and saves them. It takes the image the browser already loaded, using `fetch()` inside the page with the browser cache, so usually no extra download is needed. If that fails, it downloads the image with `requests`, with up to 3 attempts and 1 s / 2 s backoff.
4. It zooms back out and clicks the viewer's next-page button. It stops when that button is disabled (the last page).
5. Chrome's memory grows with every zoomed page, and in long runs the browser hung after about 85 pages. So it restarts the browser every 25 spreads (`--restart-every`), and a watchdog thread kills a browser that makes no progress for 180 s. After a restart, or after any error, it reopens the manual, types the next unsaved page number into the viewer's page box (`#flippage-word`), and carries on. Pages it already saved are skipped. It gives up after 10 restarts caused by errors.
6. It assembles the saved images into a PDF with `img2pdf`. JPEGs are embedded unchanged (no re-compression). There's no searchable text layer and no bookmarks.

Tradeoffs: it's slower than reading the files directly, and more fragile. It waits after every flip and zoom, and it breaks if the viewer's buttons or layout change. But it doesn't depend on the viewer's internal file layout (`book.xml` etc.); it only uses what the viewer shows.

## Fixes and test results (2026-10-20)

Everything in this section was measured on 2026-10-20 on this repo's Linux box (Chrome 155, selenium 4.51.0), on the KX450 owner's manual: `https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN`. Times are MST (UTC-7).

### 1. What was broken in the original PR #1 version

- **Invalid selectors:** it looked for buttons with selectors like `button:contains("Next")`. `:contains()` is jQuery-only, not CSS, so Selenium raised an "invalid selector" error on every loop.
- **Never entered the flip-book iframe:** the viewer is in an `<iframe>` (`/assets/manuals/<book>/index.html`), and the old code only searched the top-level page, so it never found a page image or a working next button.
- **Images only, no PDF:** even a working run would have produced only separate image files.
- **Reported success with 0 pages:** errors in the loop were logged and skipped, and it exited 0. Also, a 10 s implicit wait made every missing selector cost 10 s. Measured runs:

| Command (from the repo root) | Result |
|---|---|
| `... kawasaki_downloader.py "<URL>" -o /tmp/copilot_run2 -m 2` | 407.4 s, exit 0, logged "Processed 2 pages", **0 images** saved |
| `... kawasaki_downloader.py "<URL>" -m 1` | 207.6 s, exit 0, **0 images** saved |
| `... kawasaki_downloader.py "<URL>"` (default settings; `-m 100` at the time) | stopped by hand after about 4 min, **0 images** saved |

### 2. What was fixed

- **Valid selectors:** valid CSS/XPath, trying the viewer's own buttons first (`#flipr-btn`, `#flipl-btn`, `zoomin-btn`, `zoomout-btn`).
- **iframe switch:** it switches into the frame that contains the viewer.
- **Zoom to 4x per spread:** for each two-page spread it clicks zoom-in until the button is disabled, so the viewer loads its sharpest images (4x), and retries the zoom up to 3 more times if they haven't loaded.
- **Left-to-right, no duplicates:** it saves every page image shown in the spread, ordered by on-screen position, skipping pages it already saved.
- **Browser-cache capture with a `requests` fallback:** it reads each image the browser already loaded, using `fetch()` inside the page. If that fails, it downloads it with `requests`, with connect/read timeouts and up to 3 attempts with 1 s / 2 s backoff. (In one test run, a plain `requests` download had hung for more than 8 minutes.)
- **Last-page detection:** it clicks next, waits for the page number to change, and stops when the next button is disabled.
- **Exit codes:** exit **1** if 0 pages were saved, or if the number saved doesn't match the viewer's last page number (an incomplete run).
- **PDF assembly:** `img2pdf` puts the JPEGs into `manual.pdf` unchanged (`--pdf PATH`, `--no-pdf`). `img2pdf` is in `requirements.txt`.
- The 10 s implicit wait is gone, replaced by explicit waits. There are new unit tests, including one for the exit when 0 pages are saved (11 tests in total, all passing).

### 3. The hang in long runs, and its fix

After the fixes above, two full runs **froze for good** after about 81 and 85 pages. In the second run, the last page was saved at 21:50:59 and nothing happened for more than 7 minutes. A `py-spy` stack dump showed the program stuck inside a Selenium call to Chrome (`execute_async_script`, waiting for ChromeDriver's reply). Chrome's renderer process was using about 1 GB.

Fix:
- **Own process group:** ChromeDriver, and so Chrome, runs in its own process group, so a hung browser can be killed completely, with no leftover Chrome processes.
- **Planned restarts:** it restarts the browser every **25 spreads** (`--restart-every N`; 0 = never) to free memory.
- **Watchdog:** a background thread kills the browser if there's no progress for **180 s**. The blocked call then fails, and the main loop restarts Chrome. It gives up after 10 restarts caused by errors.
- **Resume:** after any restart, it reopens the manual, types the next unsaved page number into the viewer's page box (`#flippage-word`), and carries on. Pages it already saved are skipped.

Test of the restart/resume path: `-m 9 --restart-every 2 --no-pdf` restarted the browser twice (jumping to viewer pages 5 and 9) and saved 9 pages in 73.7 s, all at 4x. The pages saved right after each restart (4, 8, 9) were byte-identical to the same pages from an earlier run that didn't restart. No Chrome processes were left over.

### 4. Full KX450 run

Command (from the repo root, default settings):

```bash
python copilot_implementation/kawasaki_downloader.py "https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN"
```

| | Result |
|---|---|
| Date / time | 2026-10-20, 22:01–22:18 MST (last page saved 22:18:41) |
| Exit code | 0 |
| Runtime | **1043.3 s** (17.4 min), including writing the PDF |
| Browser restarts | 4 planned (every 25 spreads, at viewer pages 51, 101, 151, 201); 0 after errors |
| Pages | **212 of 212**, in order (the viewer's last page number was 212) |
| Resolution | 4x: 3600 x 2540 px JPEG for every page |
| Page images | `output/page_0001.jpg` ... `page_0212.jpg`, 110,403,121 bytes in total |
| PDF | `output/manual.pdf`: 110,509,380 bytes (110.5 MB), 212 pages, page size 3600 x 2540 pt |
| Text layer | none (no OCR). `pdftotext` output is empty |
| Bookmarks | none |
| Visual check | rendered page 100 to PNG: legible, and it's printed page 98 ("Maintenance and Adjustment"), as expected |

### 5. Byte-identity check vs the root implementation's 4x PDF

**All 212 page images are byte-identical** (same SHA-256) to the JPEGs embedded in the root implementation's [`KX450_owners_manual_99803-0401_EN_4x.pdf`](../manuals/kawasaki_manual_downloader/) (recombined with `./split_join_large_files.sh join`): 212 match, 0 differ. It was checked two ways:
- a script that hashes each page image embedded in our 4x PDF (PyMuPDF `extract_image`) and compares it with `page_NNNN.jpg`, page by page,
- `pdfimages -j` (writes the embedded JPEGs unchanged), then a comparison of the 212 hashes with the per-page list in [`../manuals/copilot_implementation/KX450_99803-0401_EN_4x_page_images.sha256`](../manuals/copilot_implementation/KX450_99803-0401_EN_4x_page_images.sha256). `sha256sum -c` of that list against `output/` passes too.

`./pdf_diff.py <root 4x PDF> output/manual.pdf` exits **1** (different) only because of **page size** (root: 210 mm wide pages; this PDF: 3600 x 2540 pt) and **text** (the root PDF has an invisible text layer, this one has none). It reports no page with an image difference. Because the pages are identical, this PDF isn't committed. [`../manuals/copilot_implementation/README.md`](../manuals/copilot_implementation/README.md) has the commands to regenerate and re-check it.

**Speed compared with the root implementation:**

| | Root implementation | This implementation |
|---|---|---|
| From scratch | 2x: 431.3 s. 4x: not measured | 4x: 1043.3 s |
| Rebuild from local cache | 2x: 41.6–44.6 s. 4x: 42.0–43.4 s | no cache (every run re-downloads through the browser) |

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

- **Slow:** 1043.3 s for the KX450 manual at 4x (see [Fixes and test results](#fixes-and-test-results-2026-10-20)), vs 431 s for the root implementation at 2x from scratch (its 4x-from-scratch time wasn't measured). Every flip and zoom waits for the viewer.
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
