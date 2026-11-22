import os
import re
from typing import Optional
from core.types import ExecutionContext, FileState


class SecurityException(Exception):
    pass


class AccessDeniedException(Exception):
    pass


class Sandbox:
    @staticmethod
    def normalize_rel_path(rel_path: str) -> str:
        clean = rel_path.strip().replace("\\", "/")
        norm = os.path.normpath(clean).replace("\\", "/")
        return norm

    @staticmethod
    def resolve_safe_path(root_dir: str, rel_path: str) -> str:
        norm_rel = Sandbox.normalize_rel_path(rel_path)
        drive, _ = os.path.splitdrive(norm_rel)
        if (
            drive
            or re.match(r"^[a-zA-Z]:", norm_rel)
            or norm_rel.startswith("/")
            or os.path.isabs(norm_rel)
            or norm_rel.startswith("../")
            or norm_rel == ".."
        ):
            raise SecurityException(
                f"Path traversal violation detected: '{rel_path}' points outside project root."
            )

        abs_root = os.path.realpath(root_dir)
        abs_target = os.path.realpath(os.path.join(abs_root, norm_rel))

        if not (abs_target == abs_root or abs_target.startswith(abs_root + os.sep)):
            raise SecurityException(
                f"Path traversal violation detected: resolved '{abs_target}' escapes '{abs_root}'."
            )

        return abs_target

    @staticmethod
    def assert_write_permitted(
        rel_path: str, context: ExecutionContext, check_registered: bool = True
    ) -> None:
        norm_rel = Sandbox.normalize_rel_path(rel_path)
        permission = context.file_permissions.get(norm_rel, FileState.UNMARKED)

        if permission == FileState.READONLY:
            raise AccessDeniedException(
                f"File '{norm_rel}' is marked as READ_ONLY in current profile '{context.active_profile}'."
            )

        if check_registered and permission != FileState.WRITABLE:
            raise AccessDeniedException(
                f"File '{norm_rel}' is UNMARKED or not registered for writing in profile '{context.active_profile}'."
            )