# Verification record for the Copilot (backup) implementation

[`copilot_implementation/kawasaki_downloader.py`](../../copilot_implementation/kawasaki_downloader.py) is this repo's **backup and cross-check implementation**: a browser-based fallback (Selenium + headless Chrome) for the case where the viewer's internal file layout changes and the primary tool ([`kawasaki_manual_downloader.py`](../../kawasaki_manual_downloader.py)) stops working. It is slower and more fragile, and it is not the primary tool.

**No PDF from it is committed here.** Its pages turned out to be byte-identical to the primary tool's 4x pages, so its PDF would only duplicate [`../kawasaki_manual_downloader/`](../kawasaki_manual_downloader/) without the text layer and bookmarks. This folder only records the verification. PDFs in this folder are listed in `.gitignore`.

## Verification (2026-10-20)

This is a short record. The full description of the fixes, the browser-hang fix, the full run, and how the byte-identity check was done is in **[Fixes and test results (2026-10-20)](../../copilot_implementation/README.md#fixes-and-test-results-2026-10-20)** in the implementation's README.

Command, run from the repo root in a venv with `copilot_implementation/requirements.txt` (Chrome 155, selenium 4.51.0), default settings:

```bash
python copilot_implementation/kawasaki_downloader.py "https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN"
```

| | Result |
|---|---|
| Exit code | 0 |
| Runtime | 1043.3 s (17.4 min), including 4 planned browser restarts (every 25 spreads) and 0 restarts after errors |
| Pages | **212 of 212**, in order (the viewer's last page number was 212) |
| Resolution | 4x, 3600 x 2540 px JPEG per page (the viewer's highest zoom) |
| Output | `copilot_implementation/output/page_0001.jpg` ... `page_0212.jpg` (110,403,121 bytes in total), and `manual.pdf` (img2pdf, 110,509,380 bytes = 110.5 MB, 212 pages, no text layer, no bookmarks) |
| **Page images vs the primary tool's 4x PDF** | **All 212 page images are byte-identical** (same SHA-256) to the JPEGs embedded in `../kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN_4x.pdf` |
| `pdf_diff.py` (primary 4x vs Copilot PDF) | different only in page **size** (ours: 210 mm wide pages; theirs: 3600 x 2540 pt) and **text** (ours has the invisible text layer; theirs has none). No page reported an image difference |

The per-page hashes are in [`KX450_99803-0401_EN_4x_page_images.sha256`](KX450_99803-0401_EN_4x_page_images.sha256) (212 lines, `sha256sum` format, file names `page_0001.jpg` ...). The SHA-256 of that list file is `a904048cf73d37740390f94e6fe8137dd335780bc856281c3a57481ea15e3de5`.

## Regenerate and re-check locally

```bash
# 1. Regenerate the pages and PDF (about 17 minutes) -> copilot_implementation/output/
python copilot_implementation/kawasaki_downloader.py "https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN"

# 2. Check the new page images against the recorded hashes
(cd copilot_implementation/output && sha256sum -c ../../manuals/copilot_implementation/KX450_99803-0401_EN_4x_page_images.sha256)

# 3. Check the recorded hashes against the primary tool's 4x PDF (pdfimages is in poppler-utils;
#    -j writes the embedded JPEGs unchanged)
./split_join_large_files.sh join
mkdir -p /tmp/ours_4x && pdfimages -j manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN_4x.pdf /tmp/ours_4x/p
(cd /tmp/ours_4x && sha256sum p-*.jpg | awk '{print $1}') | diff - <(awk '{print $1}' manuals/copilot_implementation/KX450_99803-0401_EN_4x_page_images.sha256) && echo "all pages identical"

# 4. Optional: content-level comparison of the two PDFs
./pdf_diff.py manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN_4x.pdf copilot_implementation/output/manual.pdf
```

## Copyright

The manual pages, page images, and any PDFs made from them are **copyrighted by Kawasaki** ("© 2023 Kawasaki Motors, Ltd." for the KX450 manual) and are **NOT** covered by this repository's [LICENSE](../../LICENSE). All rights belong to their copyright holder. The hash list in this folder contains no manual content.
