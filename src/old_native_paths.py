"""Shared read-only resources and writable installation paths.

Source checkouts keep code/resources in src and user data at the project root.
Frozen releases keep resources in PyInstaller's bundle and user data beside
the launcher executable.
"""
from pathlib import Path
import sys


BUNDLE = Path(__file__).resolve().parent
FROZEN = bool(getattr(sys, 'frozen', False))
MOD = Path(sys.executable).resolve().parent if FROZEN else BUNDLE.parent
VENDOR = (BUNDLE if FROZEN else MOD) / 'tools' / 'vendor'

# Source installs may use pip --target tools/vendor. Make those dependencies
# available before importing builders; frozen releases resolve bundled modules.
if not FROZEN and VENDOR.is_dir() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))
