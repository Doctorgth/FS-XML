from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class CommandType(str, Enum):
    STANDARD = "standard"
    MANAGEMENT = "management"
    CUSTOM = "custom"


class FileState(str, Enum):
    WRITABLE = "writable"
    READONLY = "readonly"
    UNMARKED = "unmarked"


@dataclass
class CommandMetadata:
    tag: str
    command_type: CommandType
    description_human: str
    example_usage: str = ""


@dataclass
class ParsedCommandNode:
    tag: str
    attributes: Dict[str, str] = field(default_factory=dict)
    inner_text: str = ""
    sub_elements: Dict[str, str] = field(default_factory=dict)
    edit_pairs: List[Tuple[str, str]] = field(default_factory=list)
    raw_snippet: str = ""


@dataclass
class ExecutionContext:
    root_dir: str
    active_profile: str
    file_permissions: Dict[str, FileState]
    allow_management: bool = False
    custom_state: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommandResult:
    tag: str
    success: bool
    target_path: Optional[str] = None
    message: str = ""
    original_snapshot: Optional[str] = None
    new_snapshot: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionBatchResult:
    total_commands: int
    success_count: int
    error_count: int
    results: List[CommandResult] = field(default_factory=list)

    @property
    def is_all_successful(self) -> bool:
        return self.error_count == 0