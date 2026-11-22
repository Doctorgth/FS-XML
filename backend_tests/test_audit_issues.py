import json
import os
import tempfile
from fastapi import FastAPI
from fastapi.testclient import TestClient
from core.engine import CoreEngine
from core.handlers import register_default_handlers
from core.types import ExecutionContext, FileState
from server.api.routes import register_routes
from server.database.repository import DatabaseRepository
from server.services.context_service import ContextService
from server.services.ignore_service import IgnoreService
from server.services.profile_service import ProfileService
from server.services.project_service import ProjectService

register_default_handlers()

CREATE_TAG = "fs" + "_" + "create"
EDIT_TAG = "fs" + "_" + "edit"
SEARCH_TAG = "fs" + "_" + "search"
REPLACE_TAG = "fs" + "_" + "replace"
FILE_STATE_TAG = "fs" + "_" + "file_state"
PROFILE_CREATE_TAG = "fs" + "_" + "profile_create"
ALL_MARKER = "<" + "all" + " " + "/>"


def setup_test_app(temp_dir: str, global_ignore_path: str = "fsignore_global"):
    db_path = os.path.join(temp_dir, "test_audit.db")
    repo = DatabaseRepository(db_path)
    ignore = IgnoreService(global_ignore_path)
    ctx = ContextService(ignore)
    engine = CoreEngine()
    project_svc = ProjectService(repo, ctx, engine)
    profile_svc = ProfileService(repo)

    app = FastAPI()
    app.include_router(register_routes(repo, project_svc, profile_svc, ctx))
    client = TestClient(app, raise_server_exceptions=False)
    return client, repo, ignore


# ---------------------------------------------------------------------------
# 1.1 Откат управляющих команд не должен удалять файлы или падать с 500
# ---------------------------------------------------------------------------
def test_audit_1_1_rollback_management_commands_safe():
    with tempfile.TemporaryDirectory() as temp_dir:
        client, repo, _ = setup_test_app(temp_dir)
        proj_id = client.post("/api/projects", json={"name": "Audit11", "root_dir": temp_dir}).json()["id"]
        prof_id = client.get(f"/api/projects/{proj_id}/profiles").json()[0]["id"]

        target_file = os.path.join(temp_dir, "keep_me.py")
        with open(target_file, "w", encoding="utf-8", newline="") as f:
            f.write("IMPORTANT_CODE = True\n")

        xml = (
            f'<{FILE_STATE_TAG} path="keep_me.py" state="writable" />\n'
            f'<{PROFILE_CREATE_TAG} name="BackendOnly" />'
        )
        res_exec = client.post(
            f"/api/projects/{proj_id}/execute?profile_id={prof_id}",
            json={"xml_content": xml, "allow_management": True},
        )
        assert res_exec.status_code == 200
        sess_id = res_exec.json()["session_id"]
        records = client.get(f"/api/sessions/{sess_id}").json()
        assert len(records) == 2

        rec_file_state = next(r for r in records if r["command_tag"] == FILE_STATE_TAG)
        rec_prof_create = next(r for r in records if r["command_tag"] == PROFILE_CREATE_TAG)

        # Откат fs_file_state НЕ должен удалять существующий файл с диска
        res_rb1 = client.post(f"/api/records/{rec_file_state['id']}/rollback", json={"force": True})
        assert res_rb1.status_code != 500
        assert os.path.isfile(target_file), "Existing file was deleted when rolling back fs_file_state!"
        with open(target_file, "r", encoding="utf-8") as f:
            assert f.read() == "IMPORTANT_CODE = True\n"

        # Откат команды без target_path (fs_profile_create) НЕ должен вызывать 500 TypeError
        res_rb2 = client.post(f"/api/records/{rec_prof_create['id']}/rollback", json={"force": True})
        assert res_rb2.status_code in (400, 422)


# ---------------------------------------------------------------------------
# 1.2 Команда fs_file_state со state="unmarked" должна сохраняться в БД
# ---------------------------------------------------------------------------
def test_audit_1_2_file_state_unmarked_persists_in_db():
    with tempfile.TemporaryDirectory() as temp_dir:
        client, repo, _ = setup_test_app(temp_dir)
        proj_id = client.post("/api/projects", json={"name": "Audit12", "root_dir": temp_dir}).json()["id"]
        prof_id = client.get(f"/api/projects/{proj_id}/profiles").json()[0]["id"]

        file_path = os.path.join(temp_dir, "module.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("x = 1\n")

        client.post(f"/api/profiles/{prof_id}/files", json={"rel_path": "module.py", "state": "writable"})
        assert repo.get_profile_rules(prof_id).get("module.py") == "writable"

        xml = f'<{FILE_STATE_TAG} path="module.py" state="unmarked" />'
        res_exec = client.post(
            f"/api/projects/{proj_id}/execute?profile_id={prof_id}",
            json={"xml_content": xml, "allow_management": True},
        )
        assert res_exec.status_code == 200
        assert res_exec.json()["error_count"] == 0

        rules_after = repo.get_profile_rules(prof_id)
        assert "module.py" not in rules_after


# ---------------------------------------------------------------------------
# 1.3 Сохранение точного стиля окончаний строк (LF / CRLF) без \r\r\n
# ---------------------------------------------------------------------------
def test_audit_1_3_preserve_crlf_and_lf_without_double_cr():
    with tempfile.TemporaryDirectory() as temp_dir:
        engine = CoreEngine()

        crlf_path = os.path.join(temp_dir, "win_crlf.py")
        lf_path = os.path.join(temp_dir, "unix_lf.py")

        with open(crlf_path, "wb") as f:
            f.write(b"a = 1\r\nb = 2\r\nc = 3\r\n")
        with open(lf_path, "wb") as f:
            f.write(b"a = 1\nb = 2\nc = 3\n")

        context = ExecutionContext(
            root_dir=temp_dir,
            active_profile="test",
            file_permissions={
                "win_crlf.py": FileState.WRITABLE,
                "unix_lf.py": FileState.WRITABLE,
            },
            allow_management=False,
        )

        xml = (
            f'<{EDIT_TAG} path="win_crlf.py">\n'
            f'<{SEARCH_TAG}>\nb = 2\n</{SEARCH_TAG}>\n'
            f'<{REPLACE_TAG}>\nb = 200\n</{REPLACE_TAG}>\n'
            f'</{EDIT_TAG}>\n'
            f'<{EDIT_TAG} path="unix_lf.py">\n'
            f'<{SEARCH_TAG}>\nb = 2\n</{SEARCH_TAG}>\n'
            f'<{REPLACE_TAG}>\nb = 200\n</{REPLACE_TAG}>\n'
            f'</{EDIT_TAG}>'
        )
        res = engine.execute_batch(xml, context)
        assert res.success_count == 2

        with open(crlf_path, "rb") as f:
            crlf_bytes = f.read()
        with open(lf_path, "rb") as f:
            lf_bytes = f.read()

        assert b"\r\r\n" not in crlf_bytes
        assert crlf_bytes == b"a = 1\r\nb = 200\r\nc = 3\r\n"
        assert b"\r\n" not in lf_bytes
        assert lf_bytes == b"a = 1\nb = 200\nc = 3\n"


# ---------------------------------------------------------------------------
# 1.4 Атрибут path с апострофом не должен обрезаться парсером
# ---------------------------------------------------------------------------
def test_audit_1_4_parse_attributes_with_apostrophe():
    engine = CoreEngine()
    xml = f'<{CREATE_TAG} path="docs/it\'s_ok.txt">hello</{CREATE_TAG}>'
    nodes = engine.parse_payload(xml)
    assert len(nodes) == 1
    assert nodes[0].attributes.get("path") == "docs/it's_ok.txt"


# ---------------------------------------------------------------------------
# 2.1 Изменение глобального игнора должно применяться без перезапуска сервиса
# ---------------------------------------------------------------------------
def test_audit_2_1_global_ignore_reloads_dynamically():
    with tempfile.TemporaryDirectory() as temp_dir:
        global_ig = os.path.join(temp_dir, "fsignore_global_test")
        with open(global_ig, "w", encoding="utf-8") as f:
            f.write("*.log\n")

        ignore = IgnoreService(global_ig)
        rules_before = ignore.get_project_rules(temp_dir)
        assert ignore.is_ignored("data.secret", is_dir=False, rules=rules_before) is False

        # Обновляем глобальный игнор-файл на диске
        with open(global_ig, "w", encoding="utf-8") as f:
            f.write("*.log\n*.secret\n")

        rules_after = ignore.get_project_rules(temp_dir)
        assert ignore.is_ignored("data.secret", is_dir=False, rules=rules_after) is True


# ---------------------------------------------------------------------------
# 2.4 restore_snapshot должен очищать лишние правила и проверять пути через Sandbox
# ---------------------------------------------------------------------------
def test_audit_2_4_restore_snapshot_resets_rules_and_blocks_traversal():
    with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as outside_dir:
        client, repo, _ = setup_test_app(temp_dir)
        proj_id = client.post("/api/projects", json={"name": "Audit24", "root_dir": temp_dir}).json()["id"]
        prof_id = client.get(f"/api/projects/{proj_id}/profiles").json()[0]["id"]

        file_a = os.path.join(temp_dir, "a.txt")
        file_b = os.path.join(temp_dir, "b.txt")
        with open(file_a, "w", encoding="utf-8") as f:
            f.write("A_V1")
        with open(file_b, "w", encoding="utf-8") as f:
            f.write("B_V1")

        client.post(f"/api/profiles/{prof_id}/files", json={"rel_path": "a.txt", "state": "writable"})
        snap_id = client.post(
            f"/api/projects/{proj_id}/snapshots?profile_id={prof_id}",
            json={"name": "clean_snap", "for_all_profiles": False},
        ).json()["id"]

        # После снапшота отмечаем b.txt как writable
        client.post(f"/api/profiles/{prof_id}/files", json={"rel_path": "b.txt", "state": "writable"})
        assert "b.txt" in repo.get_profile_rules(prof_id)

        # Восстанавливаем снапшот — b.txt больше не должен быть отмечен
        res_restore = client.post(f"/api/snapshots/{snap_id}/restore")
        assert res_restore.status_code == 200
        assert repo.get_profile_rules(prof_id) == {"a.txt": "writable"}

        # Проверка защиты от Path Traversal в снапшоте
        evil_target = os.path.join(outside_dir, "pwned.txt")
        evil_payload = json.dumps({
            "profiles": {},
            "files": {f"../{os.path.basename(outside_dir)}/pwned.txt": "HACKED"},
        })
        evil_snap_id = repo.create_snapshot(proj_id, prof_id, "evil", evil_payload)
        res_evil = client.post(f"/api/snapshots/{evil_snap_id}/restore")
        assert res_evil.status_code in (400, 403)
        assert not os.path.exists(evil_target)


# ---------------------------------------------------------------------------
# 2.5 Выполнение пустого/нераспознанного XML не должно возвращать status="success"
# ---------------------------------------------------------------------------
def test_audit_2_5_empty_or_unrecognized_xml_not_marked_success():
    with tempfile.TemporaryDirectory() as temp_dir:
        client, _, _ = setup_test_app(temp_dir)
        proj_id = client.post("/api/projects", json={"name": "Audit25", "root_dir": temp_dir}).json()["id"]
        prof_id = client.get(f"/api/projects/{proj_id}/profiles").json()[0]["id"]

        res = client.post(
            f"/api/projects/{proj_id}/execute?profile_id={prof_id}",
            json={"xml_content": "Просто текст без валидных команд <unknown_tag />", "allow_management": False},
        )
        if res.status_code == 200:
            assert res.json()["status"] != "success"
        else:
            assert res.status_code in (400, 422)


# ---------------------------------------------------------------------------
# 3.1 Валидация профилей и директорий (без 500 IntegrityError)
# ---------------------------------------------------------------------------
def test_audit_3_1_profile_and_directory_validation_errors():
    with tempfile.TemporaryDirectory() as dir1, tempfile.TemporaryDirectory() as dir2:
        client, _, _ = setup_test_app(dir1)
        p1 = client.post("/api/projects", json={"name": "P1", "root_dir": dir1}).json()["id"]
        p2 = client.post("/api/projects", json={"name": "P2", "root_dir": dir2}).json()["id"]

        # Пустое имя профиля
        res_empty = client.post(f"/api/projects/{p1}/profiles", json={"name": "   "})
        assert res_empty.status_code in (400, 422)

        # Дубликат имени профиля
        res_ok = client.post(f"/api/projects/{p1}/profiles", json={"name": "Backend"})
        assert res_ok.status_code == 200
        res_dup = client.post(f"/api/projects/{p1}/profiles", json={"name": "Backend"})
        assert res_dup.status_code in (400, 409)

        # Перемещение директории P2 на уже занятую P1
        res_dup_dir = client.put(f"/api/projects/{p2}/directory", json={"root_dir": dir1})
        assert res_dup_dir.status_code in (400, 409)

        # Несуществующий проект
        res_404 = client.put("/api/projects/999999/directory", json={"root_dir": dir2})
        assert res_404.status_code == 404


# ---------------------------------------------------------------------------
# 3.2 Edge-кейсы FsEditHandler: <all  /> с пробелами и разделители \v / \f
# ---------------------------------------------------------------------------
def test_audit_3_2_fs_edit_all_spaces_and_vertical_tab():
    with tempfile.TemporaryDirectory() as temp_dir:
        engine = CoreEngine()
        file_path = os.path.join(temp_dir, "edge.py")
        original = "x = 'a\vb'\ny = 1\nz = 2\n"
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            f.write(original)

        context = ExecutionContext(
            root_dir=temp_dir,
            active_profile="test",
            file_permissions={"edge.py": FileState.WRITABLE},
            allow_management=False,
        )

        # Attempt 2 (trailing whitespace mismatch) не должен превращать \v в \n через splitlines()
        xml_vtab = (
            f'<{EDIT_TAG} path="edge.py">\n'
            f'<{SEARCH_TAG}>\ny = 1   \n</{SEARCH_TAG}>\n'
            f'<{REPLACE_TAG}>\ny = 99\n</{REPLACE_TAG}>\n'
            f'</{EDIT_TAG}>'
        )
        res = engine.execute_batch(xml_vtab, context)
        assert res.success_count == 1
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        assert "\v" in content
        assert "y = 99" in content

        # Тег full-replacement с дополнительными пробелами (<all  />)
        all_two_spaces = "<" + "all" + "  " + "/>"
        xml_all = (
            f'<{EDIT_TAG} path="edge.py">\n'
            f'<{SEARCH_TAG}>{all_two_spaces}</{SEARCH_TAG}>\n'
            f'<{REPLACE_TAG}>\nREPLACED = True\n</{REPLACE_TAG}>\n'
            f'</{EDIT_TAG}>'
        )
        res_all = engine.execute_batch(xml_all, context)
        assert res_all.success_count == 1
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            assert f.read().strip() == "REPLACED = True"


# ---------------------------------------------------------------------------
# 3.3 IgnoreService: вложенные папки (foo/bar/) и корневой слэш (/dist)
# ---------------------------------------------------------------------------
def test_audit_3_3_ignore_nested_dir_and_root_anchor():
    ignore = IgnoreService()

    # Вложенный каталог foo/bar/
    assert ignore.is_ignored("foo/bar/baz.txt", is_dir=False, rules=["foo/bar/"]) is True

    # Корневой /dist должен игнорировать dist/app.js, но НЕ src/dist/app.js
    assert ignore.is_ignored("dist/app.js", is_dir=False, rules=["/dist"]) is True
    assert ignore.is_ignored("src/dist/app.js", is_dir=False, rules=["/dist"]) is False


# ---------------------------------------------------------------------------
# 3.3 / 4.1 Проверка чистоты FS-XML.txt и игнорирования context_dump.txt
# ---------------------------------------------------------------------------
def test_audit_4_1_prompt_file_and_context_dump_ignore():
    prompt_path = os.path.abspath("FS-XML.txt")
    if os.path.isfile(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_text = f.read()
        assert not prompt_text.lstrip().startswith("[READ_ONLY]"), (
            "FS-XML.txt contains [READ_ONLY] header that leaks into AI prompt!"
        )
        assert "Вот готовый, актуальный и исчерпывающий системный промпт" not in prompt_text

    with tempfile.TemporaryDirectory() as temp_dir:
        with open(os.path.join(temp_dir, "context_dump.txt"), "w", encoding="utf-8") as f:
            f.write("PREVIOUS DUMP")
        with open(os.path.join(temp_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write("print(1)")

        ctx = ContextService(IgnoreService("fsignore_global"))
        tree = ctx.build_file_tree(temp_dir, {})
        paths = [node["path"] for node in tree]
        assert "main.py" in paths
        assert "context_dump.txt" not in paths