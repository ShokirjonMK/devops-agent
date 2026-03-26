from __future__ import annotations

import json
import re
import time
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AuditLog, Server, Task, TaskStatus, TaskStep, StepStatus
from app.services.command_filter import is_command_allowed
from app.services.llm import complete_json
from app.services.ssh_client import SSHExecutor
from app.services.task_events import publish_task_event

# Agent loop: diagnose → (decide → execute → [implicit verify via next iteration]) → repeat
PHASE_DIAGNOSE = "diagnose"
PHASE_EXECUTE = "execute"
PHASE_VERIFY = "verify"


class DevOpsAgent:
    def __init__(self, db: Session, task_id: int) -> None:
        self.db = db
        self.task_id = task_id
        self.settings = get_settings()
        self._order = 0

    def _task(self) -> Task | None:
        return self.db.get(Task, self.task_id)

    def _llm_context(self) -> dict[str, Any]:
        t = self._task()
        oid = t.owner_user_id if t else None
        return {"db": self.db, "owner_user_id": oid}

    def _log(self, message: str, level: str = "info") -> None:
        t = self._task()
        if not t:
            return
        self.db.add(AuditLog(task_id=t.id, message=message, level=level))
        self.db.commit()

    def _next_step_order(self) -> int:
        self._order += 1
        return self._order

    def _add_step_running(
        self,
        command: str | None,
        explanation: str | None,
        phase: str | None,
    ) -> None:
        t = self._task()
        if not t:
            return
        self.db.add(
            TaskStep(
                task_id=t.id,
                step_order=self._next_step_order(),
                command=command,
                output=None,
                status=StepStatus.running.value,
                explanation=(explanation or "")[:8000] or None,
                phase=phase,
            )
        )
        self.db.commit()
        st = self.db.query(TaskStep).filter(TaskStep.task_id == t.id).order_by(TaskStep.step_order.desc()).first()
        if st:
            publish_task_event(
                t.id,
                "step_start",
                {
                    "step_order": st.step_order,
                    "command": (command or "")[:500],
                    "phase": phase,
                    "explanation": (explanation or "")[:800],
                },
            )

    def _finalize_last_step(
        self,
        task_id: int,
        output: str,
        status: str,
        *,
        duration_ms: int | None = None,
    ) -> None:
        step = (
            self.db.query(TaskStep)
            .filter(TaskStep.task_id == task_id)
            .order_by(TaskStep.step_order.desc())
            .first()
        )
        if step:
            step.output = (output or "")[:65000]
            step.status = status
            self.db.commit()
            payload = {
                "step_order": step.step_order,
                "command": (step.command or "")[:500],
                "phase": step.phase,
                "status": status,
                "output_preview": (output or "")[:1200],
            }
            if duration_ms is not None:
                payload["duration_ms"] = duration_ms
            publish_task_event(task_id, "step_done", payload)

    def _add_step_skipped(
        self,
        command: str | None,
        reason: str,
        explanation: str | None,
        phase: str | None,
    ) -> None:
        t = self._task()
        if not t:
            return
        self.db.add(
            TaskStep(
                task_id=t.id,
                step_order=self._next_step_order(),
                command=command,
                output=reason[:65000],
                status=StepStatus.skipped.value,
                explanation=(explanation or reason)[:8000],
                phase=phase,
            )
        )
        self.db.commit()
        st = self.db.query(TaskStep).filter(TaskStep.task_id == t.id).order_by(TaskStep.step_order.desc()).first()
        if st:
            publish_task_event(
                t.id,
                "step_skipped",
                {
                    "step_order": st.step_order,
                    "command": (command or "")[:500],
                    "phase": phase,
                    "reason": reason[:500],
                },
            )

    def _servers_payload(self, servers: list[Server]) -> str:
        return json.dumps(
            [{"name": s.name, "host": s.host, "id": s.id} for s in servers],
            ensure_ascii=False,
        )

    def _match_server(self, servers: list[Server], name_hint: str | None) -> Server | None:
        if not name_hint:
            return None
        hint = name_hint.strip().lower()
        hint = re.sub(r"\s+server(id|da|ida)?$", "", hint).strip()
        for s in servers:
            if s.name.lower() == hint:
                return s
        for s in servers:
            if hint in s.name.lower() or s.name.lower() in hint:
                return s
        return None

    @staticmethod
    def _normalize_diagnostic_plan(intent: dict[str, Any]) -> list[dict[str, str]]:
        plan = intent.get("diagnostic_plan")
        out: list[dict[str, str]] = []
        if isinstance(plan, list):
            for item in plan:
                if isinstance(item, dict):
                    c = str(item.get("command", "")).strip()
                    e = str(item.get("explanation", "")).strip()
                    if c:
                        out.append(
                            {
                                "command": c,
                                "explanation": e or "Diagnostika: tizim va servislar holatini tekshirish.",
                            }
                        )
                elif isinstance(item, str) and item.strip():
                    out.append(
                        {
                            "command": item.strip(),
                            "explanation": "Diagnostika: umumiy holatni aniqlash.",
                        }
                    )
        if out:
            return out[:12]
        cmds = intent.get("diagnostic_commands")
        if isinstance(cmds, list):
            for c in cmds:
                s = str(c).strip()
                if s:
                    out.append(
                        {
                            "command": s,
                            "explanation": "Diagnostika: LLM tanlagan tekshiruv buyrug‘i.",
                        }
                    )
        return out[:12]

    @staticmethod
    def _normalize_decision_steps(decision: dict[str, Any]) -> list[dict[str, str]]:
        steps = decision.get("next_steps")
        result: list[dict[str, str]] = []
        if isinstance(steps, list):
            for s in steps:
                if isinstance(s, dict):
                    c = str(s.get("command", "")).strip()
                    e = str(s.get("explanation", "")).strip()
                    if c:
                        result.append(
                            {
                                "command": c,
                                "explanation": e or "Qaror: keyingi amaliyot.",
                            }
                        )
        if result:
            return result[:8]
        cmds = decision.get("commands")
        if isinstance(cmds, list):
            for c in cmds:
                s = str(c).strip()
                if s:
                    result.append(
                        {
                            "command": s,
                            "explanation": "Qaror: tuzatish yoki tekshirish (LLM qisqa reja).",
                        }
                    )
        return result[:8]

    @staticmethod
    def _output_hints(output: str) -> list[str]:
        hints: list[str] = []
        low = output.lower()
        if "permission denied" in low:
            hints.append("Ehtimol huquq yetarli emas (sudo yoki foydalanuvchi).")
        if "command not found" in low:
            hints.append("Buyruq topilmadi — paket o‘rnatilmagan bo‘lishi mumkin.")
        if "docker" in low and ("not found" in low or "no such file" in low):
            hints.append("Docker CLI yoki daemon mavjud emas bo‘lishi mumkin.")
        if "no space left on device" in low or "disk full" in low:
            hints.append("Disk to‘lgan; bo‘sh joy kerak.")
        if "connection refused" in low:
            hints.append("Port yopiq yoki servis ishlamayapti.")
        return hints

    def _execute_ssh_command(
        self,
        ssh: SSHExecutor,
        task_id: int,
        cmd: str,
        explanation: str,
        phase: str,
        history: list[dict[str, Any]],
    ) -> None:
        ok, reason = is_command_allowed(cmd)
        if not ok:
            self._add_step_skipped(cmd, reason or "blocked", explanation, phase)
            history.append(
                {
                    "command": cmd,
                    "explanation": explanation,
                    "phase": phase,
                    "output": reason,
                    "skipped": True,
                }
            )
            return
        self._add_step_running(cmd, explanation, phase)
        try:
            t0 = time.perf_counter()
            res = ssh.run(cmd)
            dur_ms = int((time.perf_counter() - t0) * 1000)
            out = res.combined[:60000]
            st = StepStatus.success.value if res.exit_code == 0 else StepStatus.error.value
            self._finalize_last_step(task_id, out, st, duration_ms=dur_ms)
            for h in self._output_hints(out):
                self._log(f"{cmd[:80]}: {h}", "warning")
            history.append(
                {
                    "command": cmd,
                    "explanation": explanation,
                    "phase": phase,
                    "output": out,
                    "exit_code": res.exit_code,
                }
            )
        except Exception as ex:
            self._finalize_last_step(task_id, str(ex), StepStatus.error.value, duration_ms=None)
            self._log(f"SSH bajarish xatosi: {cmd[:120]} — {ex}", "error")
            history.append(
                {
                    "command": cmd,
                    "explanation": explanation,
                    "phase": phase,
                    "output": str(ex),
                    "error": True,
                }
            )

    def run(self) -> None:
        task = self._task()
        if not task:
            return
        task.status = TaskStatus.running.value
        self.db.commit()
        publish_task_event(task.id, "task_running", {"message": "Agent boshlandi"})

        servers = self.db.query(Server).order_by(Server.name).all()
        if not servers:
            self._fail("Hech qanday server ro‘yxatga kiritilmagan. Avval Web UI orqali server qo‘shing.")
            return

        try:
            intent = self._parse_intent(task.command_text, servers)
        except Exception as e:
            self._fail(f"AI intent xatosi: {e}")
            return

        prob = intent.get("problem_summary")
        if isinstance(prob, str) and prob.strip():
            self._log(f"Intent: muammo — {prob.strip()[:2000]}")

        server_name = intent.get("server_name")
        server = task.server_id and self.db.get(Server, task.server_id)
        if not server:
            server = self._match_server(servers, server_name if isinstance(server_name, str) else None)
        if not server and len(servers) == 1:
            server = servers[0]
            self._log(
                f"Server nomi aniq emas; ro‘yxatda bitta server bor — '{server.name}' ishlatildi.",
                "warning",
            )
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
        diag_plan = self._normalize_diagnostic_plan(intent)
        if not diag_plan:
            diag_plan = [
                {
                    "command": "uptime",
                    "explanation": "Diagnostika: yuklanish va ishlash vaqti.",
                },
                {
                    "command": "df -h",
                    "explanation": "Diagnostika: disk bo‘sh joyi.",
                },
                {
                    "command": "free -m",
                    "explanation": "Diagnostika: xotira.",
                },
                {
                    "command": "ss -tulnp 2>/dev/null || netstat -tulnp 2>/dev/null || true",
                    "explanation": "Diagnostika: ochiq portlar va jarayonlar.",
                },
            ]

        last_cmd_signature: tuple[str, ...] | None = None
        stuck_rounds = 0

        # Decrypt SSH password for password-auth servers
        _ssh_password: str | None = None
        if getattr(server, "auth_type", "ssh_key") == "password":
            from app.api.servers import decrypt_ssh_password
            _ssh_password = decrypt_ssh_password(server)

        try:
            with SSHExecutor(
                server,
                self.settings.ssh_connect_timeout,
                self.settings.ssh_command_timeout,
                self.settings.ssh_connect_retries,
                self.settings.ssh_retry_backoff_seconds,
                password=_ssh_password,
            ) as ssh:
                self._log("SSH ulanish: OK — diagnostika boshlandi.")
                for item in diag_plan:
                    self._execute_ssh_command(
                        ssh,
                        task.id,
                        item["command"],
                        item["explanation"],
                        PHASE_DIAGNOSE,
                        history,
                    )

                self._log("Diagnostika yakunlandi — qaror-verifikatsiya sikli.")

                for iteration in range(self.settings.agent_max_iterations):
                    publish_task_event(
                        task.id,
                        "agent_thinking",
                        {"iteration": iteration + 1, "phase": "decide"},
                    )
                    try:
                        decision = self._decide_loop(
                            task.command_text,
                            history,
                            str(intent.get("problem_summary", "")),
                            iteration,
                        )
                    except Exception as ex:
                        self._log(f"AI qaror xatosi: {ex}", "error")
                        break

                    analysis = decision.get("analysis", "")
                    if isinstance(analysis, str) and analysis.strip():
                        self._log(f"Tahlil [{iteration + 1}]: {analysis.strip()[:3000]}")

                    if decision.get("done"):
                        summary = decision.get("user_summary") or "Jarayon yakunlandi."
                        self._finish_ok(summary)
                        return

                    step_phase_raw = decision.get("step_phase", "execute")
                    step_phase = (
                        PHASE_VERIFY
                        if str(step_phase_raw).lower() == "verify"
                        else PHASE_EXECUTE
                    )

                    planned = self._normalize_decision_steps(decision)
                    if not planned:
                        self._finish_ok(
                            decision.get("user_summary")
                            or "Keyingi buyruqlar bo‘sh — tekshirish uchun LLM javobini ko‘ring."
                        )
                        return

                    sig = tuple(p["command"] for p in planned)
                    if sig == last_cmd_signature and sig:
                        stuck_rounds += 1
                        self._log(
                            f"Takrorlanuvchi reja aniqlandi ({stuck_rounds}) — siklni to‘xtatish.",
                            "warning",
                        )
                        if stuck_rounds >= 2:
                            self._finish_ok(
                                "Bir xil buyruqlar ketma-ket takrorlandi — cheksiz sikl oldini olish. "
                                "Loglar va oxirgi chiqishlarni qo‘lda tekshiring."
                            )
                            return
                    else:
                        stuck_rounds = 0
                    last_cmd_signature = sig

                    self._log(
                        f"Bajarish bosqichi [{iteration + 1}] ({step_phase}): {len(planned)} buyruq.",
                    )
                    for p in planned:
                        self._execute_ssh_command(
                            ssh,
                            task.id,
                            p["command"],
                            p["explanation"],
                            step_phase,
                            history,
                        )

                self._finish_ok(
                    "Iteratsiya limiti yetdi (verify/decide/execute). Qo‘shimcha tekshiruvni qo‘lda bajaring."
                )
        except FileNotFoundError as e:
            self._fail(f"SSH kalit yoki fayl topilmadi: {e}")
        except Exception as e:
            self._fail(f"SSH yoki agent xatosi: {e}")

    def _parse_intent(self, text: str, servers: list[Server]) -> dict[str, Any]:
        system = (
            "You are an infrastructure operator AI. "
            "Given the user message (may be Uzbek/Russian/English) and JSON list of servers, "
            "respond ONLY with JSON:\n"
            '{"server_name": string or null (best match from list), '
            '"problem_summary": string, '
            '"diagnostic_plan": [{"command": string, "explanation": string}] (max 10 items), '
            '"confidence": number }.\n'
            "Each explanation must briefly say WHY that command helps diagnose the problem.\n"
            "Use safe read-only commands: systemctl status, journalctl -n 80 --no-pager, "
            "docker ps -a, ss -tulnp, df -h, free -m, ping -c 2, curl -sI -m 5, ufw status, iptables -L -n."
        )
        user = f"User message:\n{text}\n\nServers:\n{self._servers_payload(servers)}"
        return complete_json(system, user, **self._llm_context())

    def _decide_loop(
        self,
        original: str,
        history: list[dict[str, Any]],
        problem_summary: str,
        iteration: int,
    ) -> dict[str, Any]:
        system = (
            "You are a senior DevOps engineer running a diagnose → decide → execute → verify loop.\n"
            f"Current loop iteration (0-based): {iteration}.\n"
            "Based on ALL command outputs in history, either finish or propose the NEXT batch of shell commands.\n"
            "Return ONLY JSON with this shape:\n"
            '{"analysis": string (root cause / reasoning), '
            '"step_phase": "execute" | "verify" (execute=fix/start/restart/config; verify=check status after change), '
            '"next_steps": [{"command": string, "explanation": string}] (max 6; each explanation = WHY this command), '
            '"done": boolean, '
            '"user_summary": string }.\n'
            "Rules:\n"
            "- If the user problem appears RESOLVED by outputs, set done=true and user_summary explaining what was found.\n"
            "- If more work is needed, done=false and fill next_steps with safe commands.\n"
            "- After a fix, prefer step_phase verify with read-only checks (systemctl is-active, curl, ss).\n"
            "- Never suggest: rm -rf /, dd, mkfs, shutdown, reboot, halt, piping curl|wget to bash.\n"
            "- If docker/nginx not installed, say so in analysis and avoid useless restart commands for missing units.\n"
        )
        user = (
            f"Original user request:\n{original}\n\nProblem summary:\n{problem_summary}\n\n"
            f"Full history (commands + explanations + outputs):\n{json.dumps(history, ensure_ascii=False)[:52000]}"
        )
        return complete_json(system, user, **self._llm_context())

    def _fail(self, msg: str) -> None:
        task = self._task()
        if task:
            task.status = TaskStatus.error.value
            task.summary = msg
            self.db.add(AuditLog(task_id=task.id, message=msg, level="error"))
            self.db.commit()
            publish_task_event(task.id, "task_error", {"summary": msg[:2000]})

    def _finish_ok(self, summary: str) -> None:
        task = self._task()
        if task:
            task.status = TaskStatus.done.value
            task.summary = summary
            self.db.add(AuditLog(task_id=task.id, message=summary, level="info"))
            self.db.commit()
            publish_task_event(task.id, "task_done", {"summary": summary[:2000]})
