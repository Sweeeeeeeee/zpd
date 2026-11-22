#!/usr/bin/env bash
# Install the Newclid datasets used in the published geometry benchmarks.
set -euo pipefail
cd "$(dirname "$0")/.."
dest=third_party/Newclid
revision=ac6550732a950564cf7614d605b5bf1eadd29701

if [[ -d "$dest" ]]; then
  if [[ "$(git -C "$dest" rev-parse HEAD 2>/dev/null || true)" != "$revision" ]]; then
    echo "Using existing $dest. Published runs used Newclid revision $revision." >&2
  fi
  exit 0
fi
mkdir -p third_party
temp=$(mktemp -d third_party/.newclid-XXXXXXXX)
trap 'rm -rf -- "$temp"' EXIT
git clone --no-checkout https://github.com/LMCRC/Newclid.git "$temp"
git -C "$temp" checkout --quiet --detach "$revision"
mv -T "$temp" "$dest"
