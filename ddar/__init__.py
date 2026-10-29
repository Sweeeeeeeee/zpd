"""Newclid DDAR: configs with rule toggling, solver construction, runners."""

import os
import sys
from pathlib import Path

# py_yuclid finds the yuclid binary through PATH; make it work without an
# activated venv by adding this interpreter's bin directory.
_venv_bin = str(Path(sys.executable).parent)
if _venv_bin not in os.environ.get("PATH", "").split(os.pathsep):
    os.environ["PATH"] = _venv_bin + os.pathsep + os.environ.get("PATH", "")
