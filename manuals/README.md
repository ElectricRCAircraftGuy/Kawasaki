# Manuals

Each subfolder holds the output of one implementation, so it's clear which program made which file, and neither implementation overwrites the other's output:

| Folder | Made by | Contents |
|---|---|---|
| [`kawasaki_manual_downloader/`](kawasaki_manual_downloader/) | the root implementation, [`kawasaki_manual_downloader.py`](../kawasaki_manual_downloader.py) | KX450 owner's manual: 2x PDF (49.9 MB) plus the 4x PDF (117.2 MB) as split parts + `.sha256` |
| [`copilot_implementation/`](copilot_implementation/) | the Copilot implementation, [`copilot_implementation/kawasaki_downloader.py`](../copilot_implementation/kawasaki_downloader.py) | no PDF: on the KX450 manual it downloaded 0 pages (see that folder's README) |

Each subfolder's README gives the exact command and settings that produced its files. To rebuild split PDFs after `git clone` / `git pull`, run `./split_join_large_files.sh join` from the repo root.

## Copyright

All manuals in this folder and its subfolders (PDF files, split `.part_NNN` files, any PDF recombined from them, and any page images) are **copyrighted by Kawasaki**. The KX450 manual says "© 2023 Kawasaki Motors, Ltd." (Kawasaki Motors, Ltd. is part of the Kawasaki Heavy Industries group). All rights belong to their copyright holder. They are **NOT** covered by this repository's [LICENSE](../LICENSE). That license applies only to the rest of the repo (the code and documentation). This project is not affiliated with, endorsed by, or sponsored by Kawasaki.
