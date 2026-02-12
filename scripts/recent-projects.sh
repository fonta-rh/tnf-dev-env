#!/bin/bash
# Show the 3 most recently active projects based on file modification times.
# Used by the SessionStart hook to give Claude and the user quick context.

PROJECTS_DIR="${CLAUDE_PROJECT_DIR:-.}/projects"

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

echo "📂 Recent projects:"
echo ""
printf "  %-30s %-14s %-10s %s\n" "NAME" "TYPE" "STATUS" "LAST ACTIVE"
printf "  %-30s %-14s %-10s %s\n" "----" "----" "------" "-----------"
while IFS='|' read -r _ name type status date_str; do
  printf "  %-30s %-14s %-10s %s\n" "$name" "$type" "$status" "$date_str"
done <<< "$sorted"
echo ""
echo "  Tip: /project:resume <name>"
