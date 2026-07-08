---
name: identify-go-dependencies
description: Steps to identify Go module dependencies and apply version updates.
---

## Useful Commands

| Command | Purpose |
|---------|---------|
| go mod tidy | Add missing dependencies and remove unused ones
| go mod download | Download modules to local cache
| go mod verify | Verify cached modules match go.sum checksums
| go mod vendor | Copy dependencies into vendor/directory
| go mod edit | Edit go.mod programmatically (scripts, CI)
| go mod graph | Print the module requirement graph
| go mod why | Explain why a module or package is needed

## Step 1: Identify All Dependencies

Collect every versioned dependency declared across all `go.mod` files in the repository.

Find every `go.mod` file (e.g. `modules/cli/go.mod`, `modules/buildutils/go.mod`, `modules/buildutils/openapi2beans/go.mod`) and read each `require` block. For every entry capture:

| Field | Description |
|-------|-------------|
| Module path | The full module path (e.g. `github.com/spf13/cobra`) |
| Version | The pinned version string (e.g. `v1.8.0`) |
| Direct / Indirect | Indirect dependencies are marked with `// indirect` at the end of the line |
| Source file | Path to the `go.mod` file |
| Line | Line number of the `require` directive |

Focus upgrade efforts on **direct** dependencies first. Indirect dependencies can be left to `go mod tidy` unless a specific version is required for a security fix.

## Step 2: Identify Latest Versions

Fetch the latest available version for each dependency by running the following command in the directory containing `go.mod`:

```bash
go list -m -u all
```

The output is in the form:
```
dependency version [new version]
```

Example:
```
github.com/galasa-dev/cli
github.com/cpuguy83/go-md2man/v2 v2.0.7
github.com/davecgh/go-spew v1.1.1
github.com/golang-jwt/jwt/v5 v5.3.0 [v5.3.1]
```

Where `[new version]` only appears if there is an update available.

This will also list the current project's module (e.g. github.com/galasa-dev/cli), ignore this.

> **Important:** `go list -m -u all` reports updates for the **entire module graph** — including transitive dependencies that are not pinned in `go.mod`. Only packages that appear explicitly in a `require` block in `go.mod` are candidates for a direct version bump. Packages listed by `go list -m -u` but absent from `go.mod` are managed transitively and should not be manually updated; `go mod tidy` will resolve them appropriately.

Cross-reference the `go list -m -u all` output against the `require` blocks in `go.mod`. Only act on entries that are present in `go.mod`.

**If all packages in `go.mod` are already at their latest versions:** run `go mod tidy` to confirm the file is clean (no output = clean), then conclude — no further updates are required.


## Step 3: Apply Dependency Version Updates

For each dependency that has a newer version available **and is explicitly pinned in `go.mod`**, run the following commands in the directory containing `go.mod`:

```bash
go get <module-path>@<new-version> # Update specific package
go mod tidy
go test ./...
go vet ./...
```

If any of the commands fail at any point, mark the dependency as **<major/minor/patch>-blocked** based on the classification.

**Validation alignment:** `go test ./...` and `go vet ./...` are the minimum acceptable validation for each individual dependency update. If the project has a `build.sh` or equivalent, run it as a final validation pass after all updates have been applied, to catch any issues that raw `go test` would not surface (e.g. linting, code generation, documentation).