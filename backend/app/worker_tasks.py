import logging

from app.celery_app import celery_app
from app.database import SessionLocal
from app.services.agent import DevOpsAgent

log = logging.getLogger(__name__)


@celery_app.task(name="run_agent_task")
def run_agent_task(task_id: int) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    db = SessionLocal()
    try:
        log.info("Agent task boshlandi: id=%s", task_id)
        DevOpsAgent(db, task_id).run()
        log.info("Agent task tugadi: id=%s", task_id)
    except Exception as exc:
        log.exception("Agent task xatosi: id=%s", task_id)
        db.rollback()
        try:
            from app.models import AuditLog, Task, TaskStatus

            t = db.get(Task, task_id)
            if t:
                t.status = TaskStatus.error.value
                t.summary = f"Worker xatosi: {exc}"
                db.add(AuditLog(task_id=t.id, message=str(exc), level="error"))
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()
