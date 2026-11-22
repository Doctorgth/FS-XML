import json
import os
import tempfile
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from core.engine import CoreEngine
from core.handlers import register_default_handlers
from server.api.routes import register_routes
from server.database.repository import DatabaseRepository
from server.services.context_service import ContextService
from server.services.ignore_service import IgnoreService
from server.services.profile_service import ProfileService
from server.services.project_service import ProjectService

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


def test_save_and_import_project_config_new_project():
    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as friend_dir:
        # 1. На исходной машине создаем проект, профиль и правила
        client1, _ = setup_test_app(src_dir)
        res_p = client1.post("/api/projects", json={"name": "SharedApp", "root_dir": src_dir})
        assert res_p.status_code == 200
        proj_id = res_p.json()["id"]

        def_prof_id = client1.get(f"/api/projects/{proj_id}/profiles").json()[0]["id"]
        custom_prof_id = client1.post(f"/api/projects/{proj_id}/profiles", json={"name": "Backend"}).json()["id"]

        client1.post(f"/api/profiles/{def_prof_id}/files", json={"rel_path": "README.md", "state": "readonly"})
        client1.post(f"/api/profiles/{custom_prof_id}/files", json={"rel_path": "server/app.py", "state": "writable"})

        # 2. Сохраняем конфигурацию в корень исходного проекта
        res_save = client1.post(f"/api/projects/{proj_id}/config/save")
        assert res_save.status_code == 200
        saved_path = res_save.json()["config_path"]
        assert os.path.isfile(saved_path)

        with open(saved_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["project_name"] == "SharedApp"
        assert len(data["profiles"]) == 2

        # 3. Копируем файл конфигурации в папку друга (новая БД)
        friend_config = os.path.join(friend_dir, "fs_orchestrator_config.json")
        with open(friend_config, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        client2, repo2 = setup_test_app(friend_dir)
        res_imp = client2.post("/api/projects/import-config", json={"config_path": friend_config})
        assert res_imp.status_code == 200
        imp_json = res_imp.json()
        assert imp_json["success"] is True
        assert imp_json["imported_profiles"] == 2
        assert imp_json["imported_rules"] == 2

        # Проверяем, что проект, профили и права создались у друга
        projects2 = client2.get("/api/projects").json()
        assert len(projects2) == 1
        assert projects2[0]["name"] == "SharedApp"

        profiles2 = client2.get(f"/api/projects/{projects2[0]['id']}/profiles").json()
        prof_map = {p["name"]: p["id"] for p in profiles2}
        assert "default" in prof_map
        assert "Backend" in prof_map

        assert repo2.get_profile_rules(prof_map["default"]) == {"README.md": "readonly"}
        assert repo2.get_profile_rules(prof_map["Backend"]) == {"server/app.py": "writable"}


def test_import_config_errors():
    with tempfile.TemporaryDirectory() as temp_dir:
        client, _ = setup_test_app(temp_dir)

        # Несуществующий файл
        res_missing = client.post("/api/projects/import-config", json={"config_path": os.path.join(temp_dir, "none.json")})
        assert res_missing.status_code == 404

        # Невалидный JSON
        bad_json = os.path.join(temp_dir, "bad.json")
        with open(bad_json, "w", encoding="utf-8") as f:
            f.write("{broken")
        res_bad = client.post("/api/projects/import-config", json={"config_path": bad_json})
        assert res_bad.status_code == 400


def test_open_project_folder():
    with tempfile.TemporaryDirectory() as temp_dir:
        client, _ = setup_test_app(temp_dir)

        # Несуществующий проект
        res_404 = client.post("/api/projects/999/open-folder")
        assert res_404.status_code == 404

        res_p = client.post("/api/projects", json={"name": "FolderProj", "root_dir": temp_dir})
        proj_id = res_p.json()["id"]

        with patch("platform.system", return_value="Linux"), patch("subprocess.Popen") as mock_popen:
            res_ok = client.post(f"/api/projects/{proj_id}/open-folder")
            assert res_ok.status_code == 200
            assert res_ok.json()["success"] is True
            mock_popen.assert_called_once()


def test_dump_endpoint_ignore_tests_param():
    with tempfile.TemporaryDirectory() as temp_dir:
        client, _ = setup_test_app(temp_dir)
        proj_id = client.post("/api/projects", json={"name": "DumpProj", "root_dir": temp_dir}).json()["id"]
        prof_id = client.get(f"/api/projects/{proj_id}/profiles").json()[0]["id"]

        with open(os.path.join(temp_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write("MAIN_BODY")
        with open(os.path.join(temp_dir, "test_main.py"), "w", encoding="utf-8") as f:
            f.write("TEST_BODY_HIDDEN")

        client.post(f"/api/profiles/{prof_id}/files", json={"rel_path": "main.py", "state": "writable"})
        client.post(f"/api/profiles/{prof_id}/files", json={"rel_path": "test_main.py", "state": "readonly"})

        res = client.get(f"/api/projects/{proj_id}/dump?profile_id={prof_id}&ignore_tests=true")
        assert res.status_code == 200
        payload = res.json()
        dump_text = payload["dump"]
        assert "MAIN_BODY" in dump_text
        assert "test_main.py [READ_ONLY]" in dump_text
        assert "TEST_BODY_HIDDEN" not in dump_text

        dump_file = os.path.join(temp_dir, "context_dump.txt")
        assert os.path.isfile(dump_file)
        assert payload["dump_path"] == dump_file.replace("\\", "/")
        with open(dump_file, "r", encoding="utf-8") as f:
            assert f.read() == dump_text


def test_background_personalization_copy_and_persistence():
    with tempfile.TemporaryDirectory() as temp_dir:
        client, repo = setup_test_app(temp_dir)

        # По умолчанию background.png и включен
        res_def = client.get("/api/settings/background")
        assert res_def.status_code == 200
        assert res_def.json()["filename"] == "background.png"
        assert res_def.json()["enabled"] is True

        # Тест переключения видимости фона
        res_toggle = client.put("/api/settings/background/toggle?enabled=false")
        assert res_toggle.status_code == 200
        assert res_toggle.json()["enabled"] is False

        res_check = client.get("/api/settings/background")
        assert res_check.json()["enabled"] is False

        client.put("/api/settings/background/toggle?enabled=true")

        # Создаем временный файл фона
        src_img = os.path.join(temp_dir, "test_custom_bg_unit.png")
        with open(src_img, "wb") as f:
            f.write(b"FAKEPNGDATA")

        copied_dest = os.path.join("images", "test_custom_bg_unit.png")
        try:
            res_set = client.post("/api/settings/background", json={"file_path": src_img})
            assert res_set.status_code == 200
            assert res_set.json()["success"] is True
            assert res_set.json()["filename"] == "test_custom_bg_unit.png"
            assert os.path.isfile(copied_dest)

            # Проверяем сохранение в БД
            res_get = client.get("/api/settings/background")
            assert res_get.status_code == 200
            assert res_get.json()["filename"] == "test_custom_bg_unit.png"
            assert res_get.json()["background_url"] == "/images/test_custom_bg_unit.png"
        finally:
            if os.path.isfile(copied_dest):
                os.remove(copied_dest)


def test_background_icon_collision_prefix():
    with tempfile.TemporaryDirectory() as temp_dir:
        client, repo = setup_test_app(temp_dir)

        # Проверяем, что загрузка файла с системным именем FS-XML.ico не перезатирает иконку приложения
        src_ico = os.path.join(temp_dir, "FS-XML.ico")
        with open(src_ico, "wb") as f:
            f.write(b"ICO_DATA")

        res = client.post("/api/settings/background", json={"file_path": src_ico})
        assert res.status_code == 200
        assert res.json()["filename"] == "custom_FS-XML.ico"

        safe_ico_path = os.path.join("images", "custom_FS-XML.ico")
        try:
            assert os.path.isfile(safe_ico_path)
        finally:
            if os.path.isfile(safe_ico_path):
                os.remove(safe_ico_path)