"""Run the tool: `python3 <pack>/tools/shared/umlmodel [...]`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from umlmodel.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
