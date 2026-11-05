#!/usr/bin/env python3
"""Generate the manifest-only directory consumed by the skills CLI."""
import json
from pathlib import Path

from skill_installation import NAME, install


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    print(json.dumps(install(root, [root / 'skills' / NAME]), ensure_ascii=False))
