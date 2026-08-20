#!/usr/bin/env bash
# Pre-commit gate: validate only the skills touched by this commit.
#
# NVIDIA's documented shape is a CI merge gate over the whole collection
# (docs.nvidia.com/skills/skillevaluator/ci-integration). This is the same
# command scoped to staged skills, for two reasons: the full fleet takes ~4m40s
# while one skill takes ~0.3s, and scoping means pre-existing debt in skills you
# are not touching never blocks unrelated work — while touching a skill that is
# over the size guidance tells you so.
#
# Severity decisions live in .claude/skillevaluator-policy.yaml, reviewed like
# code. Findings below high stay in the report without blocking.
#
# Skips silently when skillevaluator is absent, so a fresh clone can commit
# before anyone installs it:
#   uv tool install --python 3.13 \
#     "skillevaluator[security] @ git+https://github.com/NVIDIA/SkillEvaluator.git"
# Full scanner coverage also wants semgrep, SkillSpector and gitleaks — see
# docs.nvidia.com/skills/skillevaluator/installation

set -uo pipefail

command -v skillevaluator >/dev/null 2>&1 || exit 0

REPO_ROOT="$(git rev-parse --show-toplevel)"
POLICY="$REPO_ROOT/.claude/skillevaluator-policy.yaml"
[ -f "$POLICY" ] || exit 0

# Enables the PII home-path check. Without an identity it is skipped silently,
# which would make the most important check in this gate a no-op.
export SKILLEVALUATOR_SUBMITTER="${SKILLEVALUATOR_SUBMITTER:-$(git config user.name || echo "$USER")}"

# Staged skill directories, from any staged path under .claude/skills/<name>/.
mapfile -t SKILLS < <(
  git diff --cached --name-only --diff-filter=ACMR \
    | grep -E '^\.claude/skills/[^/]+/' \
    | cut -d/ -f1-3 \
    | sort -u
)

[ "${#SKILLS[@]}" -eq 0 ] && exit 0

status=0
for skill in "${SKILLS[@]}"; do
  [ -f "$REPO_ROOT/$skill/SKILL.md" ] || continue
  if ! skillevaluator validate "$REPO_ROOT/$skill" \
        --type skill --external --policy "$POLICY" \
        --no-dedup -c -r cli >/tmp/se-gate.$$ 2>&1; then
    echo "--- skillevaluator: $skill ---"
    grep -E '\[(CRITICAL|HIGH)\]|✗|Error:' /tmp/se-gate.$$ | head -12
    status=1
  fi
done
rm -f /tmp/se-gate.$$

if [ "$status" -ne 0 ]; then
  cat <<'MSG'

Blocked by skillevaluator. To see the full report for a skill:
  skillevaluator validate .claude/skills/<name> --type skill --external \
    --policy .claude/skillevaluator-policy.yaml --no-dedup -r cli

If a finding is wrong for this repo, downgrade it in
.claude/skillevaluator-policy.yaml with a reason — do not add a bypass.
MSG
fi
exit "$status"
