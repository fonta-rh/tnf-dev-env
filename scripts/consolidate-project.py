#!/usr/bin/env python3
"""Consolidate bloated project CLAUDE.md by archiving completed checklist items.

Usage: consolidate-project.py [--dry-run] <project-name>
Output: JSON to stdout.

Sections with 10+ completed items get their checked items (except the
last 3) archived to progress-archive.md. A pointer line replaces the
archived items in CLAUDE.md.
"""

import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

THRESHOLD = 10
KEEP_RECENT = 3
NARRATIVE_THRESHOLD = 20
NARRATIVE_KEEP_RECENT = 1
NARRATIVE_MIN_LINES = 5
ARCHIVE_FILENAME = "progress-archive.md"
SENTINEL = "consolidated in `progress-archive.md`"
NARRATIVE_SENTINEL = "subsections consolidated in `progress-archive.md`"

STRUCTURAL_SECTIONS = {
    "reference files", "related source code", "suggested skills",
    "closing notes", "bug summary", "feature summary", "test summary",
    "doc summary", "ci job links", "attachments", "scripts",
    "related prs", "related projects", "gcs access", "worktree",
    "worktree paths", "outline", "notes", "file inventory",
}

RE_HEADING = re.compile(r"^## (.+)$")
RE_H3_HEADING = re.compile(r"^### (.+)$")
RE_CHECKED = re.compile(r"^\s*- \[x\] .+$")
RE_UNCHECKED = re.compile(r"^\s*- \[ \] .+$")
RE_STRIKETHROUGH = re.compile(r"^\s*- ~~?.+~~?\s*$")
RE_POINTER_COUNT = re.compile(r"\((\d+) items")
RE_NARRATIVE_POINTER_COUNT = re.compile(r"\((\d+) subsections")


@dataclass
class Item:
    line_idx: int
    text: str
    kind: str  # "checked", "unchecked", "strikethrough", "other"


@dataclass
class Subsection:
    heading: str
    start_idx: int
    end_idx: int
    items: list[Item] = field(default_factory=list)

    @property
    def checked(self) -> list[Item]:
        return [i for i in self.items if i.kind == "checked"]

    @property
    def unchecked(self) -> list[Item]:
        return [i for i in self.items if i.kind == "unchecked"]

    @property
    def line_count(self) -> int:
        return self.end_idx - self.start_idx

    @property
    def is_complete(self) -> bool:
        return len(self.unchecked) == 0

    @property
    def is_pure_narrative(self) -> bool:
        return not self.checked and not self.unchecked and self.line_count >= NARRATIVE_MIN_LINES


def is_structural_section(name: str) -> bool:
    lower = name.lower()
    return any(lower.startswith(s) for s in STRUCTURAL_SECTIONS)


@dataclass
class Section:
    name: str
    start_idx: int
    end_idx: int  # exclusive
    items: list[Item] = field(default_factory=list)
    has_sentinel: bool = False
    has_narrative_sentinel: bool = False
    subsections: list[Subsection] = field(default_factory=list)

    @property
    def checked(self) -> list[Item]:
        return [i for i in self.items if i.kind == "checked"]

    @property
    def unchecked(self) -> list[Item]:
        return [i for i in self.items if i.kind == "unchecked"]

    @property
    def strikethrough(self) -> list[Item]:
        return [i for i in self.items if i.kind == "strikethrough"]

    @property
    def qualifies(self) -> bool:
        return self.qualifies_checklist or self.qualifies_narrative

    @property
    def qualifies_checklist(self) -> bool:
        return len(self.checked) >= THRESHOLD

    @property
    def qualifies_narrative(self) -> bool:
        if is_structural_section(self.name):
            return False
        archivable = self.archivable_narrative_subsections
        if len(archivable) <= NARRATIVE_KEEP_RECENT:
            return False
        to_archive = archivable[:-NARRATIVE_KEEP_RECENT]
        return sum(s.line_count for s in to_archive) >= NARRATIVE_THRESHOLD

    @property
    def archivable_narrative_subsections(self) -> list:
        return [s for s in self.subsections if s.is_pure_narrative]


def classify_line(line: str) -> str:
    if RE_CHECKED.match(line):
        return "checked"
    if RE_UNCHECKED.match(line):
        return "unchecked"
    if RE_STRIKETHROUGH.match(line):
        return "strikethrough"
    return "other"


def parse_sections(lines: list[str]) -> list[Section]:
    """Split CLAUDE.md lines into sections by ## headings."""
    sections: list[Section] = []
    current: Section | None = None

    for idx, line in enumerate(lines):
        m = RE_HEADING.match(line)
        if m:
            if current is not None:
                current.end_idx = idx
                sections.append(current)
            current = Section(name=m.group(1).strip(), start_idx=idx, end_idx=len(lines))
            continue

        if current is not None:
            kind = classify_line(line)
            current.items.append(Item(line_idx=idx, text=line, kind=kind))
            if SENTINEL in line:
                current.has_sentinel = True
            if NARRATIVE_SENTINEL in line:
                current.has_narrative_sentinel = True

    if current is not None:
        current.end_idx = len(lines)
        sections.append(current)

    return sections


def parse_subsections(section: Section, lines: list[str]) -> None:
    current_sub: Subsection | None = None
    in_code_block = False

    for item in section.items:
        line = lines[item.line_idx]

        if line.startswith("```"):
            in_code_block = not in_code_block
            if current_sub is not None:
                current_sub.items.append(item)
            continue

        if in_code_block:
            if current_sub is not None:
                current_sub.items.append(item)
            continue

        m = RE_H3_HEADING.match(line)
        if m:
            if current_sub is not None:
                current_sub.end_idx = item.line_idx
                section.subsections.append(current_sub)
            current_sub = Subsection(
                heading=m.group(1).strip(),
                start_idx=item.line_idx,
                end_idx=section.end_idx,
            )
            continue

        if current_sub is not None:
            current_sub.items.append(item)

    if current_sub is not None:
        current_sub.end_idx = section.end_idx
        section.subsections.append(current_sub)


def parse_reference_table(text: str) -> tuple[bool, bool, int]:
    """Check if Reference Files table exists and if archive is listed.

    Returns (has_table, archive_listed, last_row_line_idx).
    last_row_line_idx is the line index of the last table row (for insertion).
    """
    in_section = False
    found_header = False
    skipped_separator = False
    archive_listed = False
    last_row_idx = -1

    for idx, line in enumerate(text.splitlines()):
        if re.match(r"^##\s+Reference Files", line, re.IGNORECASE):
            in_section = True
            continue

        if in_section and not found_header:
            if "|" in line and "File" in line:
                found_header = True
            elif line.startswith("## "):
                return False, False, -1
            continue

        if found_header and not skipped_separator:
            if re.match(r"^\|[-\s|]+\|$", line):
                skipped_separator = True
            continue

        if skipped_separator:
            if not line.strip() or line.startswith("## "):
                break
            if ARCHIVE_FILENAME in line:
                archive_listed = True
            last_row_idx = idx

    return (found_header and skipped_separator), archive_listed, last_row_idx


def build_archive_block(section: Section, today: str) -> str:
    """Build the archive markdown block for a section."""
    checked = section.checked
    to_archive = checked[:-KEEP_RECENT] if len(checked) > KEEP_RECENT else checked
    strikethroughs = section.strikethrough

    lines = [
        f"## {section.name} (archived {today})",
        "",
        f"{len(to_archive)} completed items archived from CLAUDE.md.",
        "",
    ]
    for item in to_archive:
        lines.append(item.text)
    if strikethroughs:
        for item in strikethroughs:
            lines.append(item.text)
    lines.append("")
    return "\n".join(lines)


def build_narrative_archive_block(
    section: Section,
    subsections: list[Subsection],
    lines: list[str],
    today: str,
) -> str:
    total_lines = sum(s.line_count for s in subsections)
    block_lines = [
        f"## {section.name} — narrative (archived {today})",
        "",
        f"{len(subsections)} subsections ({total_lines} lines) archived from CLAUDE.md.",
        "",
    ]
    for sub in subsections:
        for idx in range(sub.start_idx, sub.end_idx):
            block_lines.append(lines[idx])
        block_lines.append("")

    return "\n".join(block_lines)


def _extract_old_count(items: list[Item], sentinel_text: str, pattern: re.Pattern) -> int:
    for item in items:
        if sentinel_text in item.text:
            m = pattern.search(item.text)
            if m:
                return int(m.group(1))
    return 0


def build_replacement(
    section: Section,
    today: str,
    lines: list[str] | None = None,
    narrative_to_archive: list[Subsection] | None = None,
) -> list[str]:
    checked = section.checked
    to_archive_set = set()
    if len(checked) > KEEP_RECENT:
        for item in checked[:-KEEP_RECENT]:
            to_archive_set.add(item.line_idx)

    old_checklist_count = _extract_old_count(section.items, SENTINEL, RE_POINTER_COUNT)
    archived_count = len(to_archive_set) + old_checklist_count

    remove_set = set(to_archive_set)

    if narrative_to_archive:
        for sub in narrative_to_archive:
            for idx in range(sub.start_idx, sub.end_idx):
                remove_set.add(idx)

    old_narrative_count = _extract_old_count(
        section.items, NARRATIVE_SENTINEL, RE_NARRATIVE_POINTER_COUNT,
    )
    narrative_count = (
        len(narrative_to_archive) + old_narrative_count if narrative_to_archive
        else old_narrative_count
    )

    result = [""]
    if archived_count > 0:
        pointer = (
            f"_Earlier items consolidated in `{ARCHIVE_FILENAME}` "
            f"({archived_count} items, {today})._"
        )
        result.append(pointer)
    if narrative_count > 0:
        narrative_pointer = (
            f"_Earlier subsections consolidated in `{ARCHIVE_FILENAME}` "
            f"({narrative_count} subsections, {today})._"
        )
        result.append(narrative_pointer)
    result.append("")

    kept_items = [
        item for item in section.items
        if item.line_idx not in remove_set
        and SENTINEL not in item.text
        and NARRATIVE_SENTINEL not in item.text
    ]
    while kept_items and kept_items[0].kind == "other" and not kept_items[0].text.strip():
        kept_items.pop(0)
    for item in kept_items:
        result.append(item.text)

    while len(result) > 1 and result[-1] == "":
        result.pop()
    result.append("")

    return result


def _compute_narrative_plan(section: Section) -> tuple[list[Subsection], list[Subsection]]:
    if not section.qualifies_narrative:
        return [], []
    archivable = section.archivable_narrative_subsections
    to_archive = archivable[:-NARRATIVE_KEEP_RECENT]
    to_keep = archivable[-NARRATIVE_KEEP_RECENT:]
    return to_archive, to_keep


def consolidate(project_dir: Path, dry_run: bool = False) -> dict[str, Any]:
    claude_md = project_dir / "CLAUDE.md"
    if not claude_md.is_file():
        return {
            "status": "error",
            "message": f"No CLAUDE.md found in {project_dir}",
        }

    text = claude_md.read_text()
    lines = text.splitlines()
    sections = parse_sections(lines)

    for s in sections:
        parse_subsections(s, lines)

    qualifying = [s for s in sections if s.qualifies]
    project_name = project_dir.name

    if not qualifying:
        total_checked = sum(len(s.checked) for s in sections)
        return {
            "status": "already_lean",
            "project": project_name,
            "claude_md_lines": len(lines),
            "message": (
                f"Nothing to consolidate ({total_checked} completed items "
                f"across all sections, none exceeding threshold of {THRESHOLD})."
            ),
            "sections": [],
        }

    section_plans: list[dict[str, Any]] = []
    for s in qualifying:
        checklist_to_archive = max(0, len(s.checked) - KEEP_RECENT)
        narrative_to_archive, narrative_to_keep = _compute_narrative_plan(s)
        section_plans.append({
            "section": s,
            "name": s.name,
            "checked": len(s.checked),
            "to_archive": checklist_to_archive,
            "to_keep": min(len(s.checked), KEEP_RECENT),
            "unchecked": len(s.unchecked),
            "strikethrough": len(s.strikethrough),
            "narrative_subsections": len(s.archivable_narrative_subsections),
            "narrative_to_archive": len(narrative_to_archive),
            "narrative_to_keep": len(narrative_to_keep),
            "narrative_lines": sum(sub.line_count for sub in narrative_to_archive),
            "_narrative_subs": narrative_to_archive,
        })

    if dry_run:
        section_info = [
            {k: v for k, v in sp.items() if k not in ("section", "_narrative_subs")}
            for sp in section_plans
        ]
        return {
            "status": "needs_consolidation",
            "project": project_name,
            "claude_md_path": str(claude_md.relative_to(project_dir.parent.parent)),
            "claude_md_lines": len(lines),
            "sections": section_info,
        }

    today = date.today().isoformat()

    archive_blocks = []
    for sp in section_plans:
        s = sp["section"]
        if sp["to_archive"] > 0:
            archive_blocks.append(build_archive_block(s, today))
        if sp["_narrative_subs"]:
            archive_blocks.append(
                build_narrative_archive_block(s, sp["_narrative_subs"], lines, today)
            )

    archive_path = project_dir / ARCHIVE_FILENAME
    if archive_path.is_file():
        existing = archive_path.read_text()
        new_blocks = []
        for block in archive_blocks:
            header_line = block.splitlines()[0]
            if header_line in existing:
                continue
            new_blocks.append(block)
        if new_blocks:
            with archive_path.open("a") as f:
                f.write("\n" + "\n".join(new_blocks))
        archive_action = "appended"
    else:
        header = (
            "# Progress Archive\n"
            "\n"
            "_Completed checklist items and narrative subsections archived\n"
            "from CLAUDE.md by `/project:consolidate`. Items grouped by\n"
            "source section, ordered chronologically (oldest first)._\n"
            "\n"
        )
        archive_path.write_text(header + "\n".join(archive_blocks))
        archive_action = "created"

    new_lines: list[str] = []
    qualifying_by_start = {sp["section"].start_idx: sp for sp in section_plans}
    skip_until: int | None = None

    for idx, line in enumerate(lines):
        if skip_until is not None and idx < skip_until:
            continue
        skip_until = None

        if idx in qualifying_by_start:
            sp = qualifying_by_start[idx]
            s = sp["section"]
            new_lines.append(line)
            replacement = build_replacement(
                s, today, lines,
                narrative_to_archive=sp["_narrative_subs"] or None,
            )
            new_lines.extend(replacement)
            skip_until = s.end_idx
        else:
            new_lines.append(line)

    new_text = "\n".join(new_lines)
    if not new_text.endswith("\n"):
        new_text += "\n"

    has_table, archive_listed, last_row_idx = parse_reference_table(new_text)
    ref_updated = False
    if has_table and not archive_listed and last_row_idx >= 0:
        ref_line = f"| `{ARCHIVE_FILENAME}` | Archived completed checklist items and narrative subsections |"
        ref_lines = new_text.splitlines()
        ref_lines.insert(last_row_idx + 1, ref_line)
        new_text = "\n".join(ref_lines)
        if not new_text.endswith("\n"):
            new_text += "\n"
        ref_updated = True

    claude_md.write_text(new_text)

    return {
        "status": "consolidated",
        "project": project_name,
        "sections": [
            {
                "name": sp["name"],
                "archived": sp["to_archive"],
                "kept": sp["to_keep"],
                "narrative_archived": sp["narrative_to_archive"],
                "narrative_kept": sp["narrative_to_keep"],
                "narrative_lines": sp["narrative_lines"],
            }
            for sp in section_plans
        ],
        "claude_md_before": len(lines),
        "claude_md_after": len(new_text.splitlines()),
        "archive_file": ARCHIVE_FILENAME,
        "archive_action": archive_action,
        "reference_table_updated": ref_updated,
    }


def main():
    args = sys.argv[1:]
    dry_run = False
    if "--dry-run" in args:
        dry_run = True
        args.remove("--dry-run")

    if not args:
        print(json.dumps({
            "status": "error",
            "message": "Usage: consolidate-project.py [--dry-run] <project-name>",
        }))
        sys.exit(1)

    project_name = args[0]
    root = Path(os.environ.get(
        "CLAUDE_PROJECT_DIR",
        Path(__file__).resolve().parent.parent,
    ))
    project_dir = root / "projects" / project_name

    if not project_dir.is_dir():
        print(json.dumps({
            "status": "error",
            "message": f"Project directory not found: {project_dir}",
        }))
        sys.exit(1)

    result = consolidate(project_dir, dry_run=dry_run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
