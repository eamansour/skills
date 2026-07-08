---
name: identify-java-dependencies
description: Steps to identify Gradle and Maven project dependencies.
---

## Step 1: Identify All Dependencies

Gather all dependencies declared across all build files.

### Gradle

Read all `build.gradle` files.

Gather dependencies from:
- Gradle platforms or version catalogs
- `dependencies` blocks
- `plugins` blocks

### Maven

Read all `pom.xml` files.

Gather dependencies' `groupId`, `artifactId`, and `version` tags from:
- `<dependencies>`
- `<dependencyManagement>`
- `<build><plugins>`
- `<pluginManagement><plugins>`

Record the source file and line for each dependency identified.

## Step 2: Identify Latest Versions

Fetch the latest available version for **all dependencies at once**.

Use the script [`scripts/maven-latest-version.py`](../scripts/maven-latest-version.py) to look up the latest stable version for all dependencies by supplying the dependencies as `groupId:artifactId` arguments:

```bash
python3 scripts/maven-latest-version.py <groupId>:<artifactId> [<groupId>:<artifactId> ...]
# e.g. python3 scripts/maven-latest-version.py com.fasterxml.jackson.core:jackson-databind org.yaml:snakeyaml
```

Output is one line per dependency in the form `groupId:artifactId:version`. Failures are printed to stderr and do not abort remaining lookups.

## Step 3: Apply Dependency Version Updates

Use the general SKILL.md guidance to apply version updates for Gradle and Maven projects.
