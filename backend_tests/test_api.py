import tempfile
from fastapi.testclient import TestClient
from server.api.routes import register_routes
from server.database.repository import DatabaseRepository
from server.services.context_service import ContextService
from server.services.ignore_service import IgnoreService
from server.services.profile_service import ProfileService
from server.services.project_service import ProjectService
from core.engine import CoreEngine
from fastapi import FastAPI


def test_api_full_flow():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = f"{temp_dir}/test.db"
        from core.handlers import register_default_handlers
        register_default_handlers()
        repo = DatabaseRepository(db_path)
        ignore = IgnoreService()
        ctx = ContextService(ignore)
        engine = CoreEngine()
        project_svc = ProjectService(repo, ctx, engine)
        profile_svc = ProfileService(repo)

        app = FastAPI()
        app.include_router(register_routes(repo, project_svc, profile_svc, ctx))
        client = TestClient(app)

        # 1. Создание проекта
        res = client.post("/api/projects", json={"name": "TestProj", "root_dir": temp_dir})
        assert res.status_code == 200
        proj_id = res.json()["id"]

        # 2. Получение профилей (дефолтный создан автоматически)
        res_prof = client.get(f"/api/projects/{proj_id}/profiles")
        assert res_prof.status_code == 200
        profiles = res_prof.json()
        assert len(profiles) >= 1
        prof_id = profiles[0]["id"]

        # 3. Вызов execute API
        create_tag = "fs" + "_" + "create"
        xml = f'<{create_tag} path="hello.txt">Hello API</{create_tag}>'
        res_exec = client.post(
            f"/api/projects/{proj_id}/execute?profile_id={prof_id}",
            json={"xml_content": xml, "allow_management": False}
        )
        assert res_exec.status_code == 200
        assert res_exec.json()["status"] == "success"

        # 4. Проверка истории
        res_hist = client.get(f"/api/projects/{proj_id}/history")
        assert res_hist.status_code == 200
        assert len(res_hist.json()) == 1