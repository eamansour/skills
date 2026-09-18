---
name: scriptify
description: >
  Analyse an existing agent skill and optimise it by replacing deterministic LLM steps with
  scripts. Use when the user wants to optimise, or speed up an existing skill by
  extracting mechanical steps into runnable scripts.
metadata:
  argument-hint: <skill-name>
---

# Scriptify Skill

Analyse an existing agent skill and decide whether any of its steps can be replaced by
deterministic scripts. If scriptable steps exist, generate the scripts and update the skill's
`SKILL.md` to call them. Verify that no functional behaviour is lost.

## Scriptability Criteria

A step qualifies for scripting only when **ALL** of the following hold:

| Criterion | Description |
|-----------|-------------|
| Deterministic inputs | Inputs come from files on disk, environment variables, or command output — not from user prose or LLM reasoning |
| Fixed-structure output | Output is a list, version string, boolean, or other predictable format — not a natural-language summary |
| No NL interpretation | The step does not require understanding free-form text, making a judgment call, or choosing between ambiguous alternatives |
| Self-contained | The script can be written without additional context from the user beyond what is already in the skill |

When in doubt, **leave the step with the LLM**. A conservative miss is better than a broken script.

---

## Step 1 — Resolve the target skill

The argument after `/scriptify` is the skill name (e.g., `/scriptify dependency-update`).

1. Derive the expected SKILL.md path: `skills/<skill-name>/SKILL.md` (relative to workspace root).
   Also check `.agents/skills/<skill-name>/SKILL.md` if not found in the workspace.
2. If the file cannot be found in either location, report:
   > "Could not find a skill named `<skill-name>`. Expected at `skills/<skill-name>/SKILL.md`."
   Then stop without modifying anything.

---

## Step 2 — Explore the skill via subagent

Spawn a subagent to read and analyse the target skill. Pass it the following description:

> Read `skills/<skill-name>/SKILL.md` (full content). Also list any files in
> `skills/<skill-name>/scripts/` (if the directory exists).
>
> Return a structured step inventory as a markdown table with these columns:
> - **Step ID** — sequential number (1, 2, 3 …)
> - **Heading** — the section heading or a brief label if there is no heading
> - **Summary** — one sentence describing what the step does
> - **Inputs** — what data the step consumes (files, env vars, user input, prior LLM output)
> - **Outputs** — what the step produces (a file list, a decision, a report, etc.)
>
> After the table, list any scripts already present in the `scripts/` directory (name + one-line
> purpose). Return only the inventory and scripts list — no additional commentary.

Wait for the subagent to return before proceeding.

---

## Step 3 — Assess scriptability

Evaluate each row in the subagent's inventory against the **Scriptability Criteria** table above.

Produce a verdict table, for example:

| Step ID | Heading | Scriptable? | Reason | Proposed script | Language |
|---------|---------|-------------|--------|-----------------|----------|
| 1 | Detect project type | ✅ Yes | Deterministic file scan | `detect-project-type.sh` | bash |
| 2 | Risk assessment | ❌ No | Requires NL interpretation of release notes | — | — |

Show this table to the user.

**If no steps are scriptable:**
> "No steps in `<skill-name>` qualify for scripting. This skill relies on LLM reasoning
> throughout and cannot be meaningfully optimised by scripts."
>
> List the per-step reasons. Stop — do not modify any files.

**If at least one step is scriptable:** continue to Step 4.

---

## Step 4 — Generate scripts

For each step marked ✅ scriptable:

1. **Determine the script filename.** Use the proposed name from the verdict table (kebab-case,
   appropriate extension: `.sh` for bash, `.py` for Python).
2. **Avoid collisions.** If a file with that name already exists in
   `skills/<skill-name>/scripts/`, append an incrementing integer before the extension
   (e.g., `detect-project-type-2.sh`).
3. **Write the script** to `skills/<skill-name>/scripts/<filename>` using `write_file`.

Every generated script MUST begin with:
```
#!/usr/bin/env bash          # (or #!/usr/bin/env python3)
#
# <one-sentence description of what this script does>
#
# Usage: ./<script-name> [args]
# Output: <description of stdout format>
```

After writing each script, show: `✓ Created skills/<skill-name>/scripts/<filename>`

---

## Step 5 — Patch the SKILL.md

Before making any edits, hold the **original full content** of the target SKILL.md in memory
(you will need it for verification in Step 6).

For each scriptable step, rewrite its SKILL.md section to call the generated script instead of
describing the work in prose. The replacement prose should:

- Call the script with `execute_command`
- Describe the expected stdout format
- Explain how the LLM should act on the output

**Non-scriptable sections must be preserved verbatim.** Do not alter headings, wording, or
structure of any section that was not scripted.

Example replacement pattern:

Before:
```
### Detect project type

Scan for package files (e.g. build.gradle, pom.xml, go.mod, package.json) to identify the
type of project and the relevant build tool/package manager to use.
```

After:
```
### Detect project type

Run the detection script:
    ```bash
    bash skills/<skill-name>/scripts/detect-project-type.sh
    ```

The script prints one line per detected project in the format `<path>: <type>` (e.g.
`modules/cli: go`, `modules/framework: gradle`). Use this output to determine which build
systems are present before proceeding.
```

---

## Step 6 — Verify functional equivalence

After patching, verify that nothing has been lost.

For each step in the **original** SKILL.md (from the copy you held in memory):

- ✅ **Preserved** — the section is still present verbatim in the updated SKILL.md, OR
- ✅ **Replaced** — the section has a script call whose description covers the same semantics as
  the original prose

If every step is either Preserved or Replaced:

> **Verification passed.** The updated skill is functionally equivalent to the original.
> Scripts created:
> - `skills/<skill-name>/scripts/<script1>` — <one-line purpose>
> - `skills/<skill-name>/scripts/<script2>` — <one-line purpose>

If any step is neither Preserved nor Replaced (i.e., content was dropped):

> **Verification failed.** The following steps are not accounted for in the updated SKILL.md:
> - Step N: <heading>
>
> Reverting SKILL.md to its original content. The generated scripts have been kept in
> `skills/<skill-name>/scripts/` for reference.

Revert by overwriting the patched SKILL.md with the original content you held in memory.
Then stop and ask the user how to proceed.

---

## Step 7 — Summary

On success, show:

```
## Scriptify complete: <skill-name>

**Scripts created:** N
**Sections updated:** N
**Verification:** ✅ Passed — all original steps accounted for

### Changes made
| Script | Replaces section | Language |
|--------|-----------------|----------|
| scripts/<skill-name>.sh | <section-replaced> | <language> |

The skill has been updated. Commit both `SKILL.md` and the new scripts together.
Note: generated bash scripts require a POSIX-compatible shell. They will not run on Windows
without WSL or Git Bash.
```
