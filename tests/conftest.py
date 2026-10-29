import os
import sys
from pathlib import Path

# py_yuclid finds the yuclid binary through PATH.
os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")

ORTHOCENTER = "a b c = triangle a b c; h = on_tline h b a c, on_tline h c a b ? perp a h b c"
