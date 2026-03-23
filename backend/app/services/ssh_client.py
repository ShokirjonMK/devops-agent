from __future__ import annotations

import io
import os
from pathlib import Path
from typing import TYPE_CHECKING

import paramiko

if TYPE_CHECKING:
    from app.models import Server


class SSHRunResult:
    def __init__(self, stdout: str, stderr: str, exit_code: int) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code

    @property
    def combined(self) -> str:
        parts = []
        if self.stdout:
            parts.append(self.stdout.rstrip())
        if self.stderr:
            parts.append("[stderr]\n" + self.stderr.rstrip())
        return "\n".join(parts) if parts else "(no output)"


class SSHExecutor:
    def __init__(self, server: Server, connect_timeout: int, command_timeout: int) -> None:
        self.server = server
        self.connect_timeout = connect_timeout
        self.command_timeout = command_timeout
        self._client: paramiko.SSHClient | None = None

    def __enter__(self) -> SSHExecutor:
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        key = self._load_private_key()
        connect_kw: dict = {
            "hostname": self.server.host,
            "username": self.server.user,
            "timeout": self.connect_timeout,
            "allow_agent": False,
            "look_for_keys": False,
        }
        if key is not None:
            connect_kw["pkey"] = key
        elif os.environ.get("SSH_PASSWORD"):
            connect_kw["password"] = os.environ["SSH_PASSWORD"]
        self._client.connect(**connect_kw)
        return self

    def __exit__(self, *args: object) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def _load_private_key(self) -> paramiko.PKey | None:
        key_b64 = os.environ.get("SSH_PRIVATE_KEY_B64")
        if key_b64:
            import base64

            raw = base64.b64decode(key_b64)
            for key_cls in (
                paramiko.RSAKey,
                paramiko.Ed25519Key,
                paramiko.ECDSAKey,
            ):
                try:
                    return key_cls.from_private_key(io.BytesIO(raw))
                except Exception:
                    continue
            raise ValueError("Could not parse SSH_PRIVATE_KEY_B64")
        path = self.server.key_path
        if not path:
            return None
        expanded = Path(path).expanduser()
        if not expanded.is_file():
            raise FileNotFoundError(f"SSH key not found: {expanded}")
        for key_cls in (
            paramiko.RSAKey,
            paramiko.Ed25519Key,
            paramiko.ECDSAKey,
        ):
            try:
                return key_cls.from_private_key_file(str(expanded))
            except Exception:
                continue
        raise ValueError(f"Unsupported or invalid key file: {expanded}")

    def run(self, command: str) -> SSHRunResult:
        if not self._client:
            raise RuntimeError("SSH not connected")
        stdin, stdout, stderr = self._client.exec_command(command, timeout=self.command_timeout)
        stdin.close()
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        code = stdout.channel.recv_exit_status()
        return SSHRunResult(out, err, code)
