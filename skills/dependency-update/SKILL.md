---
name: dependency-update
description: >
    Update project dependencies. Runs a pre-flight build, identifies new versions, creates a risk assessment, updates dependencies, and produces a report.
    Use this skill when the user wants to review project dependencies and update dependencies, including to remediate vulnerabilities.
---

# Dependency Update Skill

## IMPORTANT

- If a repository has several sub-projects/modules, ask the user what project(s) they would like to update.

## Step 1: Pre-flight checks

### Detect project type

Run the detection script:

```bash
python3 skills/dependency-update/scripts/detect-project-type.py [root-dir]
```

The script walks the directory tree from `root-dir` (defaults to `.`) and prints one line per
discovered build file in the format `<path>: <type>` (e.g. `modules/cli: go`,
`modules/framework: java-gradle`, `modules/obr: java-maven`). Use this output to record which
build systems are present in each sub-project before proceeding.

### Verify required tools are installed

Run the tool-verification script:

```bash
python3 skills/dependency-update/scripts/verify-tools.py [root-dir]
```

The script scans the same directory tree and prints one line per build file it finds:
`OK <tool>` when the tool is present, or `MISSING <tool> (required by <build-file>)` when it
is absent. It exits with code 1 if any tool is missing.

If the script prints any `MISSING` lines or exits non-zero, stop and report the missing tools
to the user before proceeding.

### Run a clean build

**ESSENTIAL: You MUST refer to the project or sub-project's closest README.md or AGENTS.md to find out how it must be built. If the project uses a build script, you MUST run that script perform the build.**

- **If a `build-locally.sh` or similar exists and that is the documented way to build the project: you MUST run it.** There are no exceptions. Do NOT substitute it with a raw build command (`go test`, `mvn install`, `gradle build`, etc.) for any reason — not because the script takes longer, not because it has external dependencies, not because individual stages seem unrelated to your changes.
- If no build script exists anywhere in the repository: only then run the appropriate raw build command for the project type.

If the build fails, stop and report to the user before proceeding.

**Partial failures:** If compilation and unit tests pass but integration or end-to-end tests fail, do NOT proceed silently. Surface the failure to the user, describe the stage that failed and the error, and ask whether to continue. Only proceed with dependency updates if the user confirms the failure is a pre-existing environment issue unrelated to the code.

**Environment prerequisite failures:** If a build fails because a required tool or remote resource is unavailable (e.g. Gradle cannot reach a Maven repository, a code generator jar cannot be downloaded), NEVER silently fall back to a lighter build. Report the failure to the user, explain which stage failed and why, and stop.


## Step 2: Launch per-build-system sub-tasks

A module may use more than one build system (e.g. a Go module that also contains a `build.gradle` to download Java tooling). Scan the module directory for **all** build files present:

| Build file found | Language file |
|------------------|---------------|
| `go.mod` | [languages/go.md](./languages/go.md) |
| `build.gradle` / `pom.xml` | [languages/java.md](./languages/java.md) |
| `package.json` | [languages/nodejs.md](./languages/nodejs.md) |

**For each build file found, launch a sub-task using `start_subtask`.** Each sub-task is responsible for one build system only and must complete the full identify → risk-assess → update → verify cycle for that system. Pass the relevant context (module path, build file path, language file to use) in the sub-task message.

Use the following todo list for each sub-task:
```
[ ] Identify dependencies (load and follow the language file steps)
[ ] Classify each dependency (up-to-date / patch-available / minor-available / major-available)
[ ] Risk assessment
[ ] Apply updates
[ ] Verify updates (read the build file and confirm versions)
[ ] Return results summary to parent task
```

Run sub-tasks **sequentially**, not in parallel — each one may modify shared build files and the post-update build must be clean before the next sub-task starts.

Wait for each sub-task to complete and collect its results summary before proceeding to Step 3.


## Step 3: Final Report

Produce a summary report of all dependency update activity using the outcome records returned by the sub-tasks.

### Outcome statuses

| Status | Meaning |
|--------|---------|
| `updated` | Version bump applied and build passes |
| `updated with migration` | Version bump applied with code changes required; build passes |
| `patch-blocked` | Patch update caused a build failure that could not be resolved; reverted |
| `minor-blocked` | Minor update caused a non-trivial build failure; reverted |
| `major-blocked` | Major update caused a non-trivial build failure; reverted |
| `up-to-date` | No update was needed |

### Report structure

Produce one table per build system that was in scope.

| Dependency | Old Version | New Version | Status | Notes |
|------------|-------------|-------------|--------|-------|
| `com.example:library` | `1.2.0` | `1.2.5` | `updated` | |
| `com.example:other` | `2.0.0` | `3.0.0` | `major-blocked` | Removed API `Foo.bar()` — non-trivial migration required |

After each table, include:
- A one-line summary: how many dependencies were updated, how many were blocked, how many were already up-to-date.
- If any dependencies are blocked, list the next recommended actions (e.g. link to the relevant migration guide, suggest raising a separate ticket).


## Sub-task instructions: Identify, assess, update, and verify dependencies

> These instructions are for use inside a per-build-system sub-task launched from Step 2.

### Identify all dependencies

Load the language file for this build system and follow its identification steps to collect every versioned dependency declared in the build file. Classify each one:

| Status | Meaning |
|--------|---------|
| `up-to-date` | Already on latest |
| `major-available` | New major release (**X**.y.z) |
| `minor-available` | New minor release (x.**Y**.z) |
| `patch-available` | New patch release (x.y.**Z**) |

### Risk Assessment

For any dependencies that are not classified as `up-to-date`:

| Status | Steps |
|--------|---------|
| `major-available` or `minor-available` | Use the GitHub API (`https://api.github.com/repos/<owner>/<repo>/releases`) to get a release and scan release notes/CHANGELOG.md for migration guidance, breaking API changes, any new prerequisites (e.g. language version changes), license changes |
| `patch-available` | Mark as low risk |

### Apply Dependency Updates

Follow the language file instructions to apply updates. General rules:

#### Apply all patch updates at once

Apply every `patch-available` version bump in one go by editing the build files, then run a full build using `build-locally.sh` (or equivalent). Do NOT use raw build commands.

If the build passes:
- All patches are done, record each one as **updated**

If the build fails:
- Identify the problematic patch(es) by:
    1. Reverting half of the patches that were applied
    2. Rebuilding the project
    3. If the rebuild fails, repeat from step 1. If the rebuild passes, record the problematic patches with **patch-blocked**.

#### Apply minor and major updates one by one

Go through each `minor-available` and `major-available` dependency update, starting with minor updates.

For each dependency:
1. Update the version in the build file.
2. Run the build in the exact same way that it was built previously.
3. If the build passes - Record as **updated**. If the build fails - find out why it failed:
   - Check if the error matches a breaking change from the release notes/CHANGELOG.md (e.g. deprecated/removed methods, package import changes).
   - If you can't determine the reason: Revert the version bump, record as **<major/minor>-blocked** with the error encountered.
   - If a simple fix exists: Apply the fix, rebuild. If the build passes: Record as **updated with migration**. If the build fails: Revert the changes and dependency version update and record as **<major/minor>-blocked**.
   - If the fix is not simple: Revert the version bump, record as **<major/minor>-blocked** with the failure reason.

### Verify Updates

Read the updated build file(s) directly and confirm that each dependency's version reflects the new value. If any version does not match, re-apply the update before proceeding.

### Return results summary

Return a table of all dependencies processed with their old version, new version, and outcome status. This will be collected by the parent task for the final report.
