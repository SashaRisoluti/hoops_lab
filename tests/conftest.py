"""Shared pytest configuration: make the repo root importable.

The ``hoops_lab`` package is installed (editable), but ``dashboard`` is an
application folder, not a distributed package — tests importing dashboard
components need the repo root on sys.path.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
