#!/bin/bash
# Show the 3 most recently active projects based on file modification times.
# Used by the SessionStart hook to give Claude and the user quick context.
# On startup: displays to terminal via /dev/tty (clean, before TUI initializes).
# All events: passes plain text to stdout for model context.
#
# Known limitation: SessionStart hooks on source=clear silently drop all output
# (both stdout and stderr). This is a Claude Code bug — the hook fires and runs
# correctly, but the output is discarded. Filed upstream.
# Only startup and resume sources produce visible/context output.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
PROJECTS_DIR="$PROJECT_ROOT/projects"

# Read hook input from stdin to detect event source
source=$(timeout 0.1 jq -r '.source // empty' 2>/dev/null)

# --names mode: output just project names sorted by recency (machine-readable)
if [ "${1:-}" = "--names" ]; then
  [ -d "$PROJECTS_DIR" ] || exit 0
  entries=()
  for dir in "$PROJECTS_DIR"/*/; do
    [ -d "$dir" ] || continue
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

# Build the display output
output="📂 Recent projects:"
output+=$'\n'
output+=$(printf "\n  %-3s %-30s %-14s %-10s %s" "#" "NAME" "TYPE" "STATUS" "LAST ACTIVE")
output+=$(printf "\n  %-3s %-30s %-14s %-10s %s" "-" "----" "----" "------" "-----------")
i=0
while IFS='|' read -r _ name type status date_str; do
  ((i++))
  output+=$(printf "\n  %-3s %-30s %-14s %-10s %s" "$i" "$name" "$type" "$status" "$date_str")
done <<< "$sorted"
output+=$'\n\n  Tip: /project:resume <name-or-number>'

# On startup, write directly to terminal (TUI hasn't initialized yet)
if [ "$source" = "startup" ]; then
  echo "$output" > /dev/tty 2>/dev/null
fi

# Always pass context to the model via stdout
echo "$output"
