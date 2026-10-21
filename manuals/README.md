# Copyright notice for this folder

The manuals in this folder (the PDF files, the split `.part_NNN` files of the large PDF, and any PDF recombined from them) are **copyrighted by Kawasaki**. The KX450 manual says "© 2023 Kawasaki Motors, Ltd." (Kawasaki Motors, Ltd. is part of the Kawasaki Heavy Industries group). All rights belong to their copyright holder.

They are **NOT** covered by this repository's [LICENSE](../LICENSE). That license applies only to the rest of the repo (the code and documentation), not to anything in this folder.

The PDFs were made with [`kawasaki_manual_downloader.py`](../kawasaki_manual_downloader.py) from the free, public online versions Kawasaki publishes at <https://pws.ktivs.net>:

- `KX450_owners_manual_99803-0401_EN.pdf`: KX450 Owner's Manual, part number 99803-0401, English. Source: <https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN>. It has 212 pages at 2x resolution (1800 x 1270 px per page), with an invisible text layer for search/selection and bookmarks from the table of contents.
- `KX450_owners_manual_99803-0401_EN_4x.pdf.part_000`, `.part_001`, `.part_002` + `.sha256`: the same manual at full 4x resolution (3600 x 2540 px per page, 117.2 MB, 212 pages). It's split into parts because GitHub won't accept files over 100 MB. To recombine it, run this from the repo root:

  ```bash
  ./split_join_large_files.sh join manuals/KX450_owners_manual_99803-0401_EN_4x.pdf
  ```

  Or by hand, from this folder: `cat KX450_owners_manual_99803-0401_EN_4x.pdf.part_* > KX450_owners_manual_99803-0401_EN_4x.pdf && sha256sum -c KX450_owners_manual_99803-0401_EN_4x.pdf.sha256`

This project is not affiliated with, endorsed by, or sponsored by Kawasaki.
