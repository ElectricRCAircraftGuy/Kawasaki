# Manuals made by the Copilot implementation

This folder is for files made by [`copilot_implementation/kawasaki_downloader.py`](../../copilot_implementation/kawasaki_downloader.py) (from PR #1), kept apart from the root implementation's output in [`../kawasaki_manual_downloader/`](../kawasaki_manual_downloader/).

**There is no PDF here, because the Copilot implementation produced no output for the KX450 manual.** Results of the test runs on 2026-10-20 (Chrome 155, selenium 4.51.0):

| Command (run from the repo root, in a venv with `copilot_implementation/requirements.txt`) | Result |
|---|---|
| `python copilot_implementation/kawasaki_downloader.py "https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN" -o /tmp/copilot_run2 -m 2` | 407 s, exit code 0, logged "Processed 2 pages", but **0 images** saved |
| `python copilot_implementation/kawasaki_downloader.py "https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN" -m 1` (default output folder) | 207.6 s, exit code 0, `copilot_implementation/output/` created, **0 images** saved |
| the same URL with default settings (`-m 100`) | stopped after about 4 minutes, **0 images** saved. A full run was not measured |

Also, this implementation saves page images only and never makes a PDF. So even a working run would need a separate step to turn the images into a PDF. The known limitations are described in [`copilot_implementation/README.md`](../../copilot_implementation/README.md).

## Copyright

Any manual pages or PDFs placed in this folder are **copyrighted by Kawasaki** ("© 2023 Kawasaki Motors, Ltd." for the KX450 manual) and are **NOT** covered by this repository's [LICENSE](../../LICENSE). All rights belong to their copyright holder.
