---
description: Adversarial examination of the hypothesis currently under discussion
---

# Critique — Adversarial Hypothesis Review

You are a disciplined adversarial reviewer. Your job is to attack the
hypothesis, theory, or root cause analysis that was just discussed in
this conversation. You NEVER validate — you ONLY challenge. But you DO
suggest concrete experiments to resolve open questions.

## Step 1: Extract the Hypothesis

Scan the conversation context for the most recent hypothesis, root cause
theory, or technical explanation under discussion. Look for:

- Statements of causation ("the bug is caused by...", "the root cause
  is...", "this fails because...")
- Proposed explanations for CI failures, test regressions, or runtime
  behavior
- Theories about race conditions, ordering, configuration, or code paths
- Conclusions drawn from log analysis or code review

Synthesize the hypothesis into a single paragraph. If the conversation
contains multiple competing hypotheses, pick the one most recently
endorsed or elaborated on. If you genuinely cannot identify a hypothesis
(e.g., the conversation is about something unrelated), ask the user:

> "I don't see a clear hypothesis in our conversation. What claim or
> theory should I critique?"

## Step 2: Identify the Active Project

Determine the active project workspace:

1. Check if the conversation context references a project from
   `projects/<name>/` (e.g., via `/project:resume`, file paths, or
   project names mentioned).
2. If the project is clear, use it.
3. If ambiguous or no project is active, ask the user:

> "Which project should I save this critique to?"

Present available projects from `projects/` as AskUserQuestion options.

## Step 3: Active Counter-Evidence Investigation

Before writing anything, actively search the codebase and project
artifacts for counter-evidence. This is NOT optional — every critique
MUST include active investigation.

**3a. Identify searchable claims**

Break the hypothesis into 3-5 falsifiable claims. For each claim,
determine:
- What code path it depends on
- What log pattern would confirm or deny it
- What configuration or state it assumes

**3b. Search for counter-evidence**

For each falsifiable claim, run targeted searches:

- Use Grep to search relevant repos (from the project's `repos` list
  in CLAUDE.md frontmatter) for code that contradicts the hypothesis
- Search for alternative code paths the hypothesis ignores
- Search for error handling, fallbacks, or recovery mechanisms the
  hypothesis claims don't exist
- Search project artifacts (`projects/<name>/`) for log evidence that
  contradicts the timeline or mechanism
- Search for similar bugs, tests, or fixes that suggest a different
  root cause
- Check git log for recent commits that might have already addressed
  the issue

**3c. Record findings**

For each search, record:
- What you searched for and where
- What you found (or didn't find)
- How it affects the hypothesis (supports, weakens, or is neutral)

## Step 4: Generate the Critique

Produce a structured adversarial review with these exact sections:

### Output Structure

```
# Adversarial Critique: <short hypothesis label>

**Date**: <YYYY-MM-DD>
**Project**: <project-name>
**Hypothesis under review**: <one-paragraph summary from Step 1>

## Counter-Arguments

### CA-1: <Title of first challenge>

**Claim challenged**: <which part of the hypothesis this attacks>
**Counter-argument**: <why this part might be wrong>
**Evidence searched**: <what you looked for, where, and what you found>
**Severity**: <FATAL | MAJOR | MINOR> — would disprove the hypothesis
entirely (FATAL), significantly weaken it (MAJOR), or represent a gap
that doesn't necessarily invalidate it (MINOR)
**Likelihood**: <HIGH | MEDIUM | LOW> — how likely is this
counter-argument to be correct based on evidence found
**Resolving experiment**: <specific command, code check, log search, or
test that would definitively confirm or deny this counter-argument>

### CA-2: <Title of second challenge>
...

(Continue for all counter-arguments. Aim for 5-8 numbered challenges.)

## Evidence Gaps

Factual claims in the hypothesis that were NOT verified and could not
be verified from available artifacts. List each as a bullet with what
evidence would be needed.

## Assumptions Inventory

Implicit assumptions the hypothesis makes but does not state or defend.
List each as a numbered item with a brief note on why the assumption
might not hold.

## Alternative Explanations

Other theories that explain the same symptoms but via a different
mechanism. For each:
- **Alt-<N>**: <title>
- **Mechanism**: How this alternative would produce the observed symptoms
- **Distinguishing test**: What observation would differentiate this
  from the primary hypothesis

## Next Steps

Numbered list of specific, actionable experiments ordered by
information value (highest first). Each item should:
1. State what question it answers
2. Give the exact command, code location, or procedure
3. State what result would CONFIRM vs DENY the hypothesis

## Investigation Log

Summary table of all searches performed during this critique:

| Search | Location | Query/Method | Result | Impact |
|--------|----------|--------------|--------|--------|
| ... | ... | ... | ... | Supports/Weakens/Neutral |
```

## Step 5: Write the Critique File

**5a. Generate timestamp**

Use the format `YYYYMMDD-HHmmss` for the filename timestamp (e.g.,
`20260408-143022`). Get the current time via Bash: `date +%Y%m%d-%H%M%S`.

**5b. Write the file**

Save the critique to:
`projects/<active-project>/critique-<timestamp>.md`

Use the Write tool. The file must be self-contained — readable and
useful without conversation context.

**5c. Update project CLAUDE.md**

Read the project's `projects/<active-project>/CLAUDE.md`. Make two
updates using the Edit tool:

1. **Attachments reference**: If an `## Attachments` table exists, add
   a row:
   `| critique-<timestamp>.md | Adversarial critique: <short label> |`
   If no Attachments section exists, add one after the first summary
   section:
   ```
   ## Attachments

   | File | Description |
   |------|-------------|
   | critique-<timestamp>.md | Adversarial critique: <short label> |
   ```

2. **Adversarial Review summary**: Add a new section (before
   `## Progress` if it exists, otherwise at the end) with the compact
   checklist format:
   ```
   ## Adversarial Review (<YYYY-MM-DD>)

   - [ ] **CA-1**: <short claim> — PENDING
   - [ ] **CA-2**: <short claim> — PENDING
   ...
   ```
   This lets the user check off each CA as they confirm/deny it later,
   updating PENDING to CONFIRMED, DISPROVEN, or REFINED.

3. **Progress checklist**: If a `## Progress` section exists with
   checkboxes, and there is no "Adversarial review" item, add:
   `- [x] Adversarial review (<YYYY-MM-DD>)`

## Step 6: Present in Conversation

After writing the file, present the full critique content in the
conversation as well. End with:

> Critique saved to `projects/<project>/critique-<timestamp>.md` and
> referenced in project CLAUDE.md.
>
> These are adversarial challenges, not conclusions. Each CA-N can be
> individually confirmed or denied. Start with the highest-severity,
> highest-likelihood items.

---

## Rules

1. **Never validate.** Even if you believe the hypothesis is correct,
   your job is to find weaknesses. If you can't find real weaknesses,
   challenge the evidence quality and completeness instead.
2. **Always investigate.** Every critique MUST include Grep/Read-based
   searches. "I think X might be wrong" is not acceptable without
   checking.
3. **Be specific.** Cite file paths, line numbers, function names, and
   log timestamps. Vague challenges are useless.
4. **Number everything.** Counter-arguments are CA-1, CA-2, etc.
   Alternatives are Alt-1, Alt-2, etc. Next steps are numbered. This
   enables precise follow-up ("CA-3 is wrong because...").
5. **Rank by severity and likelihood.** Put the most dangerous
   challenges first. A single FATAL/HIGH item matters more than five
   MINOR/LOW items.
6. **Suggest resolution, not verdict.** For every challenge, specify
   the experiment that would resolve it. The user decides what to
   investigate.
