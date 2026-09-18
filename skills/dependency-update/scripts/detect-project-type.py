#!/usr/bin/env python3
#
# Scans a directory tree for known build files and prints one line per project in the format: <path>: <type>.
#
# Usage: ./detect-project-type.py [root-dir]
# Output: one line per discovered build file: "<relative-path>: <type>"
#         e.g. "modules/cli: go", "modules/framework: java-gradle"
#         If no build files are found, prints nothing and exits 0.

import os
import sys

# Maps build file name → human-readable project type label
BUILD_FILE_MAP = {
    "go.mod": "go",
    "pom.xml": "java-maven",
    "build.gradle": "java-gradle",
    "build.gradle.kts": "java-gradle",
    "package.json": "nodejs",
}

def scan(root: str) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip hidden and common non-source directories
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".")
            and d not in ("node_modules", "vendor", "__pycache__", ".git")
        ]
        for filename in filenames:
            if filename in BUILD_FILE_MAP:
                rel = os.path.relpath(dirpath, root)
                if rel == ".":
                    rel = os.path.basename(os.path.abspath(root))
                project_type = BUILD_FILE_MAP[filename]
                results.append((rel, project_type))
    return results


def main() -> None:
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    if not os.path.isdir(root):
        print(f"error: '{root}' is not a directory", file=sys.stderr)
        sys.exit(1)

    found = scan(root)
    # Deduplicate by path (a dir may have both build.gradle and build.gradle.kts)
    seen: set[str] = set()
    for path, ptype in sorted(found):
        key = path
        if key not in seen:
            seen.add(key)
            print(f"{path}: {ptype}")


if __name__ == "__main__":
    main()
