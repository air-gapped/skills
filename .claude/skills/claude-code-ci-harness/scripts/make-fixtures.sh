#!/usr/bin/env bash
# Populate a workdir with the files references/scenario-bank.md names.
set -Eeuo pipefail

dir=${1:?usage: make-fixtures.sh DIR}
mkdir -p -- "$dir"
cd -- "$dir"

printf 'Fixture A.\nFirst of two files for the parallel-read scenario.\n' > fixture-a.txt
printf 'Fixture B.\nSecond of two files for the parallel-read scenario.\n' > fixture-b.txt
printf 'This file name contains spaces.\n' > 'fixture with spaces.txt'

# Long-context: ~20K tokens, under Read's 2000-line default window; the answer is the last line.
{
  for i in $(seq 1 1500); do
    printf 'Line %05d: the quick brown fox jumps over the lazy dog.\n' "$i"
  done
  printf 'LAST-LINE-MARKER-7f3a\n'
} > large-fixture.txt

mkdir -p references
printf '# Alpha\n' > references/alpha.md
printf '# Beta\n' > references/beta.md

printf '%s\n' "$dir"
