# Manuals made by `kawasaki_manual_downloader.py` (the root implementation)

These files were made by [`kawasaki_manual_downloader.py`](../../kawasaki_manual_downloader.py) in the repo root, from the free, public online manual that Kawasaki publishes at <https://pws.ktivs.net>.

| File(s) | What it is | Exact command (run from the repo root) |
|---|---|---|
| `KX450_owners_manual_99803-0401_EN.pdf` | KX450 Owner's Manual 99803-0401, English. 212 pages, 2x resolution (1800 x 1270 px per page), 49,884,379 bytes (49.9 MB). Has a searchable/selectable invisible text layer and bookmarks. | `./kawasaki_manual_downloader.py "https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN" -s 2 -o manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN.pdf` |
| `KX450_owners_manual_99803-0401_EN_4x.pdf.part_000`, `.part_001`, `.part_002` + `.sha256` | The same manual at full 4x resolution (3600 x 2540 px per page), 117,195,430 bytes (117.2 MB), split into 45 MiB parts because GitHub won't accept files over 100 MB. | `./kawasaki_manual_downloader.py "https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN" -o manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN_4x.pdf` then `./split_join_large_files.sh split manuals/kawasaki_manual_downloader/KX450_owners_manual_99803-0401_EN_4x.pdf` |

Both use the default settings otherwise: text layer on, 210 mm page width (A5 landscape), and 0.5 s minimum delay between requests. The output is deterministic: rebuilding gives byte-identical files.

To recombine the 4x PDF after `git clone` / `git pull`, run this from the repo root:

```bash
./split_join_large_files.sh join
```

## Copyright

These manuals, and the split `.part_NNN` files and any PDF recombined from them, are **copyrighted by Kawasaki**. The KX450 manual says "© 2023 Kawasaki Motors, Ltd." (Kawasaki Motors, Ltd. is part of the Kawasaki Heavy Industries group). All rights belong to their copyright holder. They are **NOT** covered by this repository's [LICENSE](../../LICENSE). That license applies only to the code and documentation in this repo. This project is not affiliated with, endorsed by, or sponsored by Kawasaki.
