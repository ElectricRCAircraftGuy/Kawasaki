#!/usr/bin/env python3
"""
Download a Kawasaki owner's manual from the interactive "eBook" viewer at
https://pws.ktivs.net/dispeBook?file=<manual-number>&lang_code=<lang>
page by page, and assemble all pages into a single PDF.

How the viewer works (as of 2026-10):
  1. The `dispeBook` page is an Inertia.js app; its HTML contains a JSON
     `data-page` attribute whose `props.url` points to the eBook folder,
     e.g. `/proxy/manuals/<book-folder>/index.html`, which redirects to
     `/assets/manuals/<book-folder>/index.html`.
  2. The eBook is a FLIPPER (Logosware) HTML5 book. `<book-folder>/book.xml`
     lists the page count, page size, the maximum zoom level, and the
     ordered list of page IDs. `<book-folder>/menu.xml` is the table of
     contents.
  3. Each page image is served as
     `<book-folder>/page<PAGE_ID>/x1.jpg` (1x), `.../x2/x2.jpg` (2x), and
     `.../x4/x4.jpg` (4x), up to the book's maxMagnification.
  4. Each page also has `<book-folder>/page<PAGE_ID>/textpoint.xml`, which
     the viewer uses for text search: every glyph (character) on the page
     with its position and size. This script uses it to put an invisible,
     correctly positioned text layer over each page image, so the PDF is
     text-searchable and text-selectable (no OCR needed).

This script only downloads the same publicly served files that a normal
web browser downloads when you view the manual. No login is needed.

The downloaded manuals are copyrighted by Kawasaki. See README.md.
"""

import argparse
import hashlib
import html
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import pymupdf  # PyMuPDF
import requests

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0 Safari/537.36 kawasaki_manual_downloader/1.0 "
    "(+https://github.com/ElectricRCAircraftGuy/Kawasaki)"
)
# Kawasaki owner's manual pages are A5 landscape (900 x 635 px at 1x, ratio ~1.417).
DEFAULT_PAGE_WIDTH_MM = 210.0


def log(msg):
    print(msg, file=sys.stderr, flush=True)


class Fetcher:
    """A small polite HTTP client: one shared session, a delay between
    requests, and retries with exponential backoff."""

    def __init__(self, delay=0.5, retries=5, timeout=60):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.delay = delay
        self.retries = retries
        self.timeout = timeout
        self._last = 0.0

    def get(self, url, referer=None):
        headers = {"Referer": referer} if referer else {}
        for attempt in range(1, self.retries + 1):
            wait = self.delay - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            try:
                r = self.session.get(url, headers=headers, timeout=self.timeout)
                if r.status_code == 200:
                    return r
                # 4xx (other than 429) won't fix itself by retrying.
                if 400 <= r.status_code < 500 and r.status_code != 429:
                    r.raise_for_status()
                err = f"HTTP {r.status_code}"
            except requests.HTTPError:
                raise
            except requests.RequestException as e:
                err = str(e)
            if attempt == self.retries:
                raise RuntimeError(f"Failed to GET {url} after {attempt} attempts: {err}")
            backoff = 2 ** attempt
            log(f"  {err} for {url}; retrying in {backoff} s ({attempt}/{self.retries})")
            time.sleep(backoff)


def find_book_base_url(fetcher, manual_url):
    """Return the base URL (ending in '/') of the FLIPPER eBook folder."""
    parsed = urlparse(manual_url)
    # Allow passing the eBook folder / index.html URL directly too.
    if "/manuals/" in parsed.path and not parsed.path.endswith("dispeBook"):
        base = manual_url.split("?")[0]
        base = base.rsplit("/", 1)[0] + "/" if base.endswith(".html") else base.rstrip("/") + "/"
        return base.replace("/proxy/manuals/", "/assets/manuals/")

    r = fetcher.get(manual_url)
    m = re.search(r'data-page="([^"]+)"', r.text)
    if not m:
        raise RuntimeError("Could not find the viewer's data-page JSON in the page. "
                           "Has the site changed, or is the manual number/language wrong?")
    data = json.loads(html.unescape(m.group(1)))
    book_url = (data.get("props") or {}).get("url")
    if not book_url:
        raise RuntimeError("The viewer page did not contain an eBook URL. "
                           "Check the `file=` and `lang_code=` parameters.")
    book_url = urljoin(manual_url, book_url)
    # /proxy/... 302-redirects to /assets/...; go straight to /assets/.
    book_url = book_url.replace("/proxy/manuals/", "/assets/manuals/")
    return book_url.rsplit("/", 1)[0] + "/"


def text_of(root, path, default=None):
    el = root.find(path)
    return el.text.strip() if el is not None and el.text else default


def parse_book_xml(xml_bytes):
    root = ET.fromstring(xml_bytes)
    info = {
        "title": text_of(root, "bookInformation/bookTitle", "manual"),
        "total": int(text_of(root, "bookInformation/total", "0")),
        "max_mag": int(float(text_of(root, "bookInformation/maxMagnification", "1"))),
        "page_width": int(float(text_of(root, "bookInformation/pageWidth", "0"))),
        "page_height": int(float(text_of(root, "bookInformation/pageHeight", "0"))),
        "page_ids": [p for p in (text_of(root, "bookInformation/data", "") or "").split(",") if p],
        "publish_date": text_of(root, "publishDate"),
    }
    if not info["page_ids"]:
        raise RuntimeError("book.xml did not contain a page list.")
    if info["total"] and info["total"] != len(info["page_ids"]):
        log(f"Warning: book.xml says {info['total']} pages but lists {len(info['page_ids'])} page IDs.")
    return info


def parse_menu_xml(xml_bytes):
    """Return a nested list of (title, page_number, children) from menu.xml."""
    def walk(el):
        out = []
        for m in el.findall("menu"):
            try:
                page = int(m.get("pagenum"))
            except (TypeError, ValueError):
                continue
            out.append((m.get("name", "").strip(), page, walk(m)))
        return out
    try:
        return walk(ET.fromstring(xml_bytes))
    except ET.ParseError:
        return []


def page_image_url(base, page_id, scale):
    if scale == 1:
        return f"{base}page{page_id}/x1.jpg"
    return f"{base}page{page_id}/x{scale}/x{scale}.jpg"


def default_output_name(manual_url, title):
    q = parse_qs(urlparse(manual_url).query)
    file_id = (q.get("file") or [None])[0]
    lang = (q.get("lang_code") or [None])[0]
    if file_id:
        name = f"Kawasaki_manual_{file_id}" + (f"_{lang}" if lang else "")
    else:
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", title)
    return name + ".pdf"


def parse_textpoint_xml(xml_bytes):
    """Parse a page's textpoint.xml into a list of words.

    Returns a list of (text, x0, y_bottom, x1, height) in viewer page
    coordinates (origin at top left, 1x page size). The file lists single
    glyphs without spaces, so glyphs are grouped into words by the gaps
    between them and by line (y) changes."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []
    words = []
    cur = None  # [text, x0, y, x1, h]
    for g in root.iter("G"):
        t = g.get("t")
        try:
            x, y, w, h = (float(g.get(k)) for k in ("x", "y", "w", "h"))
        except (TypeError, ValueError):
            continue
        if not t or not t.strip():
            if cur:
                words.append(cur)
                cur = None
            continue
        if cur is not None:
            same_line = abs(y - cur[2]) < 0.3 * max(h, cur[4])
            gap = x - cur[3]
            if same_line and -0.5 * h < gap < 0.1 * h:
                cur[0] += t
                cur[3] = max(cur[3], x + w)
                continue
            words.append(cur)
        cur = [t, x, y, x + w, h]
    if cur:
        words.append(cur)
    return [tuple(wd) for wd in words]


# The invisible text uses the built-in Helvetica font, which only covers
# Latin-1; map the other characters found in the manuals to close equivalents.
CHAR_MAP = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2022": "\u00b7", "\u25cb": "o",
    "\u2020": "+", "\u2191": "^", "\u2193": "v", "\u2192": "->",
})


def add_invisible_text(page, words, scale):
    """Write `words` (viewer coordinates) onto `page` as invisible text
    (PDF text render mode 3), stretched to cover each word on the image."""
    font = "helv"
    for text, x0, y, x1, h in words:
        text = text.translate(CHAR_MAP)
        text = "".join(c if ord(c) < 256 else "?" for c in text)
        fontsize = 0.8 * h * scale
        if fontsize <= 0:
            continue
        # In textpoint.xml, y is the bottom of the glyph's em box; the baseline
        # sits about 20% of the box height above it.
        origin = pymupdf.Point(x0 * scale, (y - 0.2 * h) * scale)
        natural = pymupdf.get_text_length(text, fontname=font, fontsize=fontsize)
        target = (x1 - x0) * scale
        sx = target / natural if natural > 0 and target > 0 else 1.0
        # A real trailing space after each word keeps word breaks intact for
        # search and copy/paste in PDF viewers.
        page.insert_text(origin, text + " ", fontsize=fontsize, fontname=font, render_mode=3,
                         morph=(origin, pymupdf.Matrix(sx, 1)))


def pdf_date_from_publish_date(publish_date):
    """Turn book.xml's publishDate ("2023/08/28 17:00:56") into a PDF date
    string ("D:20230828170056"), or "" if it's missing or unparseable."""
    digits = re.sub(r"\D", "", publish_date or "")
    return f"D:{digits[:14]}" if len(digits) >= 14 else ""


def to_toc(menu, num_pages, level=1):
    toc = []
    for title, page, children in menu:
        if 1 <= page <= num_pages:
            toc.append([level, title, page])
            toc.extend(to_toc(children, num_pages, level + 1))
    return toc


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Download a Kawasaki interactive owner's manual "
                    "(https://pws.ktivs.net/dispeBook?file=...&lang_code=...) "
                    "page by page and save it as a single, text-searchable PDF.")
    ap.add_argument("url", help="Manual viewer URL, e.g. "
                    "'https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN' (quote it!)")
    ap.add_argument("-o", "--output", help="Output PDF path "
                    "(default: Kawasaki_manual_<file>_<lang>.pdf in the current directory)")
    ap.add_argument("-s", "--scale", default="max",
                    help="Page image resolution to download: 1, 2, 4, ... or 'max' "
                         "(default: max, the highest zoom level the viewer offers). "
                         "For the KX450 manual, 1x = 900x635 px per page, "
                         "2x = 1800x1270 px (~50 MB), 4x = 3600x2540 px (~117.2 MB)")
    ap.add_argument("--no-text", action="store_true",
                    help="Do not add the invisible, searchable text layer (images only)")
    ap.add_argument("--delay", type=float, default=0.5,
                    help="Minimum seconds between HTTP requests (default: 0.5)")
    ap.add_argument("--retries", type=int, default=5, help="Retries per request (default: 5)")
    ap.add_argument("--page-width-mm", type=float, default=DEFAULT_PAGE_WIDTH_MM,
                    help="Physical PDF page width in mm (default: 210, i.e. A5 landscape)")
    ap.add_argument("--cache-dir", metavar="DIR",
                    help="Save downloaded page images and text files here, and reuse them "
                         "on later runs instead of downloading them again")
    args = ap.parse_args(argv)

    fetcher = Fetcher(delay=args.delay, retries=args.retries)

    log(f"Opening viewer: {args.url}")
    base = find_book_base_url(fetcher, args.url)
    referer = base + "index.html"
    log(f"eBook folder:   {base}")

    book = parse_book_xml(fetcher.get(base + "book.xml", referer=referer).content)
    try:
        menu = parse_menu_xml(fetcher.get(base + "menu.xml", referer=referer).content)
    except Exception as e:  # The table of contents is optional.
        log(f"Note: no table of contents (menu.xml): {e}")
        menu = []

    max_mag = max(1, book["max_mag"])
    if args.scale == "max":
        scale = max_mag
    else:
        scale = int(args.scale)
        if scale > max_mag:
            log(f"Warning: requested scale {scale}x is above the viewer's max ({max_mag}x); "
                f"using {max_mag}x.")
            scale = max_mag
    # The viewer's zoom levels are powers of two.
    if scale < 1 or scale & (scale - 1):
        raise SystemExit(f"--scale must be a power of two (1, 2, 4, ...), not {scale}")

    n = len(book["page_ids"])
    pw, ph = book["page_width"] or 900, book["page_height"] or 635
    log(f"Title: {book['title']}  |  pages: {n}  |  resolution: {scale}x "
        f"({pw * scale} x {ph * scale} px)  |  text layer: {'no' if args.no_text else 'yes'}")

    output = Path(args.output or default_output_name(args.url, book["title"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    cache = Path(args.cache_dir) if args.cache_dir else None

    def fetch_cached(url, rel):
        if cache:
            f = cache / rel
            if f.is_file() and f.stat().st_size > 0:
                return f.read_bytes()
        data = fetcher.get(url, referer=referer).content
        if cache:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
        return data

    # PDF page size in points; the viewer's 1x page coordinates map onto it.
    page_w = args.page_width_mm / 25.4 * 72
    page_h = page_w * ph / pw
    coord_scale = page_w / pw

    doc = pymupdf.open()
    # Hash of everything that goes into the PDF; used for a deterministic
    # PDF /ID, so rebuilding the same manual gives a byte-identical file.
    content_hash = hashlib.sha256()
    content_hash.update(f"{args.url}|{book['title']}|{scale}|{args.no_text}|"
                        f"{args.page_width_mm}".encode())
    t0 = time.monotonic()
    words_total = 0
    for i, page_id in enumerate(book["page_ids"], start=1):
        img = fetch_cached(page_image_url(base, page_id, scale), f"x{scale}/{page_id}.jpg")
        content_hash.update(hashlib.sha256(img).digest())
        if not img.startswith(b"\xff\xd8"):
            raise RuntimeError(f"Page {i} ({page_id}) is not a JPEG image.")
        page = doc.new_page(width=page_w, height=page_h)
        # The JPEG is embedded as-is (no re-compression).
        page.insert_image(page.rect, stream=img)
        n_words = 0
        if not args.no_text:
            try:
                xml = fetch_cached(f"{base}page{page_id}/textpoint.xml", f"text/{page_id}.xml")
                content_hash.update(hashlib.sha256(xml).digest())
                words = parse_textpoint_xml(xml)
                add_invisible_text(page, words, coord_scale)
                n_words = len(words)
                words_total += n_words
            except Exception as e:
                log(f"  Note: no text layer for page {i}: {e}")
        elapsed = time.monotonic() - t0
        eta = elapsed / i * (n - i)
        log(f"  [{i:>4}/{n}] page {page_id}  {len(img) / 1024:7.0f} KiB  "
            f"{n_words:4d} words   ETA {eta:5.0f} s")

    log("Writing PDF...")
    toc = to_toc(menu, len(doc))
    if toc:
        doc.set_toc(toc)
    # Deterministic output: no run-time timestamps (the dates come from the
    # manual's own publish date in book.xml), a producer string without a
    # version number, and a /ID derived from the content instead of a random one.
    pdf_date = pdf_date_from_publish_date(book["publish_date"])
    doc.set_metadata({
        "title": book["title"],
        "author": "Kawasaki",
        "subject": f"Downloaded from {args.url}",
        "creator": "kawasaki_manual_downloader.py (https://github.com/ElectricRCAircraftGuy/Kawasaki)",
        "producer": "PyMuPDF",
        "creationDate": pdf_date,
        "modDate": pdf_date,
    })
    if toc:
        doc.set_pagemode("UseOutlines")
    pdf_id = content_hash.hexdigest()[:32].upper()
    doc.xref_set_key(-1, "ID", f"[<{pdf_id}><{pdf_id}>]")
    doc.save(output, garbage=3, deflate=True, no_new_id=True)
    doc.close()

    log(f"Done: {output}  ({n} pages, {words_total} words of text, "
        f"{output.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
