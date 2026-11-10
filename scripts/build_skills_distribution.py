#!/usr/bin/env python3
"""Regenerate skills/martial-arts-research, the folder the skills CLI installs, from package-files.txt."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
NAME = 'martial-arts-research'


def manifest(root):
    return (root / 'package-files.txt').read_text(encoding='utf-8-sig').splitlines()


def build(root, target):
    if target.exists():
        shutil.rmtree(target)
    for name in manifest(root):
        (target / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / name, target / name)


if __name__ == '__main__':
    build(ROOT, ROOT / 'skills' / NAME)
