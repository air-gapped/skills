#!/bin/bash
# Usage: ./scan-skills.sh [search_root...]
# Finds all SKILL.md files in user-owned skill directories.
# Outputs: words, has-references, path — sorted by modification time (oldest first).
#
# Default search roots:
#   ~/.claude/skills/       (profile skills)
#   .claude/skills/         (project-local skills)
#   ./**/.claude/skills/    (nested project skills — directory-qualified since
#                            Claude Code v2.1.205, e.g. apps/web:deploy)

set -euo pipefail

search_roots=()

if [[ $# -gt 0 ]]; then
    search_roots=("$@")
else
    [[ -d "$HOME/.claude/skills" ]] && search_roots+=("$HOME/.claude/skills")
    [[ -d ".claude/skills" ]] && search_roots+=(".claude/skills")
    # Nested project skills (monorepo packages carrying their own .claude/skills).
    while IFS= read -r nested; do
        search_roots+=("$nested")
    done < <(find . -mindepth 3 -type d -path '*/.claude/skills' \
                  -not -path './.git/*' -not -path '*/node_modules/*' 2>/dev/null)
fi

if [[ ${#search_roots[@]} -eq 0 ]]; then
    echo "No skill directories found." >&2
    exit 1
fi

echo -e "words\trefs\tpath"
find "${search_roots[@]}" -name "SKILL.md" -type f -printf '%T@ %p\n' 2>/dev/null \
    | sort -n \
    | cut -d' ' -f2- \
    | while read -r path; do
        words=$(wc -w < "$path" 2>/dev/null || echo 0)
        dir=$(dirname "$path")
        refs="no"
        [[ -d "$dir/references" ]] && refs="yes"
        echo -e "${words}\t${refs}\t${path}"
    done
