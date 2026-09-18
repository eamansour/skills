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
deterministic scripts. There are two outcomes:

- **Full replacement** — every step is scriptable. The SKILL.md body is replaced with a minimal
  wrapper that runs the scripts; the original prose instructions are removed entirely.
- **Partial replacement** — some steps are scriptable. Each scriptable section is rewritten to
  call its script; non-scriptable sections are preserved verbatim.

In both cases, verify that no functional behaviour is lost.

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

Search for the skill by scanning all `skills/` directories under any root-level folder in the
workspace (i.e., directories of the form `<root-dir>/skills/` where `<root-dir>` is a direct
child of the workspace root, including the workspace root itself). Do **not** hard-code any
specific folder names.

1. List the top-level directories and the workspace root itself.
2. For each candidate, check whether `<candidate>/skills/<skill-name>/SKILL.md` exists.
3. Use the first match found as the **skill root** (`<skill-root>`), e.g.
   `.agents/skills/dependency-update` or `skills/dependency-update`.
4. If no match is found across any candidate, report:
   > "Could not find a skill named `<skill-name>`. Searched for `skills/<skill-name>/SKILL.md`
   > under every root-level folder in the workspace."
   Then stop without modifying anything.

Carry `<skill-root>` forward — use it as the base path in all subsequent steps.

---

## Step 2 — Explore the skill via subagent

Spawn a subagent to read and analyse the target skill. Pass it the following description,
substituting the resolved `<skill-root>` path:

> Read `<skill-root>/SKILL.md` (full content). Also list any files in
> `<skill-root>/scripts/` (if the directory exists).
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

Produce a verdict table based on the results of the evaluation, for example:

| Step ID | Heading | Scriptable? | Reason | Proposed script | Language |
|---------|---------|-------------|--------|-----------------|----------|
| 1 | Detect project type | ✅ Yes | Deterministic file scan | `detect-project-type.py` | python |
| 2 | Risk assessment | ❌ No | Requires NL interpretation of release notes | — | — |

Show this table to the user.

**If no steps are scriptable:**
> "No steps in `<skill-name>` qualify for scripting. This skill relies on LLM reasoning
> throughout and cannot be meaningfully optimised by scripts."
>
> List the per-step reasons. Stop — do not modify any files.

**If every step is scriptable (full replacement):** note this and continue to Step 4 with
`mode = full-replacement`.

**If some (but not all) steps are scriptable (partial replacement):** continue to Step 4 with
`mode = partial-replacement`.

---

## Step 4 — Generate scripts

**Determine the scripting language** before writing any scripts:

- If the subagent found existing scripts in `<skill-root>/` or `<skill-root>/scripts/`, inspect their
  extensions and shebangs to identify the language already in use (e.g. `.sh` → bash,
  `.py` → Python). Use that same language for all new scripts.
- If there are no existing scripts, default to **Python** (`.py`, `#!/usr/bin/env python3`)
  for better cross-platform compatibility.

For each step marked ✅ scriptable:

1. **Determine the script filename.** Use the proposed name from the verdict table (kebab-case,
   appropriate extension matching the chosen language: `.sh` for bash, `.py` for Python).
2. **Avoid collisions.** If a file with that name already exists in
   `<skill-root>/scripts/`, append an incrementing integer before the extension
   (e.g., `detect-project-type-2.py`).
3. **Write the script** to `<skill-root>/scripts/<filename>` using `write_file`.

Every generated script MUST begin with:
```
#!/usr/bin/env python3       # (or #!/usr/bin/env bash if the skill uses bash)
#
# <one-sentence description of what this script does>
#
# Usage: ./<script-name> [args]
# Output: <description of stdout format>
```

After writing each script, show: `✓ Created <skill-root>/scripts/<filename>`

---

## Step 5 — Patch the SKILL.md

Before making any edits, hold the **original full content** of the target SKILL.md in memory
(you will need it for verification in Step 6).

### Full replacement (mode = full-replacement)

Replace the entire SKILL.md body with a minimal wrapper. Keep the original frontmatter
(everything between and including the `---` delimiters) unchanged. Replace everything after
the closing `---` of the frontmatter with:

```
# <skill-name>

> This skill is fully implemented as scripts. The steps below invoke them in order.

## Usage

Run the following scripts in sequence:

1. **<script-1-description>**
   ```
   python3 <skill-root>/scripts/<script-1>
   ```
   Output: <expected stdout format>

2. **<script-2-description>**
   ```
   python3 <skill-root>/scripts/<script-2>
   ```
   Output: <expected stdout format>

Act on each script's output as described before running the next.
```

Add an entry for each generated script. Use the script's header comment as the source for its
description and output format.

### Partial replacement (mode = partial-replacement)

For each scriptable step, rewrite its SKILL.md section to call the generated script instead of
describing the work in prose. The replacement prose should:

- Call the script with `execute_command`
- Describe the expected stdout format
- Explain how the LLM should act on the output

**Non-scriptable sections must be preserved verbatim.** Do not alter headings, wording, or
structure of any section that was not scripted.

Example replacement pattern (using the resolved `<skill-root>` path):

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
    python3 <skill-root>/scripts/detect-project-type.py
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

**For full replacement:** confirm that every step from the original inventory has a
corresponding script entry in the new SKILL.md wrapper. Each script must be listed with its
description and output format.

**For partial replacement:** for each step in the original SKILL.md:

- ✅ **Preserved** — the section is still present verbatim in the updated SKILL.md, OR
- ✅ **Replaced** — the section has a script call whose description covers the same semantics
  as the original prose

**Pass condition (either mode):** every original step is accounted for.

> **Verification passed.** The updated skill is functionally equivalent to the original.
> Scripts created:
> - `<skill-root>/scripts/<script1>` — <one-line purpose>
> - `<skill-root>/scripts/<script2>` — <one-line purpose>

**Fail condition:** one or more original steps are not accounted for.

> **Verification failed.** The following steps are not accounted for in the updated SKILL.md:
> - Step N: <heading>
>
> Reverting SKILL.md to its original content. The generated scripts have been kept in
> `<skill-root>/scripts/` for reference.

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
| Script | Replaces | Language |
|--------|----------|----------|
| scripts/<script-name> | <step or "entire skill"> | <language> |

**Replacement mode:** full / partial

The skill has been updated. Commit both `SKILL.md` and the new scripts together.
Note: if bash scripts were generated, they require a POSIX-compatible shell and will not run
on Windows without WSL or Git Bash. Python scripts run cross-platform provided Python 3 is installed.
```
