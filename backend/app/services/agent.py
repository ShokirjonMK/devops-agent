from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AuditLog, Server, Task, TaskStatus, TaskStep, StepStatus
from app.services.command_filter import is_command_allowed
from app.services.llm import complete_json
from app.services.ssh_client import SSHExecutor


class DevOpsAgent:
    def __init__(self, db: Session, task_id: int) -> None:
        self.db = db
        self.task_id = task_id
        self.settings = get_settings()
        self._order = 0

    def _task(self) -> Task | None:
        return self.db.get(Task, self.task_id)

    def _log(self, message: str, level: str = "info") -> None:
        t = self._task()
        if not t:
            return
        self.db.add(AuditLog(task_id=t.id, message=message, level=level))
        self.db.commit()

    def _next_step_order(self) -> int:
        self._order += 1
        return self._order

    def _add_step(
        self,
        command: str | None,
        output: str | None,
        status: str,
    ) -> None:
        t = self._task()
        if not t:
            return
        self.db.add(
            TaskStep(
                task_id=t.id,
                step_order=self._next_step_order(),
                command=command,
                output=(output or "")[:65000],
                status=status,
            )
        )
        self.db.commit()

    def _servers_payload(self, servers: list[Server]) -> str:
        return json.dumps(
            [{"name": s.name, "host": s.host, "id": s.id} for s in servers],
            ensure_ascii=False,
        )

    def _match_server(self, servers: list[Server], name_hint: str | None) -> Server | None:
        if not name_hint:
            return None
        hint = name_hint.strip().lower()
        for s in servers:
            if s.name.lower() == hint:
                return s
        for s in servers:
            if hint in s.name.lower() or s.name.lower() in hint:
                return s
        return None

    def run(self) -> None:
        task = self._task()
        if not task:
            return
        task.status = TaskStatus.running.value
        self.db.commit()

        servers = self.db.query(Server).order_by(Server.name).all()
        if not servers:
            self._fail("Hech qanday server ro‘yxatga kiritilmagan. Avval Web UI orqali server qo‘shing.")
            return

        try:
            intent = self._parse_intent(task.command_text, servers)
        except Exception as e:
            self._fail(f"AI intent xatosi: {e}")
            return

        server_name = intent.get("server_name")
        server = task.server_id and self.db.get(Server, task.server_id)
        if not server:
            server = self._match_server(servers, server_name if isinstance(server_name, str) else None)
        if not server:
            self._fail(
                "Server aniqlanmadi. Buyruqda server nomini yozing yoki server_id bering. "
                f"Mavjud serverlar: {', '.join(s.name for s in servers)}"
            )
            return

        task.server_id = server.id
        self.db.commit()
        self._log(f"Server aniqlandi: {server.name} ({server.host})")

        history: list[dict[str, Any]] = []

        diag_cmds = intent.get("diagnostic_commands") or []
        if not isinstance(diag_cmds, list):
            diag_cmds = []
        diag_cmds = [str(c).strip() for c in diag_cmds if str(c).strip()][:12]

        if not diag_cmds:
            diag_cmds = [
                "uptime",
                "df -h",
                "free -m",
                "ss -tulnp 2>/dev/null || netstat -tulnp 2>/dev/null || true",
            ]

        try:
            with SSHExecutor(
                server,
                self.settings.ssh_connect_timeout,
                self.settings.ssh_command_timeout,
                self.settings.ssh_connect_retries,
                self.settings.ssh_retry_backoff_seconds,
            ) as ssh:
                self._log("SSH ulanish: OK")
                for cmd in diag_cmds:
                    ok, reason = is_command_allowed(cmd)
                    if not ok:
                        self._add_step(cmd, reason, StepStatus.skipped.value)
                        history.append({"command": cmd, "output": reason, "skipped": True})
                        continue
                    self._add_step(cmd, None, StepStatus.running.value)
                    try:
                        res = ssh.run(cmd)
                        out = res.combined[:60000]
                        st = StepStatus.success.value if res.exit_code == 0 else StepStatus.error.value
                        self._update_last_step_output(task.id, out, st)
                        history.append({"command": cmd, "output": out, "exit_code": res.exit_code})
                    except Exception as ex:
                        self._update_last_step_output(task.id, str(ex), StepStatus.error.value)
                        history.append({"command": cmd, "output": str(ex), "error": True})

                for iteration in range(self.settings.agent_max_iterations):
                    try:
                        decision = self._decide(task.command_text, history, intent.get("problem_summary", ""))
                    except Exception as ex:
                        self._log(f"AI qaror xatosi: {ex}", "error")
                        break

                    analysis = decision.get("analysis", "")
                    if analysis:
                        self._log(f"Tahlil: {analysis}")

                    if decision.get("done"):
                        summary = decision.get("user_summary") or "Jarayon yakunlandi."
                        self._finish_ok(summary)
                        return

                    cmds = decision.get("commands") or []
                    if not isinstance(cmds, list):
                        cmds = []
                    cmds = [str(c).strip() for c in cmds if str(c).strip()][:6]
                    if not cmds:
                        self._finish_ok(decision.get("user_summary") or "Qo‘shimcha buyruqlar talab qilinmadi.")
                        return

                    for cmd in cmds:
                        ok, reason = is_command_allowed(cmd)
                        if not ok:
                            self._add_step(cmd, reason, StepStatus.skipped.value)
                            history.append({"command": cmd, "output": reason, "skipped": True})
                            continue
                        self._add_step(cmd, None, StepStatus.running.value)
                        try:
                            res = ssh.run(cmd)
                            out = res.combined[:60000]
                            st = StepStatus.success.value if res.exit_code == 0 else StepStatus.error.value
                            self._update_last_step_output(task.id, out, st)
                            history.append({"command": cmd, "output": out, "exit_code": res.exit_code})
                        except Exception as ex:
                            self._update_last_step_output(task.id, str(ex), StepStatus.error.value)
                            history.append({"command": cmd, "output": str(ex), "error": True})

                self._finish_ok("Iteratsiya limiti. Qo‘lda tekshiring.")
        except FileNotFoundError as e:
            self._fail(f"SSH kalit: {e}")
        except Exception as e:
            self._fail(f"SSH yoki bajarish xatosi: {e}")

    def _update_last_step_output(self, task_id: int, output: str, status: str) -> None:
        step = (
            self.db.query(TaskStep)
            .filter(TaskStep.task_id == task_id)
            .order_by(TaskStep.step_order.desc())
            .first()
        )
        if step:
            step.output = output[:65000]
            step.status = status
            self.db.commit()

    def _parse_intent(self, text: str, servers: list[Server]) -> dict[str, Any]:
        system = (
            "You are an infrastructure operator AI. "
            "Given the user message and JSON list of servers, respond ONLY with JSON:\n"
            '{"server_name": string or null (must match a server name from the list if possible), '
            '"problem_summary": string, '
            '"diagnostic_commands": string[] (safe Linux shell commands, max 10), '
            '"confidence": number }.\n'
            "Prefer read-only diagnostics: systemctl status, journalctl -n 50 --no-pager, docker ps -a, "
            "ss -tulnp, df -h, free -m, ping -c 2, curl -sI, ufw status, iptables -L -n."
        )
        user = f"User message:\n{text}\n\nServers:\n{self._servers_payload(servers)}"
        return complete_json(system, user)

    def _decide(self, original: str, history: list[dict[str, Any]], problem_summary: str) -> dict[str, Any]:
        system = (
            "You are a senior DevOps engineer. Based on command outputs, propose safe fix commands or verification. "
            "Return ONLY JSON: "
            '{"analysis": string, "commands": string[], "done": boolean, "user_summary": string}. '
            "Set done true if the problem appears fixed or nothing else to try. "
            "Allowed fixes examples: systemctl restart/start/enable, docker start/restart, ufw allow, "
            "nginx -t && systemctl reload nginx, apt-get update (read-only ok). "
            "Never suggest rm -rf /, dd, mkfs, shutdown, or piping curl to bash."
        )
        user = (
            f"Original request:\n{original}\n\nProblem summary:\n{problem_summary}\n\n"
            f"History:\n{json.dumps(history, ensure_ascii=False)[:50000]}"
        )
        return complete_json(system, user)

    def _fail(self, msg: str) -> None:
        task = self._task()
        if task:
            task.status = TaskStatus.error.value
            task.summary = msg
            self.db.add(AuditLog(task_id=task.id, message=msg, level="error"))
            self.db.commit()

    def _finish_ok(self, summary: str) -> None:
        task = self._task()
        if task:
            task.status = TaskStatus.done.value
            task.summary = summary
            self.db.add(AuditLog(task_id=task.id, message=summary, level="info"))
            self.db.commit()
