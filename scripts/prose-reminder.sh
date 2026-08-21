#!/usr/bin/env bash
# Pre-commit reminder: skill markdown is loaded into an agent's context, so
# prose that does not change behaviour is a permanent token tax on every read.
#
# Deliberately does NOT try to detect which lines are bad. A pattern list only
# ever catches the shapes someone already noticed, and the author is looking at
# the diff anyway — the gap is not detection, it is that the question never gets
# asked at the moment the text is written. So this just counts and asks.
#
# Never blocks.
set -uo pipefail

ADDED=$(git diff --cached --numstat -- '.claude/skills/**/*.md' \
        | awk '{s += $1} END {print s+0}')
[ "${ADDED:-0}" -gt 0 ] || exit 0

FILES=$(git diff --cached --name-only -- '.claude/skills/**/*.md' | wc -l)

cat <<EOF

  prose check — $ADDED line(s) added across $FILES skill markdown file(s).

  Each added line must either change what an agent DOES, or stop an agent
  undoing a rule. Anything else — how a number was arrived at, what an earlier
  version claimed, what was cross-checked against what — belongs in this commit
  message, where git already keeps it.

  Cost of getting it wrong differs by file:
    SKILL.md body   loaded whenever the skill fires, injected in full for
                    preloaded-skill subagents, re-attached after compaction
    references/     costs nothing until something reads it

EOF
exit 0
