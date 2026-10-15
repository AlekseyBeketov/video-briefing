"""Small cross-platform helpers for private application files."""
from __future__ import annotations

import os
from pathlib import Path

_WINDOWS = os.name == "nt"


def set_private_file_mode(descriptor: int, path: Path) -> None:
    """Restrict a file where POSIX mode bits are supported.

    Python added Windows ``os.fchmod`` support in 3.13. On older Windows
    versions, ``mkstemp`` creates the file under the current user's ACL and
    permission bits cannot further restrict access, so retain that inherited
    protection without failing setup.
    """
    fchmod = getattr(os, "fchmod", None)
    if fchmod is not None:
        fchmod(descriptor, 0o600)
    elif not _WINDOWS:
        os.chmod(path, 0o600)
