#!/usr/bin/env bash
# Read-only Secure Boot certificate audit for a Linux host or guest.
#
#   audit-secureboot.sh             read the live EFI variables (mokutil, else efi-readvar)
#   audit-secureboot.sh --from DIR  judge saved dumps: DIR/kek.txt and DIR/db.txt
#                                   (`mokutil --kek > kek.txt; mokutil --db > db.txt` on the host)
#
# Prints one line per certificate checked and a verdict.
# Exit 0 = GOOD, 1 = NEEDS UPDATE, 2 = the variables could not be read.

set -uo pipefail

read_var() { # $1 = kek|db
  if [ -n "${from:-}" ]; then
    cat "$from/$1.txt"
  elif command -v mokutil >/dev/null 2>&1; then
    mokutil "--$1" 2>/dev/null | grep 'Subject:'
  elif command -v efi-readvar >/dev/null 2>&1; then
    if [ "$1" = kek ]; then
      efi-readvar -v KEK 2>/dev/null
    else
      efi-readvar -v db 2>/dev/null
    fi
  fi
}

has() {
  printf '%s\n' "$1" | grep -qiE "$2"
}

mark() {
  if has "$1" "$2"; then
    echo "  present  $3"
  else
    echo "  MISSING  $3"
  fi
}

from=""
if [ "${1:-}" = "--from" ]; then
  from="${2:?--from needs a directory}"
elif [ -n "${1:-}" ]; then
  sed -n '2,9p' "$0" >&2
  exit 2
fi

if [ -z "$from" ] && command -v mokutil >/dev/null 2>&1; then
  echo "state: $(mokutil --sb-state 2>&1 | head -1)"
fi

kek=$(read_var kek)
db=$(read_var db)
if [ -z "$kek" ] || [ -z "$db" ]; then
  echo "verdict: UNKNOWN (could not read KEK or db; run as root, or install mokutil or efitools)"
  exit 2
fi

# "Microsoft UEFI CA 2023" must not match "Microsoft Option ROM UEFI CA 2023".
uefi2023='(CN=|^| )Microsoft UEFI CA 2023'
echo "KEK:"
mark "$kek" 'KEK 2K CA 2023' "Microsoft Corporation KEK 2K CA 2023"
echo "db:"
mark "$db" "$uefi2023" "Microsoft UEFI CA 2023 (signs the Linux shim)"
mark "$db" 'Windows UEFI CA 2023' "Windows UEFI CA 2023"
mark "$db" 'Microsoft Corporation UEFI CA 2011' "Microsoft Corporation UEFI CA 2011 (old, expected)"

if has "$db" "$uefi2023" && has "$kek" 'KEK 2K CA 2023'; then
  echo "verdict: GOOD"
  exit 0
fi
if has "$db" "$uefi2023"; then
  echo "verdict: NEEDS UPDATE (db has the 2023 CA, KEK 2023 is missing)"
else
  echo "verdict: NEEDS UPDATE (db lacks Microsoft UEFI CA 2023)"
fi
exit 1
