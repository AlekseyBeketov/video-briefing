from __future__ import annotations

import os
import stat

import video_briefing.file_permissions as file_permissions


def test_private_file_mode_uses_path_chmod_when_fchmod_is_unavailable(tmp_path, monkeypatch):
    path = tmp_path / "private.txt"
    path.write_text("private", encoding="utf-8")
    monkeypatch.setattr(os, "fchmod", None)
    monkeypatch.setattr(file_permissions, "_WINDOWS", False)

    with path.open("rb") as stream:
        file_permissions.set_private_file_mode(stream.fileno(), path)

    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_missing_windows_fchmod_keeps_secure_mkstemp_acl_path(tmp_path, monkeypatch):
    path = tmp_path / "private.txt"
    path.write_text("private", encoding="utf-8")
    monkeypatch.setattr(os, "fchmod", None)
    monkeypatch.setattr(file_permissions, "_WINDOWS", True)

    with path.open("rb") as stream:
        file_permissions.set_private_file_mode(stream.fileno(), path)
