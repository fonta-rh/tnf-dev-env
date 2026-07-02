"""Tests for scripts/consolidate-project.py."""

import json
import shutil
from pathlib import Path

import pytest

# Import from script
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from importlib import import_module
mod = import_module("consolidate-project")

parse_sections = mod.parse_sections
parse_subsections = mod.parse_subsections
build_replacement = mod.build_replacement
build_archive_block = mod.build_archive_block
build_narrative_archive_block = mod.build_narrative_archive_block
is_structural_section = mod.is_structural_section
consolidate = mod.consolidate
Section = mod.Section
Subsection = mod.Subsection
Item = mod.Item
SENTINEL = mod.SENTINEL
NARRATIVE_SENTINEL = mod.NARRATIVE_SENTINEL


# ── Helpers ──────────────────────────────────────────────────────────

def make_lines(text: str) -> list[str]:
    return text.strip("\n").split("\n")


def parse_full(text: str):
    lines = make_lines(text)
    sections = parse_sections(lines)
    for s in sections:
        parse_subsections(s, lines)
    return sections, lines


# ── Section classification ───────────────────────────────────────────

class TestStructuralSections:
    def test_known_structural(self):
        assert is_structural_section("Reference Files")
        assert is_structural_section("Feature Summary")
        assert is_structural_section("Suggested Skills")
        assert is_structural_section("File Inventory")

    def test_prefix_match(self):
        assert is_structural_section("Related Source Code (outdated)")
        assert is_structural_section("closing notes")

    def test_work_tracking_not_blocked(self):
        assert not is_structural_section("Progress")
        assert not is_structural_section("Implementation Plan")
        assert not is_structural_section("Investigation Findings")
        assert not is_structural_section("Validation Results — Patched Payload (2026-04-07)")


# ── Subsection parsing ──────────────────────────────────────────────

class TestParseSubsections:
    def test_basic_subsections(self):
        sections, lines = parse_full("""\
## Progress

### Finding A
Some prose about finding A.
More prose.

### Finding B
Prose about B.
""")
        s = sections[0]
        assert len(s.subsections) == 2
        assert s.subsections[0].heading == "Finding A"
        assert s.subsections[1].heading == "Finding B"

    def test_code_block_not_split(self):
        sections, lines = parse_full("""\
## Progress

### Real subsection
```bash
### This is NOT a heading
echo hello
```
More content after code block.
""")
        s = sections[0]
        assert len(s.subsections) == 1
        assert s.subsections[0].heading == "Real subsection"

    def test_preamble_not_in_subsections(self):
        sections, lines = parse_full("""\
## Progress

Preamble text here.

- [x] Done item

### Sub 1
Narrative.
""")
        s = sections[0]
        assert len(s.subsections) == 1
        assert len(s.checked) == 1

    def test_pure_narrative_detection(self):
        text = "## Progress\n\n"
        for i in range(6):
            text += f"### Sub {i}\n" + "Line.\n" * 6 + "\n"
        sections, lines = parse_full(text)
        s = sections[0]
        assert len(s.archivable_narrative_subsections) == 6
        for sub in s.subsections:
            assert sub.is_pure_narrative

    def test_subsection_with_checklist_not_pure(self):
        sections, lines = parse_full("""\
## Progress

### Sub with items
- [x] Done
- [ ] Not done
""")
        s = sections[0]
        assert len(s.subsections) == 1
        assert not s.subsections[0].is_pure_narrative

    def test_small_subsection_not_archivable(self):
        sections, lines = parse_full("""\
## Progress

### Tiny
Hi.

### Also tiny
Yo.
""")
        s = sections[0]
        for sub in s.subsections:
            assert not sub.is_pure_narrative


# ── Narrative qualification ──────────────────────────────────────────

class TestNarrativeQualification:
    def _make_section_with_narrative(self, num_subs, lines_per_sub):
        text = "## Investigation Findings\n\n"
        for i in range(num_subs):
            text += f"### Sub {i}\n" + "Line.\n" * lines_per_sub + "\n"
        sections, lines = parse_full(text)
        return sections[0]

    def test_qualifies_when_enough_content(self):
        s = self._make_section_with_narrative(3, 15)
        assert s.qualifies_narrative

    def test_not_enough_subsections(self):
        s = self._make_section_with_narrative(1, 30)
        assert not s.qualifies_narrative

    def test_below_line_threshold(self):
        s = self._make_section_with_narrative(3, 3)
        assert not s.qualifies_narrative

    def test_structural_section_blocked(self):
        text = "## Reference Files\n\n"
        for i in range(5):
            text += f"### Sub {i}\n" + "Line.\n" * 10 + "\n"
        sections, lines = parse_full(text)
        assert not sections[0].qualifies_narrative


# ── Re-consolidation ────────────────────────────────────────────────

class TestReconsolidation:
    def test_sentinel_does_not_block_qualification(self):
        text = "## Progress\n\n"
        text += "_Earlier items consolidated in `progress-archive.md` (25 items, 2026-07-01)._\n\n"
        for i in range(12):
            text += f"- [x] Item {i}\n"
        sections, lines = parse_full(text)
        s = sections[0]
        assert s.has_sentinel
        assert s.qualifies_checklist

    def test_old_sentinel_stripped_in_replacement(self):
        text = "## Progress\n\n"
        text += "_Earlier items consolidated in `progress-archive.md` (5 items, 2026-06-01)._\n\n"
        for i in range(12):
            text += f"- [x] Item {i}\n"
        sections, lines = parse_full(text)
        s = sections[0]
        result = build_replacement(s, "2026-07-02")
        result_text = "\n".join(result)
        sentinel_count = result_text.count("consolidated in `progress-archive.md`")
        assert sentinel_count == 1

    def test_cumulative_count(self):
        text = "## Progress\n\n"
        text += "_Earlier items consolidated in `progress-archive.md` (5 items, 2026-06-01)._\n\n"
        for i in range(12):
            text += f"- [x] Item {i}\n"
        sections, lines = parse_full(text)
        s = sections[0]
        result = build_replacement(s, "2026-07-02")
        result_text = "\n".join(result)
        assert "(14 items, 2026-07-02)" in result_text


# ── build_replacement with narrative ─────────────────────────────────

class TestBuildReplacementNarrative:
    def test_narrative_lines_removed(self):
        text = "## Progress\n\n"
        text += "### Old finding\n" + "Old prose.\n" * 8 + "\n"
        text += "### Recent finding\n" + "Recent prose.\n" * 8 + "\n"
        sections, lines = parse_full(text)
        s = sections[0]
        narrative_to_archive = [s.subsections[0]]
        result = build_replacement(s, "2026-07-02", lines, narrative_to_archive)
        result_text = "\n".join(result)
        assert "Old finding" not in result_text
        assert "Recent finding" in result_text
        assert NARRATIVE_SENTINEL in result_text

    def test_narrative_pointer_cumulative(self):
        text = "## Progress\n\n"
        text += "_Earlier subsections consolidated in `progress-archive.md` (3 subsections, 2026-06-01)._\n\n"
        text += "### Sub A\n" + "Line.\n" * 8 + "\n"
        text += "### Sub B\n" + "Line.\n" * 8 + "\n"
        sections, lines = parse_full(text)
        s = sections[0]
        result = build_replacement(s, "2026-07-02", lines, [s.subsections[0]])
        result_text = "\n".join(result)
        assert "(4 subsections, 2026-07-02)" in result_text


# ── build_narrative_archive_block ────────────────────────────────────

class TestNarrativeArchiveBlock:
    def test_archive_contains_full_content(self):
        text = "## Investigation\n\n### Gap Analysis\nLine 1.\nLine 2.\nLine 3.\n"
        sections, lines = parse_full(text)
        s = sections[0]
        block = build_narrative_archive_block(s, s.subsections, lines, "2026-07-02")
        assert "## Investigation — narrative (archived 2026-07-02)" in block
        assert "1 subsections (4 lines)" in block
        assert "### Gap Analysis" in block
        assert "Line 1." in block
        assert "Line 3." in block


# ── Integration: consolidate() ───────────────────────────────────────

SAMPLE_CLAUDE_MD = """\
---
project: test-project
status: active
---

# Test Project

## Feature Summary

This is a feature summary. Should not be touched.

## Reference Files

| File | Content |
|------|---------|
| `design.md` | Architecture |

## Implementation Plan

### Phase 1: Setup
- [x] Set up repo
- [x] Configure CI

### Design Decisions (2026-06-30)
This is a design decision block.
It explains why we chose approach A over B.
The rationale involves several factors.
Additional context about the decision.
More explanation here.
Even more details.
Final notes on the design.
We considered three alternatives.
The first alternative was X.
The second alternative was Y.
The third alternative was Z.
Each had tradeoffs.
We evaluated performance.
We evaluated maintainability.
We evaluated cost.
The winner was approach A.
It scored highest on all criteria.
Implementation timeline: 2 weeks.
Risk assessment: low.
Dependencies: none.
Approved by team lead.

### Architecture Choice (2026-06-29)
We chose microservices over monolith.
The decision was based on scaling needs.
Here is the detailed reasoning.
And more context.
Further elaboration.
Additional points.
Concluding thoughts.
The architecture supports horizontal scaling.
Each service has its own database.
Communication uses gRPC.
Deployment uses Kubernetes.
Monitoring via Prometheus.

## Progress

- [x] Item 01
- [x] Item 02
- [x] Item 03
- [x] Item 04
- [x] Item 05
- [x] Item 06
- [x] Item 07
- [x] Item 08
- [x] Item 09
- [x] Item 10
- [x] Item 11
- [ ] Pending item

### DNS Fix (2026-07-01)
The DNS was broken because of X.
We fixed it by doing Y.
This involved changing Z.
Additional steps were needed.
The fix was validated on cluster A.
Final verification passed.
Root cause: misconfigured resolver.
The resolver pointed to wrong IP.
We updated the config file.
Restarted the DNS service.
Verified with dig command.
All nodes resolving correctly.
Monitoring confirmed no regressions.
Documented in runbook.
Notified the on-call team.
Closed the incident ticket.
Post-mortem scheduled for next week.
Action items documented.
Prevention measures identified.
Automated test added.
CI pipeline updated.

### Port Fix (2026-07-02)
Port was wrong because of A.
Fixed by updating B.
Validated on cluster C.
Additional testing done.
All clear.
The port was hardcoded to 8080.
Changed to read from config.
Added environment variable support.
Updated the deployment manifest.
Tested in staging environment.
Confirmed in production.
No downtime during rollout.
Metrics show normal traffic.
Alert thresholds unchanged.
Documentation updated.
"""


class TestConsolidateIntegration:
    def test_dry_run(self, tmp_path):
        project_dir = tmp_path / "projects" / "test-project"
        project_dir.mkdir(parents=True)
        (project_dir / "CLAUDE.md").write_text(SAMPLE_CLAUDE_MD)

        result = consolidate(project_dir, dry_run=True)
        assert result["status"] == "needs_consolidation"
        names = [s["name"] for s in result["sections"]]
        assert "Progress" in names
        assert "Implementation Plan" in names

        progress = next(s for s in result["sections"] if s["name"] == "Progress")
        assert progress["to_archive"] == 8
        assert progress["narrative_to_archive"] == 1

        impl = next(s for s in result["sections"] if s["name"] == "Implementation Plan")
        assert impl["narrative_to_archive"] == 1

    def test_apply_reduces_lines(self, tmp_path):
        project_dir = tmp_path / "projects" / "test-project"
        project_dir.mkdir(parents=True)
        (project_dir / "CLAUDE.md").write_text(SAMPLE_CLAUDE_MD)

        result = consolidate(project_dir, dry_run=False)
        assert result["status"] == "consolidated"
        assert result["claude_md_after"] < result["claude_md_before"]
        assert result["archive_action"] == "created"

        new_text = (project_dir / "CLAUDE.md").read_text()
        assert "Feature Summary" in new_text
        assert "Reference Files" in new_text
        assert "Port Fix" in new_text
        assert "DNS Fix" not in new_text

        archive_text = (project_dir / "progress-archive.md").read_text()
        assert "DNS Fix" in archive_text
        assert "Item 01" in archive_text

    def test_idempotent_rerun(self, tmp_path):
        project_dir = tmp_path / "projects" / "test-project"
        project_dir.mkdir(parents=True)
        (project_dir / "CLAUDE.md").write_text(SAMPLE_CLAUDE_MD)

        consolidate(project_dir, dry_run=False)
        result2 = consolidate(project_dir, dry_run=True)
        assert result2["status"] == "already_lean"

    def test_structural_sections_untouched(self, tmp_path):
        project_dir = tmp_path / "projects" / "test-project"
        project_dir.mkdir(parents=True)
        (project_dir / "CLAUDE.md").write_text(SAMPLE_CLAUDE_MD)

        consolidate(project_dir, dry_run=False)
        new_text = (project_dir / "CLAUDE.md").read_text()
        assert "This is a feature summary" in new_text
        assert "| `design.md` | Architecture |" in new_text

    def test_reference_table_updated(self, tmp_path):
        project_dir = tmp_path / "projects" / "test-project"
        project_dir.mkdir(parents=True)
        (project_dir / "CLAUDE.md").write_text(SAMPLE_CLAUDE_MD)

        result = consolidate(project_dir, dry_run=False)
        assert result["reference_table_updated"]
        new_text = (project_dir / "CLAUDE.md").read_text()
        assert "progress-archive.md" in new_text


class TestConsolidateRealProject:
    """Test against actual project files (read-only dry-run)."""

    PROJECTS_DIR = Path(__file__).resolve().parent.parent / "projects"

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "projects" / "ocpedge-2775").is_dir(),
        reason="ocpedge-2775 project not present",
    )
    def test_ocpedge_2775_dry_run(self):
        project_dir = self.PROJECTS_DIR / "ocpedge-2775"
        result = consolidate(project_dir, dry_run=True)
        assert result["status"] == "needs_consolidation"
        total_narrative = sum(s["narrative_lines"] for s in result["sections"])
        assert total_narrative > 40
