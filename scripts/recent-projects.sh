#!/bin/bash
# Show the 3 most recently active projects based on file modification times.
# Used by the SessionStart hook to give Claude and the user quick context.
# Output: JSON with systemMessage (user-visible) and additionalContext (model context).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
PROJECTS_DIR="$PROJECT_ROOT/projects"

# Read hook input from stdin to detect event source
source=$(timeout 0.1 jq -r '.source // empty' 2>/dev/null)

# Check if a project's CLAUDE.md has status: done
is_done() {
  local claude_md="$1/CLAUDE.md"
  [ -f "$claude_md" ] || return 1
  local s
  s=$(sed -n '/^---$/,/^---$/{ s/^status:[[:space:]]*//p; }' "$claude_md" 2>/dev/null)
  [ "$s" = "done" ]
}

# --names mode: output just project names sorted by recency (machine-readable)
if [ "${1:-}" = "--names" ]; then
  [ -d "$PROJECTS_DIR" ] || exit 0
  entries=()
  for dir in "$PROJECTS_DIR"/*/; do
    [ -d "$dir" ] || continue
    is_done "$dir" && continue
    name=$(basename "$dir")
    newest=$(find "$dir" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1)
    [ -z "$newest" ] && continue
    entries+=("${newest}|${name}")
  done
  [ ${#entries[@]} -eq 0 ] && exit 0
  printf '%s\n' "${entries[@]}" | sort -t'|' -k1 -rn | cut -d'|' -f2
  exit 0
fi

# Exit silently if no projects directory
[ -d "$PROJECTS_DIR" ] || exit 0

# Collect project info: epoch|name|type|status|human_date
entries=()
for dir in "$PROJECTS_DIR"/*/; do
  [ -d "$dir" ] || continue
  name=$(basename "$dir")

  # Skip projects marked as done
  is_done "$dir" && continue

  # Find the most recently modified file inside the project
  newest=$(find "$dir" -type f -printf '%T@|%Tb %Td %TH:%TM\n' 2>/dev/null \
           | sort -t'|' -k1 -rn | head -1)
  [ -z "$newest" ] && continue

  epoch=${newest%%|*}
  date_str=${newest#*|}

  # Extract type and status from CLAUDE.md frontmatter
  type="—"
  status="—"
  claude_md="$dir/CLAUDE.md"
  if [ -f "$claude_md" ]; then
    t=$(sed -n '/^---$/,/^---$/{ s/^type:[[:space:]]*//p; }' "$claude_md" 2>/dev/null)
    s=$(sed -n '/^---$/,/^---$/{ s/^status:[[:space:]]*//p; }' "$claude_md" 2>/dev/null)
    [ -n "$t" ] && type="$t"
    [ -n "$s" ] && status="$s"
  fi

  entries+=("${epoch}|${name}|${type}|${status}|${date_str}")
done

# Exit silently if no projects found
[ ${#entries[@]} -eq 0 ] && exit 0

# Sort by epoch (newest first), take top 3
sorted=$(printf '%s\n' "${entries[@]}" | sort -t'|' -k1 -rn | head -3)

# Build the display text
output="Recent projects:\n"
output+="\n  #   NAME                           TYPE           STATUS     LAST ACTIVE"
output+="\n  -   ----                           ----           ------     -----------"
while IFS='|' read -r _ name type status date_str; do
  ((i++))
  output+=$(printf '\n  %-3s %-30s %-14s %-10s %s' "$i" "$name" "$type" "$status" "$date_str")
done <<< "$sorted"
output+="\n\n  Tip: /project:resume <name-or-number>"

# Escape for JSON string (newlines → \n, quotes → \", backslashes → \\)
json_output=$(echo -e "$output" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().rstrip()))')

# Output JSON: systemMessage for user display, additionalContext for model
cat <<EOF
{
  "systemMessage": ${json_output},
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": ${json_output}
  }
}
EOF

exit 0
