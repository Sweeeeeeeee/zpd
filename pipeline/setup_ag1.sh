#!/usr/bin/env bash
# AG1 environment: Python 3.10.9 (AG1 README), pinned requirements with hashes, no pip cache.
# jaxlib 0.4.6 is gone from PyPI; the same wheel (hash in requirements.txt) comes
# from Google's JAX bucket: storage.googleapis.com/jax-releases/nocuda/
set -euo pipefail
cd /workspaces/zpd
WHEELS=${WHEELS:?folder with jaxlib-0.4.6-cp310-cp310-manylinux2014_x86_64.whl}
[ -x .venv-ag1/bin/python ] || /opt/conda/bin/conda create -y -q -p .venv-ag1 python=3.10.9 pip
.venv-ag1/bin/python -m pip install -q --no-cache-dir --require-hashes --find-links "$WHEELS" -r third_party/alphageometry/requirements.txt
.venv-ag1/bin/python -m pip install -q --no-cache-dir "setuptools==69.5.1"   # pkg_resources, needed by tensorflow_hub; removed in later setuptools
.venv-ag1/bin/python -c "import jax, tensorflow, flax, t5, gin, sentencepiece; print('imports ok', jax.__version__, tensorflow.__version__)"
du -sh .venv-ag1
