from __future__ import annotations

from app.services.command_filter import is_command_allowed


def test_blocks_rm_root() -> None:
    ok, reason = is_command_allowed("rm -rf /")
    assert ok is False
    assert reason


def test_allows_safe() -> None:
    ok, _ = is_command_allowed("systemctl status nginx")
    assert ok is True
