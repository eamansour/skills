#!/usr/bin/env python3

# Fetches the latest stable release version of one or more Maven artifacts from Maven Central.
#
# Usage:
#   python3 maven-latest-version.py <groupId>:<artifactId> [<groupId>:<artifactId> ...]
#
# Example:
#   python3 maven-latest-version.py commons-io:commons-io
#   python3 maven-latest-version.py com.fasterxml.jackson.core:jackson-databind org.yaml:snakeyaml
#
# Output (one line per dependency):
#   <groupId>:<artifactId>:<latestVersion>
#
# Reads all <version> tags from the maven-metadata.xml and returns the highest
# version that does not contain a pre-release qualifier (e.g. -alpha, -beta, -rc,
# -SNAPSHOT, -M, -EA). Never relies on <release> or <latest> tags as these can
# point to a pre-release version.
#
# Lookup failures are printed to stderr and do not abort remaining lookups.
# The script exits with a non-zero status if any lookup failed.
#
# Requirements: Python 3 standard library only (urllib, xml.etree, re, sys)

import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from functools import cmp_to_key

PRE_RELEASE_PATTERN = re.compile(r'(alpha|beta|rc|snapshot|\.m\d|-m\d|-ea)', re.IGNORECASE)


def parse_version(version_str):
    """Return a tuple of ints for semver sorting, with non-numeric parts as 0."""
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r'[.\-]', version_str))


def compare_versions(a, b):
    pa, pb = parse_version(a), parse_version(b)
    # Pad to equal length
    length = max(len(pa), len(pb))
    pa = pa + (0,) * (length - len(pa))
    pb = pb + (0,) * (length - len(pb))
    if pa < pb:
        return -1
    if pa > pb:
        return 1
    return 0


def fetch_latest_version(group_id, artifact_id):
    """Return the latest stable version string, or raise RuntimeError on failure."""
    group_path = group_id.replace('.', '/')
    url = f'https://repo1.maven.org/maven2/{group_path}/{artifact_id}/maven-metadata.xml'

    try:
        with urllib.request.urlopen(url) as response:
            xml_content = response.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'Could not fetch metadata from {url} (HTTP {e.code})')
    except urllib.error.URLError as e:
        raise RuntimeError(f'Could not fetch metadata from {url}: {e.reason}')

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise RuntimeError(f'Failed to parse XML from {url}: {e}')

    all_versions = [el.text for el in root.iter('version') if el.text]

    if not all_versions:
        raise RuntimeError(f'No <version> tags found in metadata from {url}')

    stable_versions = [v for v in all_versions if not PRE_RELEASE_PATTERN.search(v)]

    if not stable_versions:
        raise RuntimeError(f'No stable release versions found for {group_id}:{artifact_id}')

    return max(stable_versions, key=cmp_to_key(compare_versions))


def main():
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} <groupId>:<artifactId> [<groupId>:<artifactId> ...]', file=sys.stderr)
        sys.exit(1)

    failed = False
    for arg in sys.argv[1:]:
        if ':' not in arg:
            print(f'ERROR: Invalid dependency format "{arg}" — expected <groupId>:<artifactId>', file=sys.stderr)
            failed = True
            continue

        group_id, artifact_id = arg.split(':', 1)
        try:
            version = fetch_latest_version(group_id, artifact_id)
            print(f'{group_id}:{artifact_id}:{version}')
        except RuntimeError as e:
            print(f'ERROR: {e}', file=sys.stderr)
            failed = True

    if failed:
        sys.exit(1)


if __name__ == '__main__':
    main()
