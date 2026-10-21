# Kawasaki
A program to download the user manuals page by page from their interactive websites. 

Kawasaki publishes its owner's manuals as interactive page-flipping "eBooks" at <https://pws.ktivs.net>. `kawasaki_manual_downloader.py` takes the link to one of these manuals, downloads every page in order, and saves the whole manual as a single PDF. The PDF:

- uses the highest-resolution page images the viewer offers (or a lower resolution if you pick one),
- is **text-searchable and text-selectable**: the viewer's own per-page text data (the glyph positions it uses for its search feature) goes into an invisible text layer on top of each page image. This uses no OCR, so the text matches the manual exactly,
- has clickable bookmarks built from the manual's table of contents.

It only downloads the same public files your web browser downloads when you view the manual. No login is needed.


## Implementations

This repo has two independent implementations. Each has its own code, dependencies, and output folder, so they can be installed, run, tested, and compared separately. **The root implementation is the primary tool.** The Copilot implementation is kept as a **backup and cross-check**: a browser-based fallback in case the viewer's internal file layout changes, which is slower and more fragile.

| | Root implementation (primary) | Copilot implementation (backup and cross-check, from PR #1, fixed) |
|---|---|---|
| Code | [`kawasaki_manual_downloader.py`](kawasaki_manual_downloader.py) (repo root) | [`copilot_implementation/kawasaki_downloader.py`](copilot_implementation/kawasaki_downloader.py) |
| Dependencies | [`requirements.txt`](requirements.txt): PyMuPDF, requests | [`copilot_implementation/requirements.txt`](copilot_implementation/requirements.txt): selenium, webdriver-manager, requests, img2pdf, plus the Chrome browser |
| Output | the PDF path you give with `-o`. The committed PDFs are in [`manuals/kawasaki_manual_downloader/`](manuals/kawasaki_manual_downloader/) | page images + `manual.pdf` in `copilot_implementation/output/` by default (ignored by git). Its PDF is **not committed**, because its pages are byte-identical to the root implementation's 4x pages. [`manuals/copilot_implementation/`](manuals/copilot_implementation/) has the verification record and per-page hashes |
| Status on the KX450 manual | works: 212-page searchable PDF with bookmarks | works: 212-page image-only PDF, every page image byte-identical to the root 4x PDF |

Run and test each one separately:

```bash
# Root implementation
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
./kawasaki_manual_downloader.py "https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN" -s 2 -o /tmp/ours_2x.pdf
pdftotext /tmp/ours_2x.pdf - | grep -ci "engine oil"        # check the text layer
deactivate

# Copilot implementation (needs Chrome)
cd copilot_implementation
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m unittest test_kawasaki                             # unit tests
python validate_installation.py                              # environment checks
python kawasaki_downloader.py "https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN" -m 4   # first 4 pages
ls output/                                                   # page images + manual.pdf
deactivate; cd ..
```

To compare the two, compare their PDFs by content with [`pdf_diff.py`](pdf_diff.py), e.g. `./pdf_diff.py manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN_4x.pdf copilot_implementation/output/manual.pdf`, or compare the page images by hash as described in [`manuals/copilot_implementation/README.md`](manuals/copilot_implementation/README.md).


## Manuals

| Model | Manual | Online viewer | PDF in this repo |
|---|---|---|---|
| KX450 (KX450MR) | Owner's Manual 99803-0401, English, **2x** (1800 x 1270 px per page, 49.9 MB, single file) | [KX450 user manual](https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN) | [manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN.pdf](manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN.pdf) |
| KX450 (KX450MR) | Owner's Manual 99803-0401, English, **4x, full resolution** (3600 x 2540 px per page, 117.2 MB, split into 3 parts) | [KX450 user manual](https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN) | `manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN_4x.pdf.part_000` ... `.part_002` + `.sha256`. Recombine it with the commands below |

GitHub won't accept files over 100 MB. So the 4x PDF is stored as three parts of 45 MiB or less (`.part_000`, `.part_001`, `.part_002`), plus a SHA-256 checksum file. The recombined 4x PDF is in `.gitignore`, so the whole file never gets committed.

### Large-file commands (`split_join_large_files.sh`)

```bash
# After `git clone` or `git pull`: rebuild EVERY split PDF under manuals/ (all subfolders) from its parts,
# then check each one against its .sha256 checksum
./split_join_large_files.sh join

# Rebuild ONE split file from <file>.part_000, .part_001, ..., and check its .sha256
./split_join_large_files.sh join <file>
#   e.g.: ./split_join_large_files.sh join manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN_4x.pdf

# After regenerating a large PDF: split it into 45 MB parts and write <file>.sha256.
# It skips the split (and says so) if the PDF's content is the same as the existing
# parts. Add --force to split anyway: ./split_join_large_files.sh split --force <file>
./split_join_large_files.sh split <file>
#   e.g.: ./split_join_large_files.sh split manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN_4x.pdf

# Show help
./split_join_large_files.sh -h
```

A full example: clone, then rebuild the 4x PDF:

```bash
git clone https://github.com/ElectricRCAircraftGuy/Kawasaki.git   # or: git pull
cd Kawasaki
./split_join_large_files.sh join
```

The same thing by hand, without the script:

```bash
cd manuals/kawasaki_manual_downloader
cat KX450_owners_manual_99803-0401_EN_4x.pdf.part_* > KX450_owners_manual_99803-0401_EN_4x.pdf
sha256sum -c KX450_owners_manual_99803-0401_EN_4x.pdf.sha256
```

A full example: regenerate, split, and commit the 4x PDF:

```bash
./kawasaki_manual_downloader.py "https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN" \
    -o manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN_4x.pdf
./split_join_large_files.sh split manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN_4x.pdf
git add manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN_4x.pdf.part_* manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN_4x.pdf.sha256
```

`split` runs `split -b 45M -d -a 3` and also writes `<file>.sha256`. For a new large file, add its whole-file name to `.gitignore` too.

To find other manuals, browse <https://pws.ktivs.net/manuals>, open a manual, and copy its `https://pws.ktivs.net/dispeBook?file=...&lang_code=...` link.


## Installation

Requires Python 3.9 or newer. Tested on Linux (Ubuntu).

```bash
git clone https://github.com/ElectricRCAircraftGuy/Kawasaki.git
cd Kawasaki

python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

The only Python dependencies are [PyMuPDF](https://pypi.org/project/PyMuPDF/) and [requests](https://pypi.org/project/requests/). You don't need to install any other system packages, such as OCR tools.


## Usage

Put the manual's URL in quotes, because it has a `&` in it:

```bash
. .venv/bin/activate

# KX450 owner's manual, at the highest resolution the viewer offers (4x, ~117.2 MB)
./kawasaki_manual_downloader.py "https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN" \
    -o manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN_4x.pdf

# The exact command used to make the PDF in this repo (2x, 49.9 MB)
./kawasaki_manual_downloader.py "https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN" \
    -s 2 -o manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN.pdf
```

Options:

```
./kawasaki_manual_downloader.py -h

  url                   Manual viewer URL (quote it!)
  -o, --output OUTPUT   Output PDF path (default: Kawasaki_manual_<file>_<lang>.pdf)
  -s, --scale SCALE     Page image resolution: 1, 2, 4, ... or 'max' (default: max)
  --no-text             Do not add the invisible, searchable text layer (images only)
  --delay DELAY         Minimum seconds between HTTP requests (default: 0.5)
  --retries RETRIES     Retries per request (default: 5)
  --page-width-mm MM    Physical PDF page width in mm (default: 210, i.e. A5 landscape)
  --cache-dir DIR       Save downloaded files here, and reuse them on later runs
```

The script waits at least 0.5 s between requests and retries failed requests with backoff. Downloading the KX450 manual's 212 pages takes about 5 to 8 minutes.

To check that the text layer works: `pdftotext manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN.pdf - | grep -i "engine oil"`


## Checking whether a regenerated PDF really changed

Regenerating a manual gives the **exact same bytes** every time, as long as the source pages haven't changed. The downloader writes no run-time timestamps (the PDF dates come from the manual's own publish date). Its PDF `/ID` is a hash of the page images and text, not a random value. So a plain `sha256sum` comparison usually works. These tools also compare by *content*: page count, each page's embedded images, each page's text, page sizes, and bookmarks. That way PDFs that differ only in metadata still count as the same. They work offline, on local files and git, and never download anything.

```bash
# Compare two PDFs by content. Exit code: 0 = same, 1 = different, 2 = error,
# 3 = no committed version found (for git inputs)
./pdf_diff.py a.pdf b.pdf

# Compare a PDF with the version committed in git: HEAD by default, or any revision.
# If git has the file as split parts, they're joined automatically.
./pdf_diff.py manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN.pdf --against-git
./pdf_diff.py manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN_4x.pdf --against-git HEAD~1

# Compare a PDF with a split set on disk, or with git objects directly
# (REV:path; ":path" = the staged version)
./pdf_diff.py new.pdf manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN_4x.pdf.part_000
./pdf_diff.py new.pdf HEAD:manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN.pdf

# Check EVERY PDF under manuals/ (all subfolders; whole files and split sets) against HEAD (or a REV),
# and list each one as NEW, CHANGED, or UNCHANGED. -v shows which pages differ.
./check_pdfs_changed.sh
./check_pdfs_changed.sh -v HEAD
```

`pdf_diff.py` gives a short summary of the differences, e.g. `page count: 211 vs 212`, `pages only in B: 50`, `page A100 vs B100: text differ`.

**Optional git pre-commit hook** (not installed by default): it blocks a commit if a staged PDF, or a split PDF's parts/checksum, has the same content as in HEAD.

```bash
git config core.hooksPath hooks          # install (this repo only)
git config --unset core.hooksPath        # uninstall
git commit --no-verify                   # skip the hook for one commit
```


## Comparison of implementations

Measured on 2026-10-20 on this repo's Linux box, using the KX450 owner's manual URL (`https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN`). Anything not measured is marked as such.

### How each approach works

- **Root implementation (primary): reads the viewer's data files directly.** It reads the `dispeBook` page's JSON to find the eBook folder. Then it downloads `book.xml` (the ordered page list, page size, and max zoom) and `menu.xml` (the table of contents). For each page it downloads the page JPEG (`page<ID>/x4/x4.jpg` etc.) and `textpoint.xml` (every character and its position) with plain HTTP requests: no browser, at least 0.5 s apart, with retries. It builds the PDF with PyMuPDF: each JPEG is embedded unchanged, the text is laid over it as invisible, searchable text, and the TOC becomes bookmarks. The output is deterministic. Details: [How it works](#how-it-works).
- **Copilot implementation (backup): drives a real browser like a person.** It opens the URL in headless Chrome with Selenium and switches into the `<iframe>` holding the flip-book. For each two-page spread it clicks zoom-in until the button is disabled (so the viewer loads its sharpest, 4x images), reads which page `<img>` elements are shown left to right, and saves those images from the browser's own cache with an in-page `fetch()` (with a `requests` fallback with retries). Then it zooms out and clicks next, until the next button is disabled. It restarts Chrome every 25 spreads to limit memory, and a watchdog kills a browser that hangs; after a restart it types the next unsaved page number into the viewer's page box and carries on. Finally `img2pdf` assembles the JPEGs, unchanged, into an image-only PDF. It only uses what the viewer shows, so it doesn't depend on `book.xml` or the folder layout, but it does depend on the viewer's buttons and iframe. Details: [its README](copilot_implementation/README.md#how-it-works).

### Results

| | Root implementation (`kawasaki_manual_downloader.py`) | Copilot implementation (`copilot_implementation/kawasaki_downloader.py`) |
|---|---|---|
| How it finds pages | `book.xml` (ordered page IDs) and `menu.xml` (TOC), found via the viewer page's JSON | Headless Chrome: the page `<img>` elements the viewer displays in each spread, flipping with the viewer's next button |
| How it fetches pages | Direct HTTP downloads of each page's JPEG and its `textpoint.xml` | The image the browser already loaded, via in-page `fetch()`; `requests` fallback |
| Dependencies | PyMuPDF, requests | selenium, webdriver-manager, requests, img2pdf, plus Chrome |
| Output format | One PDF | Page JPEGs + one PDF (`manual.pdf`) |
| Resolution / quality | Viewer's own JPEGs embedded unchanged: 4x = 3600x2540 px (default), 2x = 1800x1270 px | Viewer's own 4x JPEGs (3600x2540 px), embedded unchanged. **All 212 page images are byte-identical** (same SHA-256) to the root implementation's 4x PDF |
| Searchable text | Yes: invisible text layer from the viewer's `textpoint.xml` (no OCR). `pdftotext` finds "engine oil" 42 times in the 2x PDF | No (no OCR). `pdftotext` output is empty |
| Bookmarks / TOC | Yes, 62 bookmarks from `menu.xml` | No |
| PDF page size | 210 mm wide (A5 landscape) by default | 3600 x 2540 pt (img2pdf's default of 1 px = 1 pt) |
| Deterministic output / duplicate detection | Yes: a fresh download gave a byte-identical PDF (same sha256 as the committed 2x). `pdf_diff.py`, `check_pdfs_changed.sh`, `split` skip, and the opt-in pre-commit hook catch unchanged regenerated PDFs | Page images are identical to the source. PDF determinism not measured. Its per-page hash list can be checked with `sha256sum -c` |
| Speed | 2x from scratch (download + build): **431.3 s**. From the local cache (build only): 2x 41.6-44.6 s, 4x 42.0-43.4 s. 4x from scratch: not measured with the current version | Full 4x run (default settings): **1043.3 s** (17.4 min), with 4 planned browser restarts and 0 restarts after errors. No cache |
| Output size | 2x: 49,884,379 bytes (49.9 MB). 4x: 117,195,430 bytes (117.2 MB, committed as 3 split parts) | 4x PDF: 110,509,380 bytes (110.5 MB; not committed). Page images: 110,403,121 bytes |
| Page count | 212 (matches `book.xml` and the viewer) | 212 (matches the viewer's last page number) |
| `pdf_diff.py` root 4x vs Copilot PDF | Exit 1 (different). Every page differs in **size**, and pages with text differ in **text** (the root PDF has a text layer, the Copilot PDF has none). No page is reported with an image difference | (same) |
| Robustness / retries / rate limit | ≥0.5 s between requests, 5 retries with exponential backoff, image validation, progress/ETA | ≥1 s wait after each flip/zoom click. Browser cache first, then `requests` with 3 attempts and backoff. Browser restart every 25 spreads, 180 s hang watchdog, up to 10 restarts after errors. Exits 1 on 0 pages or a page-count mismatch. Before the restart fix, two full runs stalled for good at about 85 pages |
| Generality | Any manual on the same FLIPPER viewer (`dispeBook?file=...&lang_code=...`). Not tested on manuals other than KX450 | Same viewer; depends on its button IDs (`flipr-btn`, `zoomin-btn`, `flippage-word`) and iframe, not on its file layout. Generic fallback selectors untested. Not tested on manuals other than KX450 |
| Known limitations | Site-specific: depends on the viewer's `book.xml`/`page<ID>`/`textpoint.xml` layout. Cover/back-cover artwork has no text layer, so "KX450" isn't searchable there. A few illustration labels come out as run-together words in the text layer | Slow, needs Chrome, breaks if the viewer UI changes. No text layer or bookmarks. Page order comes from the on-screen left-to-right position (correct for KX450). See [its README](copilot_implementation/README.md) |

Notes:
- Output folders: the root implementation's committed PDFs are in [`manuals/kawasaki_manual_downloader/`](manuals/kawasaki_manual_downloader/) (2x 49.9 MB, plus 4x 117.2 MB as 45 + 45 + 21.8 MiB parts). The Copilot implementation writes to `copilot_implementation/output/`. Its PDF would duplicate the root 4x pages without the text layer and bookmarks, so it isn't committed (`manuals/copilot_implementation/*.pdf` is in `.gitignore`). [`manuals/copilot_implementation/`](manuals/copilot_implementation/) has the verification record and a 212-line per-page SHA-256 list.
- The Copilot implementation's unit tests (11 tests) and `validate_installation.py` pass. They test helper logic, PDF assembly, and the non-zero exit when 0 pages are saved, not a live download.


## How it works

1. The `dispeBook?file=...&lang_code=...` page has a JSON `data-page` attribute whose `props.url` points to the eBook folder (`/proxy/manuals/<book>/index.html`, which redirects to `/assets/manuals/<book>/`).
2. The eBook is a FLIPPER HTML5 book. `<book>/book.xml` gives the page count, the page size, the maximum zoom, and the ordered list of page IDs. `<book>/menu.xml` is the table of contents.
3. Each page is a JPEG at `<book>/page<ID>/x1.jpg`, `.../x2/x2.jpg`, or `.../x4/x4.jpg`. Each page's text comes from `<book>/page<ID>/textpoint.xml`, which lists every character with its position.
4. Each JPEG goes into the PDF unchanged (no re-compression). Then the text is written over it in invisible text (PDF render mode 3), placed and stretched to cover each word.


## License and copyright

- **Code and documentation:** Everything in this repo **except the downloaded manuals** is covered by this repo's [LICENSE](LICENSE) file (GNU GPL v3). That includes `kawasaki_manual_downloader.py`, `split_join_large_files.sh`, `pdf_diff.py`, `check_pdfs_changed.sh`, `hooks/`, `requirements.txt`, the Copilot implementation in `copilot_implementation/`, and this README.
- **Manuals / PDFs:** The manuals, and every PDF or image made from them, including everything in the [`manuals/`](manuals/) folder and its subfolders (the `.pdf` files, the split `.part_NNN` files, and anything recombined from them), are **copyrighted by Kawasaki** ("© 2023 Kawasaki Motors, Ltd.", as printed in the KX450 manual. Kawasaki Motors, Ltd. is part of the Kawasaki Heavy Industries group). They are **NOT** covered by this repo's license, and the license grants no rights to them. All rights to them belong to their copyright holder. They are stored here only as a personal reference copy of a manual that Kawasaki publishes for free online. See [`manuals/README.md`](manuals/README.md) and the README in each subfolder.

This project is not affiliated with, endorsed by, or sponsored by Kawasaki. "Kawasaki" and model names are trademarks of their respective owners.
