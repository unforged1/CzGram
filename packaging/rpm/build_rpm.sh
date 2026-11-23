#!/bin/sh
# Builds dist/czgram-<version>-1.<dist>.noarch.rpm from this checkout.
# Needs rpmbuild (Fedora/RHEL: rpm-build; openSUSE: rpm-build) and Pillow for the icon.
set -eu
cd "$(dirname "$0")/../.."
TOP=$(pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

rpmbuild -bb --define "_topdir $WORK" --define "czgram_top $TOP" packaging/rpm/czgram.spec
mkdir -p dist
cp "$WORK"/RPMS/noarch/czgram-*.rpm dist/
ls dist/czgram-*.rpm
