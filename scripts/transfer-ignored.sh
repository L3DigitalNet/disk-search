#!/usr/bin/env bash
#
# transfer-ignored.sh — sync purposely-gitignored, local-only dev files between
# workstations via a shared NAS folder, without ever putting them on the public
# GitHub repo.
#
# WHY THIS EXISTS
#   A handful of files are intentionally kept out of the public repo (session
#   handoff notes, the local agent guides, editor config, etc.) but still need to
#   follow the developer from one workstation to another. Git can't carry them
#   (that's the whole point — they're gitignored), so this script copies them
#   through /mnt/nas/dev/transfer/hw-radar, preserving the repo-relative layout.
#
# SINGLE SOURCE OF TRUTH FOR *WHAT* GETS SYNCED
#   The manifest is NOT hardcoded here. It is read from the local repo's
#   .gitignore, from the block delimited by the markers below. To add/remove a
#   synced path, edit that .gitignore block — nothing in this script changes.
#     # >>> transfer-ignored manifest ... >>>
#     <one repo-relative path per line; trailing '/' allowed for directories>
#     # <<< transfer-ignored manifest <<<
#
# DIRECTIONS
#   --up    : local repo  ->  NAS   (publish this workstation's local-only files)
#   --down  : NAS         ->  local repo   (pull them onto this workstation)
#
# CONFLICT / IDEMPOTENCY RULES (per file)
#   * destination missing            -> copy
#   * byte-identical to destination  -> skip (never rewrite)
#   * source newer than destination  -> copy (the normal "I edited it" update)
#   * DESTINATION NEWER than source  -> STOP and ask: overwrite or skip
#     (this guards against clobbering a fresh copy pushed from another
#     workstation with a stale one).
#
#   Timestamps are the load-bearing signal for "newer", so copies use
#   `cp --preserve=timestamps`: a synced file keeps the source's mtime, which
#   makes the next run see it as identical instead of spuriously newer. (Content
#   is compared first, so mtime granularity on the NAS never causes false skips.)
#
# NOT A MIRROR (copy-only, no prune): a file deleted on one side is NOT deleted
#   on the other. If you remove a local-only file and then --down, the NAS copy
#   is restored. Delete on both sides (or from the NAS) to retire something.
#
# REQUIRES GNU coreutils + bash 4+ (mapfile, stat -c, date -d, cp
#   --preserve=timestamps, find -print0 | sort -z). Fine on the Fedora dev boxes
#   and the Debian 13 target; would need adjustment on macOS/BusyBox.

set -euo pipefail

# --- configuration (env-overridable, mainly for testing) --------------------
# Local repos live at the same path on every workstation, by convention.
LOCAL_REPO="${HW_RADAR_LOCAL:-$HOME/projects/hw-radar}"
NAS_DIR="${HW_RADAR_NAS:-/mnt/nas/dev/transfer/hw-radar}"
GITIGNORE="$LOCAL_REPO/.gitignore"

# Markers that bound the manifest block inside .gitignore.
MANIFEST_BEGIN='# >>> transfer-ignored manifest'
MANIFEST_END='# <<< transfer-ignored manifest'

# --- output helpers ---------------------------------------------------------
if [[ -t 1 ]]; then
  c_red=$'\033[31m'; c_grn=$'\033[32m'; c_yel=$'\033[33m'; c_dim=$'\033[2m'; c_rst=$'\033[0m'
else
  c_red=''; c_grn=''; c_yel=''; c_dim=''; c_rst=''
fi
info()  { printf '%s\n' "$*"; }
warn()  { printf '%swarn:%s %s\n' "$c_yel" "$c_rst" "$*" >&2; }
die()   { printf '%serror:%s %s\n' "$c_red" "$c_rst" "$*" >&2; exit 1; }

usage() {
  cat <<EOF
Usage: ${0##*/} (--up | --down) [--dry-run] [-h|--help]

Sync purposely-gitignored local-only files between this workstation and the NAS.

  --up        copy from the local repo ($LOCAL_REPO)
              to the NAS folder ($NAS_DIR)
  --down      copy from the NAS folder to the local repo
  --dry-run   show what would happen; copy nothing, ask nothing
  -h, --help  show this help

The list of synced paths is read from the manifest block in:
  $GITIGNORE
(between "$MANIFEST_BEGIN ... >>>" and "$MANIFEST_END <<<").

On a per-file conflict where the destination is NEWER than the source, the
script stops and asks what to do (overwrite / skip; also overwrite-all /
skip-all / quit). Identical files are never rewritten.
EOF
}

# --- argument parsing -------------------------------------------------------
direction=""
dry_run=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --up)    [[ -n "$direction" ]] && die "choose only one of --up / --down"; direction="up" ;;
    --down)  [[ -n "$direction" ]] && die "choose only one of --up / --down"; direction="down" ;;
    --dry-run) dry_run=1 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die "unknown argument: $1" ;;
  esac
  shift
done
[[ -z "$direction" ]] && { usage >&2; die "one of --up / --down is required"; }

# --- preflight --------------------------------------------------------------
[[ -d "$LOCAL_REPO" ]]  || die "local repo not found: $LOCAL_REPO"
[[ -f "$GITIGNORE" ]]   || die "no .gitignore at: $GITIGNORE"
# If the NAS isn't mounted, its parent path won't exist — refuse rather than
# silently reading/writing an empty local directory under the mountpoint.
nas_parent="$(dirname "$NAS_DIR")"
[[ -d "$nas_parent" ]]  || die "NAS path unavailable: $nas_parent (is /mnt/nas mounted?)"

# Can we prompt? A conflict with no controlling terminal (cron/CI) must fall back
# to a safe skip rather than crash on a failed /dev/tty write.
have_tty=0
if [[ -e /dev/tty ]] && ( : >/dev/tty ) 2>/dev/null; then have_tty=1; fi

# --- read the manifest from .gitignore --------------------------------------
# Everything strictly between the two markers, minus blanks/comments, trimmed.
# BOTH markers must exist: without the end marker the block would run to EOF and
# silently swallow whatever .gitignore patterns follow it as transfer entries.
grep -qF "$MANIFEST_BEGIN" "$GITIGNORE" || die "manifest begin marker not found in $GITIGNORE"
grep -qF "$MANIFEST_END"   "$GITIGNORE" || die "manifest end marker not found in $GITIGNORE (block would run to EOF)"
mapfile -t MANIFEST < <(
  awk -v b="$MANIFEST_BEGIN" -v e="$MANIFEST_END" '
    index($0, b) == 1 { inblk = 1; next }
    index($0, e) == 1 { inblk = 0 }
    inblk {
      sub(/\r$/, "")                    # tolerate CRLF line endings
      sub(/#.*/, "")                    # strip inline comments (script-only; git takes them literally)
      gsub(/^[ \t]+|[ \t]+$/, "")       # trim
      if ($0 != "") print
    }
  ' "$GITIGNORE"
)
[[ ${#MANIFEST[@]} -gt 0 ]] || die "manifest block empty in $GITIGNORE"

# --- resolve direction ------------------------------------------------------
if [[ "$direction" == "up" ]]; then
  SRC_ROOT="$LOCAL_REPO"; DST_ROOT="$NAS_DIR"
else
  SRC_ROOT="$NAS_DIR";    DST_ROOT="$LOCAL_REPO"
fi
[[ -d "$SRC_ROOT" ]] || die "source root does not exist: $SRC_ROOT"

info "${c_dim}manifest (${#MANIFEST[@]} entries) from ${GITIGNORE#"$LOCAL_REPO"/}${c_rst}"
info "${c_dim}${direction^^}: $SRC_ROOT  ->  $DST_ROOT${c_rst}"
[[ $dry_run -eq 1 ]] && info "${c_yel}(dry run — no changes)${c_rst}"
info ""

# --- counters & conflict auto-mode ------------------------------------------
n_copied=0 n_updated=0 n_identical=0 n_skipped=0 n_missing=0 n_conflict=0 n_failed=0
auto=""   # "" | "overwrite-all" | "skip-all"

# Decide+act on one file. Args: absolute src, absolute dst, display rel path.
transfer_file() {
  local src="$1" dst="$2" rel="$3"

  # These are meant to be plain files. Refuse symlinks on either side: cp/stat/cmp
  # would dereference them and could read or clobber a target OUTSIDE the tree.
  if [[ -L "$src" || -L "$dst" ]]; then
    warn "symlink involved, skipping (not following): $rel"; (( ++n_skipped )); return
  fi

  if [[ ! -e "$dst" ]]; then
    if do_copy "$src" "$dst" "$rel" "new"; then (( ++n_copied )); else (( ++n_failed )); fi
    return
  fi

  # cmp exit: 0 identical, 1 differ, >1 real error (e.g. unreadable NAS file).
  # An error must NOT fall through to overwrite logic on an unverified comparison.
  local cmp_rc=0
  cmp -s "$src" "$dst" || cmp_rc=$?
  if (( cmp_rc == 0 )); then
    info "${c_dim}= identical  $rel${c_rst}"; (( ++n_identical )); return
  elif (( cmp_rc > 1 )); then
    warn "cannot compare (read error), skipping: $rel"; (( ++n_skipped )); return
  fi

  local src_m dst_m
  src_m="$(stat -c %Y "$src")"; dst_m="$(stat -c %Y "$dst")"
  # Overwrite only when the source is STRICTLY newer. Equal mtime + differing
  # content is ambiguous (same-second edit on two boxes, or coarse NAS mtime) —
  # treat it as a conflict rather than silently clobbering the destination.
  if (( dst_m >= src_m )); then
    (( ++n_conflict ))
    if [[ $dry_run -eq 1 ]]; then
      info "${c_yel}! would conflict${c_rst} $rel ${c_dim}(dest newer/equal — would ask)${c_rst}"
      return
    fi
    local choice
    case "$auto" in
      overwrite-all) choice="o" ;;
      skip-all)      choice="s" ;;
      *)
        if [[ $have_tty -eq 1 ]]; then
          ask_conflict "$rel" "$src_m" "$dst_m"; choice="$REPLY_CHOICE"
        else
          warn "conflict (dest newer/equal), no terminal to prompt — skipping: $rel"
          choice="s"
        fi
        ;;
    esac
    case "$choice" in
      o) if do_copy "$src" "$dst" "$rel" "overwrite (dest was newer)"; then (( ++n_updated )); else (( ++n_failed )); fi ;;
      s) info "${c_yel}~ skip       $rel${c_rst} ${c_dim}(dest newer)${c_rst}"; (( ++n_skipped )) ;;
    esac
    return
  fi

  # Source strictly newer: normal update.
  if do_copy "$src" "$dst" "$rel" "update"; then (( ++n_updated )); else (( ++n_failed )); fi
}

# Copy src -> dst, preserving timestamps. Returns non-zero on ANY failure so the
# caller does not count a failed copy as success. Writes to a temp file in the
# destination directory and atomically mv's it into place, so an interrupted or
# failed copy (common on a flaky NAS mount) cannot leave a truncated destination
# — the old file survives until the new one is complete. Honors dry-run.
do_copy() {
  local src="$1" dst="$2" rel="$3" why="$4" dstdir tmp
  if [[ $dry_run -eq 1 ]]; then
    info "${c_grn}+ would copy${c_rst} $rel ${c_dim}($why)${c_rst}"
    return 0
  fi
  dstdir="$(dirname "$dst")"
  mkdir -p "$dstdir"                              || { warn "mkdir failed: $rel"; return 1; }
  tmp="$(mktemp "$dstdir/.transfer.XXXXXX")"      || { warn "mktemp failed: $rel"; return 1; }
  if ! cp --preserve=timestamps "$src" "$tmp"; then
    rm -f "$tmp"; warn "copy failed: $rel"; return 1
  fi
  # Same-directory rename: atomic on the destination filesystem, and it replaces
  # (rather than writes through) an existing symlink at $dst as a bonus.
  if ! mv -f "$tmp" "$dst"; then
    rm -f "$tmp"; warn "install failed: $rel"; return 1
  fi
  info "${c_grn}+ copied${c_rst}     $rel ${c_dim}($why)${c_rst}"
}

# Interactive conflict prompt. Prompts on /dev/tty (works with stdout redirected).
# Sets globals directly — REPLY_CHOICE (o|s), and possibly `auto` or exit — so it
# must NOT be called in a command substitution (that would lose those effects).
# Only invoked when have_tty=1.
ask_conflict() {
  local rel="$1" src_m="$2" dst_m="$3" ans
  {
    printf '%sCONFLICT%s %s\n' "$c_red" "$c_rst" "$rel"
    printf '  destination is NEWER than source (dest %s > src %s)\n' \
      "$(date -d "@$dst_m" '+%Y-%m-%d %H:%M:%S')" "$(date -d "@$src_m" '+%Y-%m-%d %H:%M:%S')"
  } >/dev/tty
  while true; do
    printf '  [o]verwrite  [s]kip  [O]verwrite-all  [S]kip-all  [q]uit ? ' >/dev/tty
    if ! read -r ans </dev/tty; then ans="s"; fi   # EOF -> safe default
    case "$ans" in
      o|overwrite) REPLY_CHOICE="o"; return ;;
      s|skip|'')   REPLY_CHOICE="s"; return ;;
      O)           auto="overwrite-all"; REPLY_CHOICE="o"; return ;;
      S)           auto="skip-all";      REPLY_CHOICE="s"; return ;;
      q|quit)      printf '%saborted by user%s\n' "$c_yel" "$c_rst" >/dev/tty; print_summary; exit 130 ;;
      *)           printf '  please answer o/s/O/S/q\n' >/dev/tty ;;
    esac
  done
}

print_summary() {
  info ""
  info "Summary: ${c_grn}${n_copied} new${c_rst}, ${c_grn}${n_updated} updated${c_rst}, ${n_identical} identical, ${c_yel}${n_skipped} skipped${c_rst}, ${n_missing} missing-source, ${c_red}${n_conflict} conflicts${c_rst}, ${c_red}${n_failed} failed${c_rst}"
}

# A manifest entry must be a plain repo-relative path. Reject absolute paths and
# any '..'/'.' component so a stray/typo'd entry can't read or write OUTSIDE the
# local repo or NAS root (path traversal).
is_safe_relpath() {
  local p="$1"
  [[ -n "$p" ]]    || return 1
  [[ "$p" != /* ]] || return 1
  case "/$p/" in *"/../"*|*"/./"*) return 1 ;; esac
  return 0
}

# --- walk the manifest ------------------------------------------------------
for entry in "${MANIFEST[@]}"; do
  entry="${entry%/}"                       # normalize trailing slash on dirs
  if ! is_safe_relpath "$entry"; then
    warn "unsafe manifest path (absolute or contains '..'/'.'), skipping: $entry"
    (( ++n_skipped )); continue
  fi
  src_path="$SRC_ROOT/$entry"

  if [[ -d "$src_path" ]]; then
    # Directory: transfer every file underneath, preserving the relative tree.
    while IFS= read -r -d '' f; do
      rel="${f#"$SRC_ROOT"/}"
      transfer_file "$f" "$DST_ROOT/$rel" "$rel"
    done < <(find "$src_path" -type f -print0 | sort -z)
  elif [[ -f "$src_path" ]]; then
    transfer_file "$src_path" "$DST_ROOT/$entry" "$entry"
  else
    warn "manifest path not present on source, skipping: $entry"
    (( ++n_missing ))
  fi
done

print_summary
# Non-zero exit if any copy failed, so a caller/cron notices.
(( n_failed == 0 )) || exit 1
