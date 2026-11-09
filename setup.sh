#!/usr/bin/env bash
# One-shot setup of a fresh Codespace (or any Debian/Ubuntu machine) for this repo.
# Runs automatically when a Codespace is created (.devcontainer/devcontainer.json);
# safe to rerun: every step skips work that is already done.
#
#   bash setup.sh               Python env, data, TeX Live, quick test run
#   bash setup.sh --no-tex      skip TeX Live (only needed to build zpd_darbs/)
#   bash setup.sh --extract     also install soffice/pdftotext/antiword/catdoc
#                               (only needed to rerun the Latvian import, bench/latvia/)
set -euo pipefail
cd "$(dirname "$0")"

TEX=1; EXTRACT=0
for a in "$@"; do
  case "$a" in
    --no-tex) TEX=0 ;;
    --extract) EXTRACT=1 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done
step() { printf '\n==> %s\n' "$*"; }

# 1. Python: newclid 3.0.1 needs >= 3.11; the project was built and tested on 3.13.
PY=${PYTHON:-}
if [ -z "$PY" ]; then
  for c in python3.13 /usr/local/python/3.13*/bin/python3.13 python3.12 python3.11; do
    if command -v "$c" >/dev/null 2>&1; then PY=$c; break; fi
  done
fi
[ -n "$PY" ] || { echo "need Python 3.11-3.13 (set PYTHON=...)" >&2; exit 1; }

step "Newclid venv (.venv-newclid) with $PY, Newclid repo in third_party/"
if [ ! -x .venv-newclid/bin/python ]; then
  PYTHON="$PY" bash ddar/setup_newclid.sh
else
  [ -d third_party/Newclid ] || git clone https://github.com/LMCRC/Newclid.git third_party/Newclid
fi

step "torch (CPU), geo-lm, pyarrow, pytest, matplotlib"
.venv-newclid/bin/python -c "import torch" 2>/dev/null ||
  .venv-newclid/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv-newclid/bin/pip install -q -e geo-lm pyarrow pytest matplotlib

# 2. Training data: the exact 100k GenesisGeo split is kept in git as .gz
#    (3.5 MB instead of a 1 GB download); unpack it next to the archives.
step "GenesisGeo train/val split (data/genesisgeo/)"
for f in train val; do
  if [ ! -s data/genesisgeo/$f.txt ]; then
    gunzip -kf data/genesisgeo/$f.txt.gz
  fi
done
wc -l data/genesisgeo/train.txt data/genesisgeo/val.txt

# 3. System packages.
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
PKGS=()
if [ "$TEX" = 1 ] && ! command -v latexmk >/dev/null; then
  PKGS+=(latexmk lmodern texlive-latex-base texlive-latex-recommended texlive-latex-extra
         texlive-fonts-recommended texlive-lang-european texlive-pictures texlive-xetex)
fi
if [ "$EXTRACT" = 1 ] && ! command -v pdftotext >/dev/null; then
  PKGS+=(poppler-utils antiword catdoc libreoffice-core libreoffice-writer)
fi
if [ ${#PKGS[@]} -gt 0 ]; then
  step "apt: ${PKGS[*]}"
  $SUDO apt-get update -qq
  DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq --no-install-recommends "${PKGS[@]}"
fi

# 4. Check.
step "tests"
.venv-newclid/bin/python -m pytest -q

cat <<'EOF'

Setup done. Next:
  source .venv-newclid/bin/activate
  claude/LOG.md            what happened so far and where to continue
  docs/README.md           how everything fits together
EOF
