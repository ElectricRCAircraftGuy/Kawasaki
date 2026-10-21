#!/usr/bin/env python3
"""
Compare two PDFs by *content*, not bytes.

PDF files can differ byte-for-byte while showing exactly the same thing (for
example a different creation date or /ID). This tool compares:
  - the page count,
  - each page's embedded images (SHA-256 of the raw image streams),
  - each page's extracted text,
  - each page's size,
  - the outline (bookmarks).

It works fully offline, on local files and git objects only.

Each PDF argument can be:
  path/to/file.pdf          a normal PDF file
  path/to/file.pdf.part_000 a split set made by split_join_large_files.sh
  path/to/file.pdf.sha256   (also a split set; or pass file.pdf when only the
                            parts exist on disk). The parts are joined into a
                            temporary file.
  REV:path/to/file.pdf      the version committed in git at REV (e.g.
                            HEAD:manuals/x.pdf). ":path" means the staged
                            (index) version. If REV has no file at that path
                            but has a split set (path.part_000, ...), those
                            parts are joined.

Exit codes:
  0  same content
  1  different content
  2  error
  3  no committed/staged version found (only with git REV:path inputs;
     "new file")

Examples:
  ./pdf_diff.py a.pdf b.pdf
  ./pdf_diff.py manuals/x.pdf --against-git          # vs HEAD
  ./pdf_diff.py manuals/x.pdf --against-git HEAD~1
  ./pdf_diff.py new.pdf manuals/x_4x.pdf.part_000    # vs a split set
"""

import argparse
import difflib
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

EXIT_SAME, EXIT_DIFFERENT, EXIT_ERROR, EXIT_NOT_FOUND = 0, 1, 2, 3
PART_RE = re.compile(r"^(?P<base>.+)\.part_\d{3}$")


class NotFound(Exception):
    pass


# ---------------------------------------------------------------- inputs

def git(*args, cwd=None, binary=False):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True)
    if r.returncode != 0:
        raise subprocess.CalledProcessError(r.returncode, ["git", *args], r.stdout, r.stderr)
    return r.stdout if binary else r.stdout.decode()


def repo_root(start="."):
    return Path(git("rev-parse", "--show-toplevel", cwd=start).strip())


def repo_relpath(path):
    """Path of `path` relative to the git repo root, with forward slashes."""
    p = Path(path).resolve()
    root = repo_root(p.parent if p.parent.exists() else ".")
    return root, p.relative_to(root).as_posix()


def git_list(root, rev, directory):
    """Files under `directory` in `rev` ("" = index)."""
    if rev == "":
        out = git("ls-files", "--cached", "--", directory or ".", cwd=root)
    else:
        out = git("ls-tree", "-r", "--name-only", rev, "--", directory or ".", cwd=root)
    return [line for line in out.splitlines() if line]


def git_blob(root, rev, relpath):
    return git("show", f"{rev}:{relpath}", cwd=root, binary=True)


def load_from_git(rev, path, tmpdir):
    """Write the REV version of `path` (whole file or joined split set) to a
    temp file and return its path. Raises NotFound."""
    root, rel = repo_relpath(path)
    names = set(git_list(root, rev, os.path.dirname(rel)))
    where = "the index" if rev == "" else rev
    out = Path(tmpdir) / (f"git_{(rev or 'INDEX').replace('/', '_')}_" + os.path.basename(rel))
    if rel in names:
        out.write_bytes(git_blob(root, rev, rel))
        return out
    parts = sorted(n for n in names if PART_RE.match(n) and PART_RE.match(n)["base"] == rel)
    if not parts:
        raise NotFound(f"{rel} (or a split set of it) is not in {where}")
    with open(out, "wb") as f:
        for part in parts:
            f.write(git_blob(root, rev, part))
    return out


def join_parts(base, tmpdir):
    parts = sorted(Path(base).parent.glob(Path(base).name + ".part_[0-9][0-9][0-9]"))
    if not parts:
        raise FileNotFoundError(f"{base}: no such file, and no split parts ({base}.part_NNN) found")
    out = Path(tmpdir) / ("joined_" + Path(base).name)
    with open(out, "wb") as f:
        for part in parts:
            with open(part, "rb") as pf:
                while chunk := pf.read(1 << 20):
                    f.write(chunk)
    return out


def resolve(spec, tmpdir):
    """Turn an input spec into a local PDF path (maybe a temp file)."""
    # git REV:path ("" REV = index). Avoid treating Windows drive letters
    # like C:\\ as revs.
    if ":" in spec and not os.path.exists(spec) and not re.match(r"^[A-Za-z]:[\\/]", spec):
        rev, path = spec.split(":", 1)
        return load_from_git(rev, path, tmpdir)
    m = PART_RE.match(spec)
    if m:
        return join_parts(m["base"], tmpdir)
    if spec.endswith(".sha256"):
        return join_parts(spec[: -len(".sha256")], tmpdir)
    if os.path.isfile(spec):
        return Path(spec)
    return join_parts(spec, tmpdir)  # only the parts exist on disk


# ---------------------------------------------------------------- compare

def page_signatures(pdf_path):
    import pymupdf  # imported here so --help works without PyMuPDF
    doc = pymupdf.open(pdf_path)
    pages = []
    for page in doc:
        h = hashlib.sha256()
        for img in page.get_images(full=True):
            h.update(hashlib.sha256(doc.xref_stream_raw(img[0]) or b"").digest())
        text = page.get_text()
        r = page.rect
        pages.append({
            "images": h.hexdigest(),
            "text": hashlib.sha256(text.encode()).hexdigest(),
            "size": (round(r.width, 2), round(r.height, 2)),
        })
    toc = doc.get_toc(simple=True)
    doc.close()
    return pages, toc


def ranges(nums):
    """[1,2,3,7,9,10] -> '1-3, 7, 9-10'"""
    out, start, prev = [], None, None
    for n in nums:
        if start is None:
            start = prev = n
        elif n == prev + 1:
            prev = n
        else:
            out.append(f"{start}-{prev}" if start != prev else f"{start}")
            start = prev = n
    if start is not None:
        out.append(f"{start}-{prev}" if start != prev else f"{start}")
    return ", ".join(out)


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def compare(a_path, b_path, a_name, b_name, quiet=False):
    # Fast path: byte-identical files have identical content.
    if os.path.getsize(a_path) == os.path.getsize(b_path) and file_sha256(a_path) == file_sha256(b_path):
        if not quiet:
            print(f"SAME content (byte-identical): {a_name} == {b_name}")
        return EXIT_SAME
    pa, toc_a = page_signatures(a_path)
    pb, toc_b = page_signatures(b_path)
    lines = []
    if len(pa) != len(pb):
        lines.append(f"page count: {len(pa)} vs {len(pb)}")
    # Align pages (so one inserted/removed page doesn't flag every later page).
    key = lambda p: (p["images"], p["text"], p["size"])  # noqa: E731
    sm = difflib.SequenceMatcher(None, [key(p) for p in pa], [key(p) for p in pb], autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "delete":
            lines.append(f"pages only in A: {ranges(range(i1 + 1, i2 + 1))}")
        elif tag == "insert":
            lines.append(f"pages only in B: {ranges(range(j1 + 1, j2 + 1))}")
        else:  # replace
            for k in range(max(i2 - i1, j2 - j1)):
                i, j = i1 + k, j1 + k
                if i < i2 and j < j2:
                    what = [n for n in ("images", "text", "size") if pa[i][n] != pb[j][n]]
                    lines.append(f"page A{i + 1} vs B{j + 1}: {', '.join(what)} differ")
                elif i < i2:
                    lines.append(f"page only in A: {i + 1}")
                else:
                    lines.append(f"page only in B: {j + 1}")
    if toc_a != toc_b:
        lines.append(f"outline/bookmarks differ ({len(toc_a)} vs {len(toc_b)} entries; "
                     f"titles, levels, or target pages)")

    if not lines:
        if not quiet:
            print(f"SAME content: {a_name} == {b_name} ({len(pa)} pages)")
        return EXIT_SAME
    if not quiet:
        print(f"DIFFERENT content: A={a_name}  B={b_name}")
        max_lines = 40
        for line in lines[:max_lines]:
            print("  " + line)
        if len(lines) > max_lines:
            print(f"  ... and {len(lines) - max_lines} more differences")
    return EXIT_DIFFERENT


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Compare two PDFs by content (pages, images, text, bookmarks). "
                    "Exit 0 = same, 1 = different, 2 = error, 3 = git version not found.",
        epilog=__doc__[__doc__.index("Each PDF argument"):],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("a", help="First PDF (file, split set, or REV:path)")
    ap.add_argument("b", nargs="?", help="Second PDF (file, split set, or REV:path)")
    ap.add_argument("--against-git", nargs="?", const="HEAD", metavar="REV",
                    help="Compare A with the version of the same path committed at REV "
                         "(default HEAD; use '' for the index). Split sets are joined.")
    ap.add_argument("-q", "--quiet", action="store_true", help="No output; exit code only")
    args = ap.parse_args(argv)

    if (args.b is None) == (args.against_git is None):
        ap.error("give either a second PDF or --against-git [REV]")
    b_spec = args.b if args.b is not None else f"{args.against_git}:{args.a}"

    try:
        with tempfile.TemporaryDirectory(prefix="pdf_diff_") as tmp:
            try:
                a_path = resolve(args.a, tmp)
                b_path = resolve(b_spec, tmp)
            except NotFound as e:
                if not args.quiet:
                    print(f"NOT FOUND: {e}")
                return EXIT_NOT_FOUND
            return compare(a_path, b_path, args.a, b_spec, args.quiet)
    except subprocess.CalledProcessError as e:
        print(f"Error: {' '.join(e.cmd)}: {e.stderr.decode(errors='replace').strip()}", file=sys.stderr)
    except Exception as e:  # noqa: BLE001
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
    return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
