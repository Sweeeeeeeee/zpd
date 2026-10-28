#!/usr/bin/env bash
# Reproducible CPU-only Newclid setup used for step 1.
# Creates .venv-newclid (Python >= 3.11 required by newclid 3.x) and clones the
# Newclid repo into third_party/ for its example problem files.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3.13}
"$PY" -m venv .venv-newclid
.venv-newclid/bin/pip install --upgrade pip
# py-yuclid ships the C++ `yuclid` DDAR binary as a prebuilt wheel.
# pyyaml is imported by newclid but missing from its 3.0.1 metadata.
.venv-newclid/bin/pip install "newclid[yuclid]==3.0.1" pyyaml
[ -d third_party/Newclid ] || git clone https://github.com/LMCRC/Newclid.git third_party/Newclid
echo "Done. Run: source .venv-newclid/bin/activate && python ddar/run_examples.py"
