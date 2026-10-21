#!/usr/bin/env bash
#
# Split large files into parts small enough for GitHub (< 100 MB per file),
# and join them back together, verifying the result with a SHA-256 checksum.
#
# Parts are named <file>.part_000, <file>.part_001, ... and the checksum of the
# whole file is stored in <file>.sha256.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PART_SIZE="45M"
DEFAULT_DIR="$SCRIPT_DIR/manuals"
PYTHON="${PYTHON:-python3}"
PDF_DIFF="$SCRIPT_DIR/pdf_diff.py"

usage() {
    cat <<USAGE
Usage:
  $(basename "$0") split [--force] <file>
                                   Split <file> into <file>.part_000, .part_001, ...
                                   (${PART_SIZE} each) and write <file>.sha256.
                                   Skips (exit 0) if <file> has the same content as
                                   the existing parts (byte-identical, or same
                                   pages/images/text/bookmarks per pdf_diff.py).
                                   --force splits anyway.
  $(basename "$0") join <file>     Join <file>.part_* back into <file> and verify
                                   it against <file>.sha256.
  $(basename "$0") join            Join every split file found in manuals/.
  $(basename "$0") -h | --help     Show this help.

Examples:
  # After 'git clone' or 'git pull', rebuild the full-resolution (4x) PDF:
  ./split_join_large_files.sh join manuals/KX450_owners_manual_99803-0401_EN_4x.pdf

  # After regenerating a large PDF, split it so it can be committed:
  ./split_join_large_files.sh split manuals/KX450_owners_manual_99803-0401_EN_4x.pdf
USAGE
}

# Return 0 if <file> has the same content as its existing split parts.
same_as_existing_parts() {
    local file="$1"
    [[ -f "$file.part_000" ]] || return 1
    # Fast path: whole-file checksum matches the stored one.
    if [[ -f "$file.sha256" ]] && \
       [[ "$(sha256sum -- "$file" | cut -d' ' -f1)" == "$(cut -d' ' -f1 < "$file.sha256")" ]]; then
        echo "'$file' is byte-identical to its existing parts (checksum matches)."
        return 0
    fi
    # Content-level comparison for PDFs (ignores dates, /ID, etc.).
    if [[ "$file" == *.pdf && -f "$PDF_DIFF" ]]; then
        local rc=0
        "$PYTHON" "$PDF_DIFF" "$file" "$file.part_000" || rc=$?
        case "$rc" in
            0) return 0 ;;
            1) return 1 ;;
            *) echo "Warning: pdf_diff.py failed (exit $rc); treating '$file' as changed." >&2
               return 1 ;;
        esac
    fi
    return 1
}

split_file() {
    local force=0
    if [[ "${1:-}" == "--force" ]]; then
        force=1
        shift
    fi
    local file="${1:-}"
    [[ -n "$file" ]] || { usage >&2; exit 1; }
    [[ -f "$file" ]] || { echo "Error: file not found: $file" >&2; exit 1; }
    if (( ! force )) && same_as_existing_parts "$file"; then
        echo "Skipping split: '$file' has the same content as its existing parts," \
             "so there is nothing new to commit. Use 'split --force' to split anyway."
        return 0
    fi
    local dir base
    dir="$(dirname "$file")"
    base="$(basename "$file")"
    (
        cd "$dir"
        rm -f -- "$base".part_*
        split -b "$PART_SIZE" -d -a 3 -- "$base" "$base.part_"
        sha256sum -- "$base" > "$base.sha256"
    )
    echo "Split '$file' into:"
    ls -l -- "$file".part_*
    echo "Checksum written to '$file.sha256'."
}

join_file() {
    local file="$1"
    local dir base
    dir="$(dirname "$file")"
    base="$(basename "$file")"
    shopt -s nullglob
    local parts=("$dir/$base".part_[0-9][0-9][0-9])
    shopt -u nullglob
    if (( ${#parts[@]} == 0 )); then
        echo "Error: no parts found matching '$file.part_NNN'" >&2
        exit 1
    fi
    # Glob expansion is sorted, and the numeric suffixes have a fixed width, so
    # the parts are joined in the right order.
    cat -- "${parts[@]}" > "$file.tmp"
    mv -f -- "$file.tmp" "$file"
    echo "Joined ${#parts[@]} parts into '$file'."
    if [[ -f "$file.sha256" ]]; then
        (cd "$dir" && sha256sum -c -- "$base.sha256")
    else
        echo "Warning: '$file.sha256' not found; cannot verify the joined file." >&2
    fi
}

join_all() {
    shopt -s nullglob
    local first_parts=("$DEFAULT_DIR"/*.part_000)
    shopt -u nullglob
    if (( ${#first_parts[@]} == 0 )); then
        echo "No split files found in '$DEFAULT_DIR'."
        return 0
    fi
    local p
    for p in "${first_parts[@]}"; do
        join_file "${p%.part_000}"
    done
}

main() {
    if (( $# == 0 )); then
        usage
        exit 1
    fi
    case "$1" in
        -h|--help)
            usage
            ;;
        split)
            shift
            (( $# == 1 || $# == 2 )) || { usage >&2; exit 1; }
            split_file "$@"
            ;;
        join)
            if (( $# == 1 )); then
                join_all
            elif (( $# == 2 )); then
                join_file "$2"
            else
                usage >&2
                exit 1
            fi
            ;;
        *)
            echo "Error: unknown command '$1'" >&2
            usage >&2
            exit 1
            ;;
    esac
}

main "$@"
