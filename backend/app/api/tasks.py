from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import get_optional_current_user
from app.models import Task, TaskSource, User
from app.schemas import TaskCreate, TaskDetailRead, TaskRead, TaskSubmit
from app.worker_tasks import run_agent_task

router = APIRouter()


@router.get("", response_model=list[TaskRead])
def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[Task]:
    q = db.query(Task).order_by(Task.created_at.desc())
    return q.offset(skip).limit(limit).all()


@router.get("/{task_id}", response_model=TaskDetailRead)
def get_task(task_id: int, db: Session = Depends(get_db)) -> Task:
    row = (
        db.query(Task)
        .options(selectinload(Task.steps), selectinload(Task.logs))
        .filter(Task.id == task_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return row


@router.post("", response_model=TaskRead, status_code=status.HTTP_202_ACCEPTED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> Task:
    task = Task(
        command_text=payload.command_text.strip(),
        server_id=payload.server_id,
        source=TaskSource.web.value,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    run_agent_task.delay(task.id)
    return task


@router.post("/submit", response_model=TaskRead, status_code=status.HTTP_202_ACCEPTED)
def submit_task_external(payload: TaskSubmit, db: Session = Depends(get_db)) -> Task:
    src = payload.source.strip().lower()
    if src not in (TaskSource.web.value, TaskSource.telegram.value):
        src = TaskSource.web.value
    owner_user_id = None
    if payload.user_id is not None and str(payload.user_id).strip():
        try:
            tid = int(str(payload.user_id).strip())
        except ValueError:
            tid = None
        if tid is not None:
            u = db.query(User).filter(User.telegram_id == tid).first()
            if u:
                owner_user_id = u.id
    task = Task(
        command_text=payload.command_text.strip(),
        server_id=payload.server_id,
        user_id=payload.user_id,
        source=src,
        owner_user_id=owner_user_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    run_agent_task.delay(task.id)
    return task
