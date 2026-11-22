import os
import tempfile
from fastapi import FastAPI
from fastapi.testclient import TestClient
from server.api.routes import register_routes
from server.database.repository import DatabaseRepository
from server.services.context_service import ContextService
from server.services.ignore_service import IgnoreService
from server.services.profile_service import ProfileService
from server.services.project_service import ProjectService
from core.engine import CoreEngine
from core.handlers import register_default_handlers

register_default_handlers()


def setup_test_app(temp_dir: str):
    db_path = os.path.join(temp_dir, "test.db")
    repo = DatabaseRepository(db_path)
    ignore = IgnoreService()
    ctx = ContextService(ignore)
    engine = CoreEngine()
    project_svc = ProjectService(repo, ctx, engine)
    profile_svc = ProfileService(repo)

    app = FastAPI()
    app.include_router(register_routes(repo, project_svc, profile_svc, ctx))
    client = TestClient(app)
    return client, repo


def test_ignore_exact_matching_bug():
    """Проверяем, что правило 'test' не матчит 'text.txt'"""
    ignore = IgnoreService()
    rules = ["test"]

    assert ignore.is_ignored("test", is_dir=False, rules=rules) is True
    assert ignore.is_ignored("src/test", is_dir=False, rules=rules) is True
    assert ignore.is_ignored("text.txt", is_dir=False, rules=rules) is False
    assert ignore.is_ignored("test.txt", is_dir=False, rules=rules) is False


def test_ignore_inline_comments_and_escaped_hash():
    with tempfile.TemporaryDirectory() as temp_dir:
        ig_file = os.path.join(temp_dir, ".fsignore")
        with open(ig_file, "w", encoding="utf-8") as f:
            f.write(
                "# Полный комментарий\n"
                "secret.txt # inline comment\n"
                "file\\#name.txt\n"
                "   \n"
            )
        ignore = IgnoreService()
        rules = ignore.get_project_rules(temp_dir)
        assert "secret.txt" in rules
        assert "file#name.txt" in rules
        assert ignore.is_ignored("secret.txt", is_dir=False, rules=rules) is True
        assert ignore.is_ignored("file#name.txt", is_dir=False, rules=rules) is True


def test_reapply_and_file_content_viewer():
    with tempfile.TemporaryDirectory() as temp_dir:
        client, repo = setup_test_app(temp_dir)
        res_p = client.post("/api/projects", json={"name": "ReapplyProj", "root_dir": temp_dir})
        proj_id = res_p.json()["id"]
        prof_id = client.get(f"/api/projects/{proj_id}/profiles").json()[0]["id"]

        file_path = os.path.join(temp_dir, "demo.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("V1")
        client.post(f"/api/profiles/{prof_id}/files", json={"rel_path": "demo.py", "state": "writable"})

        edit_tag = "fs" + "_" + "edit"
        search_tag = "fs" + "_" + "search"
        replace_tag = "fs" + "_" + "replace"
        xml = f'<{edit_tag} path="demo.py"><{search_tag}>V1</{search_tag}><{replace_tag}>V2</{replace_tag}></{edit_tag}>'
        sess_id = client.post(
            f"/api/projects/{proj_id}/execute?profile_id={prof_id}",
            json={"xml_content": xml, "allow_management": False}
        ).json()["session_id"]
        rec_id = client.get(f"/api/sessions/{sess_id}").json()[0]["id"]

        # Откатываем к V1
        client.post(f"/api/records/{rec_id}/rollback", json={"force": True})
        with open(file_path, "r", encoding="utf-8") as f:
            assert f.read() == "V1"

        # Повторно применяем (Reapply) к V2
        res_re = client.post(f"/api/records/{rec_id}/reapply")
        assert res_re.status_code == 200
        with open(file_path, "r", encoding="utf-8") as f:
            assert f.read() == "V2"

        # Читаем файл через API просмотрщика
        res_view = client.get(f"/api/projects/{proj_id}/file-content?rel_path=demo.py")
        assert res_view.status_code == 200
        assert res_view.json()["content"] == "V2"


def test_rollback_with_manual_edit_detection():
    with tempfile.TemporaryDirectory() as temp_dir:
        client, repo = setup_test_app(temp_dir)

        # 1. Создаем проект
        res_p = client.post("/api/projects", json={"name": "P1", "root_dir": temp_dir})
        proj_id = res_p.json()["id"]
        prof_id = client.get(f"/api/projects/{proj_id}/profiles").json()[0]["id"]

        # Создаем файл на диске
        file_path = os.path.join(temp_dir, "code.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("ORIGINAL_CONTENT")

        # Отмечаем как writable
        client.post(f"/api/profiles/{prof_id}/files", json={"rel_path": "code.py", "state": "writable"})

        # 2. Выполняем замену нейросетью
        edit_tag = "fs" + "_" + "edit"
        search_tag = "fs" + "_" + "search"
        replace_tag = "fs" + "_" + "replace"
        xml = (
            f'<{edit_tag} path="code.py">\n'
            f'<{search_tag}>ORIGINAL_CONTENT</{search_tag}>\n'
            f'<{replace_tag}>AI_PATCHED_CONTENT</{replace_tag}>\n'
            f'</{edit_tag}>'
        )
        res_exec = client.post(
            f"/api/projects/{proj_id}/execute?profile_id={prof_id}",
            json={"xml_content": xml, "allow_management": False}
        )
        sess_id = res_exec.json()["session_id"]
        records = client.get(f"/api/sessions/{sess_id}").json()
        rec_id = records[0]["id"]

        # Проверяем, что файл изменился
        with open(file_path, "r", encoding="utf-8") as f:
            assert f.read() == "AI_PATCHED_CONTENT"

        # 3. Вносим ручные правки на диске
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("AI_PATCHED_CONTENT + MANUAL_EDIT")

        # 4. Попытка отката без force -> должна задетектировать manual_edited=True
        res_rb1 = client.post(f"/api/records/{rec_id}/rollback", json={"force": False})
        assert res_rb1.status_code == 200
        assert res_rb1.json()["manual_edited"] is True

        # 5. Откат с force=True -> должен успешно вернуть ORIGINAL_CONTENT
        res_rb2 = client.post(f"/api/records/{rec_id}/rollback", json={"force": True})
        assert res_rb2.status_code == 200
        assert res_rb2.json()["success"] is True

        with open(file_path, "r", encoding="utf-8") as f:
            assert f.read() == "ORIGINAL_CONTENT"


def test_snapshots_lifecycle():
    with tempfile.TemporaryDirectory() as temp_dir:
        client, repo = setup_test_app(temp_dir)

        res_p = client.post("/api/projects", json={"name": "SnapProj", "root_dir": temp_dir})
        proj_id = res_p.json()["id"]
        prof_id = client.get(f"/api/projects/{proj_id}/profiles").json()[0]["id"]

        # Создаем файлы
        f1 = os.path.join(temp_dir, "f1.txt")
        with open(f1, "w", encoding="utf-8") as f:
            f.write("VERSION_1")

        client.post(f"/api/profiles/{prof_id}/files", json={"rel_path": "f1.txt", "state": "writable"})

        # 1. Создаем снапшот
        res_snap = client.post(
            f"/api/projects/{proj_id}/snapshots?profile_id={prof_id}",
            json={"name": "v1.0", "for_all_profiles": False}
        )
        assert res_snap.status_code == 200
        snap_id = res_snap.json()["id"]

        # 2. Модифицируем файл на диске
        with open(f1, "w", encoding="utf-8") as f:
            f.write("VERSION_2_RUINED")

        # 3. Восстанавливаем снапшот
        res_restore = client.post(f"/api/snapshots/{snap_id}/restore")
        assert res_restore.status_code == 200

        # Файл вернулся к VERSION_1
        with open(f1, "r", encoding="utf-8") as f:
            assert f.read() == "VERSION_1"

        # 4. Удаляем снапшот
        res_del = client.delete(f"/api/snapshots/{snap_id}")
        assert res_del.status_code == 200
        assert len(client.get(f"/api/projects/{proj_id}/snapshots").json()) == 0


def test_profile_deletion_and_default_recreation():
    with tempfile.TemporaryDirectory() as temp_dir:
        client, repo = setup_test_app(temp_dir)

        res_p = client.post("/api/projects", json={"name": "ProfProj", "root_dir": temp_dir})
        proj_id = res_p.json()["id"]

        # Создаем кастомный профиль
        res_c = client.post(f"/api/projects/{proj_id}/profiles", json={"name": "Custom"})
        c_id = res_c.json()["id"]

        # Удаляем кастомный
        res_del = client.delete(f"/api/profiles/{c_id}")
        assert res_del.status_code == 200

        # Удаляем дефолтный профиль -> система должна автоматически пересоздать default
        def_id = client.get(f"/api/projects/{proj_id}/profiles").json()[0]["id"]
        res_del_def = client.delete(f"/api/profiles/{def_id}")
        assert res_del_def.status_code == 200

        profiles_left = client.get(f"/api/projects/{proj_id}/profiles").json()
        assert len(profiles_left) == 1
        assert profiles_left[0]["name"] == "default"