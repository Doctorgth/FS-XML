from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


def _current_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ProjectModel:
    id: Optional[int] = None
    name: str = ""
    root_dir: str = ""
    created_at: str = field(default_factory=_current_utc_iso)


@dataclass
class ProfileModel:
    id: Optional[int] = None
    project_id: int = 0
    name: str = "default"
    is_default: bool = False


@dataclass
class ProfileFileRuleModel:
    id: Optional[int] = None
    profile_id: int = 0
    rel_path: str = ""
    state: str = "writable"


@dataclass
class ExecutionSessionModel:
    id: Optional[int] = None
    project_id: int = 0
    profile_id: int = 0
    created_at: str = field(default_factory=_current_utc_iso)
    status: str = "success"
    total_commands: int = 0
    error_count: int = 0


@dataclass
class ChangeRecordModel:
    id: Optional[int] = None
    session_id: int = 0
    command_tag: str = ""
    target_path: Optional[str] = None
    status: str = "success"
    error_details: Optional[str] = None
    original_snapshot: Optional[str] = None
    new_snapshot: Optional[str] = None