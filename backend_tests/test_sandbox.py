import os
import tempfile
import pytest
from core.sandbox import Sandbox, SecurityException, AccessDeniedException
from core.types import ExecutionContext, FileState


def test_sandbox_path_traversal_detection():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Попытка вырваться наружу
        with pytest.raises(SecurityException):
            Sandbox.resolve_safe_path(temp_dir, "../outside.txt")

        with pytest.raises(SecurityException):
            Sandbox.resolve_safe_path(temp_dir, "foo/../../outside.txt")

        # Корректный вложенный путь
        safe = Sandbox.resolve_safe_path(temp_dir, "src/main.py")
        assert safe.startswith(os.path.realpath(temp_dir))


def test_sandbox_permission_enforcement():
    context = ExecutionContext(
        root_dir="/mock",
        active_profile="test",
        file_permissions={
            "src/allowed.txt": FileState.WRITABLE,
            "src/locked.txt": FileState.READONLY,
        }
    )

    # Writable должен проходить
    Sandbox.assert_write_permitted("src/allowed.txt", context)

    # Read-Only должен вызывать AccessDeniedException
    with pytest.raises(AccessDeniedException):
        Sandbox.assert_write_permitted("src/locked.txt", context)

    # Unmarked должен вызывать AccessDeniedException при check_registered=True
    with pytest.raises(AccessDeniedException):
        Sandbox.assert_write_permitted("src/unknown.txt", context, check_registered=True)