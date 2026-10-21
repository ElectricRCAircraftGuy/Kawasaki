#!/usr/bin/env bash
#
# Check every PDF in manuals/ against the version committed in git (HEAD by
# default) and say whether it's NEW, CHANGED, or UNCHANGED, by content (pages,
# images, text, bookmarks; see pdf_diff.py), not by bytes.
#
# Split PDFs (file.pdf.part_000, ...) are compared as a whole. If only the
# parts are on disk, the parts are joined into a temp file first.
# Runs fully offline (local files and git objects only).
#
# Usage: ./check_pdfs_changed.sh [-v] [REV] [DIR]
#   REV   git revision to compare against (default: HEAD)
#   DIR   folder to check (default: manuals/ next to this script)
#   -v    also print pdf_diff.py's details for changed files
#
# Exit code: 0 if every PDF is unchanged, 1 if any is new or changed, 2 on error.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
PDF_DIFF="$SCRIPT_DIR/pdf_diff.py"

verbose=0
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    sed -n '3,19p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
fi
if [[ "${1:-}" == "-v" ]]; then
    verbose=1
    shift
fi
rev="${1:-HEAD}"
dir="${2:-$SCRIPT_DIR/manuals}"

# Collect each PDF once: whole files, plus split sets (by their base name).
declare -A seen=()
pdfs=()
shopt -s nullglob
for f in "$dir"/*.pdf "$dir"/*.pdf.part_000; do
    base="${f%.part_000}"
    [[ -n "${seen[$base]:-}" ]] && continue
    seen[$base]=1
    pdfs+=("$base")
done
shopt -u nullglob

if (( ${#pdfs[@]} == 0 )); then
    echo "No PDFs found in '$dir'."
    exit 0
fi

any_changed=0
any_error=0
for pdf in "${pdfs[@]}"; do
    rel="${pdf#"$SCRIPT_DIR"/}"
    how="file"
    [[ -f "$pdf" ]] || how="parts"
    rc=0
    out="$("$PYTHON" "$PDF_DIFF" "$pdf" --against-git "$rev" 2>&1)" || rc=$?
    case "$rc" in
        0) printf '%-10s %s\n' "UNCHANGED" "$rel" ;;
        1) printf '%-10s %s\n' "CHANGED" "$rel"; any_changed=1
           if (( verbose )); then sed 's/^/    /' <<< "$out"; fi ;;
        3) printf '%-10s %s\n' "NEW" "$rel  (not in $rev)"; any_changed=1 ;;
        *) printf '%-10s %s\n' "ERROR" "$rel"; sed 's/^/    /' <<< "$out"; any_error=1 ;;
    esac
    [[ "$how" == "parts" ]] && echo "           (checked the split parts on disk; whole file not present)"
done

(( any_error )) && exit 2
(( any_changed )) && exit 1
exit 0
