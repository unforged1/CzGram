#!/bin/sh
# Downloads the README's badges from shields.io into this folder. The README shows these files,
# so the page doesn't depend on shields.io answering GitHub's image proxy in time (it often
# didn't, and badges showed as broken links). Run it again after changing a version or a status.
set -eu
cd "$(dirname "$0")"
VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' ../../czgram/__init__.py)
B=https://img.shields.io/badge
S="style=for-the-badge"

get() {
    curl -fsS --retry 3 -o "$1.tmp" "$2"
    # Badges must be plain SVG with nothing fetched from elsewhere when shown.
    grep -q '<svg' "$1.tmp"
    ! grep -q 'href="http' "$1.tmp"
    mv "$1.tmp" "$1"
}

get version.svg  "$B/version-$VERSION-D97757?$S"
get debian.svg   "$B/Debian%20based-native-A81D33?$S&logo=debian&logoColor=white"
get arch.svg     "$B/Arch%20based-supported-1793D1?$S&logo=archlinux&logoColor=white"
get macos.svg    "$B/macOS-supported-555555?$S&logo=apple&logoColor=white"
get windows.svg  "$B/Windows-experimental-0078D4?$S&logo=windows&logoColor=white"
get rpm.svg      "$B/RHEL%20and%20RPM%20based-supported-EE0000?$S&logo=redhat&logoColor=white"
get security.svg "$B/security-reviewed%20Nov%202026-2EA043?$S"
get license.svg  "$B/license-MIT-4FA8FF?$S"
ls -l ./*.svg
