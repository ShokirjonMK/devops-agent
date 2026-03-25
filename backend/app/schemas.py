import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ServerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    host: str = Field(..., min_length=1, max_length=512)
    user: str = Field(default="root", max_length=128)
    auth_type: str = Field(default="ssh_key", max_length=32)
    key_path: str | None = Field(default=None, max_length=1024)


class ServerCreate(ServerBase):
    pass


class ServerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    host: str | None = Field(default=None, min_length=1, max_length=512)
    user: str | None = Field(default=None, max_length=128)
    auth_type: str | None = Field(default=None, max_length=32)
    key_path: str | None = Field(default=None, max_length=1024)


class ServerRead(ServerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    environment: str = "production"
    monitoring_enabled: bool = False
    monitoring_interval_minutes: int = 5
    last_check_status: str = "unknown"
    last_check_at: datetime | None = None
    server_metadata: dict[str, Any] = Field(default_factory=dict)


class TaskStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    step_order: int
    command: str | None
    output: str | None
    status: str
    explanation: str | None = None
    phase: str | None = None
    created_at: datetime


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    message: str
    level: str
    timestamp: datetime


class TaskCreate(BaseModel):
    command_text: str = Field(..., min_length=1, max_length=8000)
    server_id: int | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str | None
    owner_user_id: uuid.UUID | None = None
    server_id: int | None
    command_text: str
    status: str
    source: str
    summary: str | None
    telegram_message_id: int | None = None
    created_at: datetime


class TaskDetailRead(TaskRead):
    steps: list[TaskStepRead] = []
    logs: list[AuditLogRead] = []


class TaskSubmit(BaseModel):
    """Telegram / external clients."""

    command_text: str = Field(..., min_length=1, max_length=8000)
    server_id: int | None = None
    user_id: str | None = None
    source: str = Field(default="web")
