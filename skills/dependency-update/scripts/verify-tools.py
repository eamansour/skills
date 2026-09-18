#!/usr/bin/env python3
#
# Checks that each build-file-to-tool mapping has the required tool installed and exits non-zero if any are missing.
#
# Usage: ./verify-tools.py [root-dir]
# Output: one line per build file found: "OK <tool>" or "MISSING <tool> (required by <build-file>)"
#         Exits 0 if all required tools are present; exits 1 if any are missing.

import os
import shutil
import sys

# Maps build file name → list of acceptable tool names (first found wins)
TOOL_MAP: dict[str, list[str]] = {
    "go.mod": ["go"],
    "pom.xml": ["mvn"],
    "build.gradle": ["gradlew", "gradle"],
    "build.gradle.kts": ["gradlew", "gradle"],
    "package.json": ["npm", "yarn"],
}


def find_build_files(root: str) -> list[tuple[str, str]]:
    """Return (dirpath, build_file_name) pairs, skipping non-source dirs."""
    results: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".")
            and d not in ("node_modules", "vendor", "__pycache__", ".git")
        ]
        for filename in filenames:
            if filename in TOOL_MAP:
                results.append((dirpath, filename))
    return results


def check_tool(dirpath: str, build_file: str) -> tuple[bool, str]:
    """
    Return (ok, message).  For gradlew we first check for a local wrapper
    script in the same directory before falling back to the global `gradle`.
    """
    candidates = TOOL_MAP[build_file]
    for tool in candidates:
        if tool == "gradlew":
            wrapper = os.path.join(dirpath, "gradlew")
            if os.path.isfile(wrapper) and os.access(wrapper, os.X_OK):
                return True, f"OK gradlew  (local wrapper at {os.path.relpath(wrapper)})"
        elif shutil.which(tool) is not None:
            return True, f"OK {tool}"
    # None found
    display = " or ".join(candidates)
    rel = os.path.relpath(os.path.join(dirpath, build_file))
    return False, f"MISSING {display}  (required by {rel})"


def main() -> None:
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    if not os.path.isdir(root):
        print(f"error: '{root}' is not a directory", file=sys.stderr)
        sys.exit(1)

    build_files = find_build_files(root)
    if not build_files:
        print("No build files found — nothing to check.")
        sys.exit(0)

    missing = False
    # Deduplicate by directory so we don't report the same gradlew twice
    seen: set[str] = set()
    for dirpath, build_file in sorted(build_files):
        key = f"{dirpath}:{build_file}"
        if key in seen:
            continue
        seen.add(key)
        ok, message = check_tool(dirpath, build_file)
        print(message)
        if not ok:
            missing = True

    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
