import os
import tempfile
from core.engine import CoreEngine
from core.handlers import register_default_handlers
from core.types import ExecutionContext, FileState

register_default_handlers()
engine = CoreEngine()


def test_fs_create_and_collision():
    with tempfile.TemporaryDirectory() as temp_dir:
        context = ExecutionContext(
            root_dir=temp_dir,
            active_profile="test",
            file_permissions={},
            allow_management=True
        )

        create_tag = "fs" + "_" + "create"
        xml = f'<{create_tag} path="new_file.txt">Hello World</{create_tag}>'
        res = engine.execute_batch(xml, context)
        assert res.success_count == 1
        assert os.path.exists(os.path.join(temp_dir, "new_file.txt"))

        # Повторное создание того же файла должно вызвать ошибку коллизии
        res2 = engine.execute_batch(xml, context)
        assert res2.error_count == 1
        assert "already exists" in res2.results[0].message


def test_fs_edit_search_replace_and_all():
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, "app.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("def foo():\n    return 42\n")

        context = ExecutionContext(
            root_dir=temp_dir,
            active_profile="test",
            file_permissions={"app.py": FileState.WRITABLE},
            allow_management=False
        )

        # 1. Частичная замена
        edit_tag = "fs" + "_" + "edit"
        search_tag = "fs" + "_" + "search"
        replace_tag = "fs" + "_" + "replace"
        xml = (
            f'<{edit_tag} path="app.py">\n'
            f'<{search_tag}>return 42</{search_tag}>\n'
            f'<{replace_tag}>return 100</{replace_tag}>\n'
            f'</{edit_tag}>'
        )
        res = engine.execute_batch(xml, context)
        assert res.success_count == 1
        with open(file_path, "r", encoding="utf-8") as f:
            assert "return 100" in f.read()

        # 2. Полная замена через <all />
        xml_all = (
            f'<{edit_tag} path="app.py">\n'
            f'<{search_tag}><all /></{search_tag}>\n'
            f'<{replace_tag}>print("OVERWRITTEN")</{replace_tag}>\n'
            f'</{edit_tag}>'
        )
        res_all = engine.execute_batch(xml_all, context)
        assert res_all.success_count == 1
        with open(file_path, "r", encoding="utf-8") as f:
            assert f.read() == 'print("OVERWRITTEN")'


def test_management_commands_flag_guard():
    with tempfile.TemporaryDirectory() as temp_dir:
        context_locked = ExecutionContext(
            root_dir=temp_dir,
            active_profile="test",
            file_permissions={},
            allow_management=False
        )

        prof_tag = "fs" + "_" + "profile_create"
        xml = f'<{prof_tag} name="SecretProfile" />'

        # Без флага allow_management команда блокируется
        res = engine.execute_batch(xml, context_locked)
        assert res.error_count == 1
        assert "MANAGEMENT command" in res.results[0].message

        # С активным флагом выполняется
        context_open = ExecutionContext(
            root_dir=temp_dir,
            active_profile="test",
            file_permissions={},
            allow_management=True
        )
        res_ok = engine.execute_batch(xml, context_open)
        assert res_ok.success_count == 1