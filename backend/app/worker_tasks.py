from app.celery_app import celery_app
from app.database import SessionLocal
from app.services.agent import DevOpsAgent


@celery_app.task(name="run_agent_task")
def run_agent_task(task_id: int) -> None:
    db = SessionLocal()
    try:
        DevOpsAgent(db, task_id).run()
    except Exception as exc:
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
