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
engine = CoreEngine()

CREATE_TAG = "fs" + "_" + "create"
EDIT_TAG = "fs" + "_" + "edit"
SEARCH_TAG = "fs" + "_" + "search"
REPLACE_TAG = "fs" + "_" + "replace"


def _setup_app(temp_dir: str, ignore_file: str = ""):
    db_path = os.path.join(temp_dir, "test.db")
    repo = DatabaseRepository(db_path)
    ignore = IgnoreService(ignore_file or os.path.join(temp_dir, "fsignore_global"))
    ctx = ContextService(ignore)
    project_svc = ProjectService(repo, ctx, engine)
    profile_svc = ProfileService(repo)

    app = FastAPI()
    app.include_router(register_routes(repo, project_svc, profile_svc, ctx))
    client = TestClient(app)
    return client, repo, ctx


def test_parser_handles_nested_repeated_literal_tags_and_punctuation():
    with tempfile.TemporaryDirectory() as temp_dir:
        doc_path = os.path.join(temp_dir, "doc.py")
        with open(doc_path, "w", encoding="utf-8", newline="") as f:
            f.write(f'closing = "</{EDIT_TAG}>"\nval = 1\n')

        context = ExecutionContext(
            root_dir=temp_dir,
            active_profile="test",
            file_permissions={"doc.py": FileState.WRITABLE},
            allow_management=False
        )

        close_edit = f"</{EDIT_TAG}>"
        close_replace = f"</{REPLACE_TAG}>"
        close_create = f"</{CREATE_TAG}>"

        xml = (
            f'Ниже применён <{EDIT_TAG}> к файлу и <{CREATE_TAG}> для нового файла:\n'
            f'(<{EDIT_TAG} path="doc.py">\n'
            f'<{SEARCH_TAG}>\n'
            f'closing = "{close_edit}"\n'
            f'</{SEARCH_TAG}>\n'
            f'<{REPLACE_TAG}>\n'
            f'closing = "{close_replace}{close_edit}"\n'
            f'example = "<{EDIT_TAG} path=\\"x.py\\"><{SEARCH_TAG}>a</{SEARCH_TAG}><{REPLACE_TAG}>b{close_replace}{close_edit}"\n'
            f'</{REPLACE_TAG}>\n'
            f'<{SEARCH_TAG}>\n'
            f'val = 1\n'
            f'</{SEARCH_TAG}>\n'
            f'<{REPLACE_TAG}>\n'
            f'val = 2\n'
            f'</{REPLACE_TAG}>\n'
            f'</{EDIT_TAG}>), а далее идёт создание файла:\n'
            f'<{CREATE_TAG} path="it\'s/nested.md">\n'
            f'Пример команды:\n'
            f'<{CREATE_TAG} path="inner.txt">hello{close_create}\n'
            f'close_str = "{close_create}"\n'
            f'</{CREATE_TAG}>, конец пакета.'
        )

        res = engine.execute_batch(xml, context)
        assert res.error_count == 0
        assert res.success_count == 2

        with open(doc_path, "r", encoding="utf-8", newline="") as f:
            doc_content = f.read()
        assert f'closing = "{close_replace}{close_edit}"' in doc_content
        assert "val = 2" in doc_content

        nested_file = os.path.join(temp_dir, "it's", "nested.md")
        assert os.path.isfile(nested_file)
        with open(nested_file, "r", encoding="utf-8", newline="") as f:
            nested_content = f.read()
        assert f'<{CREATE_TAG} path="inner.txt">hello{close_create}' in nested_content
        assert f'close_str = "{close_create}"' in nested_content


def test_edit_rejects_empty_search_and_deletes_cleanly_in_attempt2():
    with tempfile.TemporaryDirectory() as temp_dir:
        target = os.path.join(temp_dir, "app.py")
        with open(target, "w", encoding="utf-8", newline="") as f:
            f.write("line1\nline2   \nline3\n")

        context = ExecutionContext(
            root_dir=temp_dir,
            active_profile="test",
            file_permissions={"app.py": FileState.WRITABLE},
        )

        # Пустой search должен возвращать ошибку, а не вставлять в начало файла
        xml_empty = f'<{EDIT_TAG} path="app.py"><{SEARCH_TAG}></{SEARCH_TAG}><{REPLACE_TAG}>INJECTED</{REPLACE_TAG}></{EDIT_TAG}>'
        res_empty = engine.execute_batch(xml_empty, context)
        assert res_empty.error_count == 1
        with open(target, "r", encoding="utf-8", newline="") as f:
            assert "INJECTED" not in f.read()

        # Используем хвостовой \t, чтобы пропустить Attempt 1 и попасть в Attempt 2:
        # Attempt 2 с пустым replace не должен оставлять лишнюю пустую строку
        xml_delete = f'<{EDIT_TAG} path="app.py"><{SEARCH_TAG}>line2\t</{SEARCH_TAG}><{REPLACE_TAG}></{REPLACE_TAG}></{EDIT_TAG}>'
        res_del = engine.execute_batch(xml_delete, context)
        assert res_del.success_count == 1
        with open(target, "r", encoding="utf-8", newline="") as f:
            assert f.read() == "line1\nline3\n"


def test_get_dump_preserves_crlf_and_import_normalizes_paths():
    with tempfile.TemporaryDirectory() as temp_dir:
        client, repo, _ = _setup_app(temp_dir)
        proj_id = client.post("/api/projects", json={"name": "DumpCRLF", "root_dir": temp_dir}).json()["id"]
        prof_id = client.get(f"/api/projects/{proj_id}/profiles").json()[0]["id"]

        crlf_file = os.path.join(temp_dir, "win.py")
        with open(crlf_file, "wb") as f:
            f.write(b"a = 1\r\nb = 2\r\n")

        client.post(f"/api/profiles/{prof_id}/files", json={"rel_path": "win.py", "state": "writable"})
        res_dump = client.get(f"/api/projects/{proj_id}/dump?profile_id={prof_id}")
        assert res_dump.status_code == 200

        with open(os.path.join(temp_dir, "context_dump.txt"), "rb") as f:
            dump_bytes = f.read()
        assert b"\r\r\n" not in dump_bytes

        # Импорт конфига с обратными слэшами в rel_path должен нормализовать их в '/'
        cfg_path = os.path.join(temp_dir, "fs_orchestrator_config.json")
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump({
                "project_name": "DumpCRLF",
                "profiles": [{"name": "default", "rules": {"sub\\win.py": "writable"}}],
            }, f)

        res_imp = client.post("/api/projects/import-config", json={"config_path": cfg_path})
        assert res_imp.status_code == 200
        assert repo.get_profile_rules(prof_id) == {"sub/win.py": "writable"}
def test_audit_batch_cors_profile_dup_sandbox_and_test_files():
    from server.middlewares.cors import setup_cors

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_sec.db")
        repo = DatabaseRepository(db_path)
        ignore = IgnoreService(os.path.join(temp_dir, "fsignore_global"))
        ctx = ContextService(ignore)
        project_svc = ProjectService(repo, ctx, engine)
        profile_svc = ProfileService(repo)

        app = FastAPI()
        setup_cors(app)
        app.include_router(register_routes(repo, project_svc, profile_svc, ctx))
        client = TestClient(app)

        # 1. Чужой Origin блокируется
        res_evil = client.get("/api/projects", headers={"Origin": "https://evil.example"})
        assert res_evil.status_code == 403

        # 2. Валидный локальный Origin разрешен
        res_ok = client.get("/api/projects", headers={"Origin": "http://127.0.0.1:18420"})
        assert res_ok.status_code == 200

        p1 = client.post("/api/projects", json={"name": "P1", "root_dir": temp_dir}).json()["id"]
        prof1 = client.get(f"/api/projects/{p1}/profiles").json()[0]["id"]

        # 3. Несовпадение profile_id и project_id -> 404
        res_mismatch = client.post(
            f"/api/projects/{p1}/execute?profile_id=999999",
            json={"xml_content": f'<{CREATE_TAG} path="x.txt">1</{CREATE_TAG}>', "allow_management": False},
        )
        assert res_mismatch.status_code == 404

        # 4. Создание дубликата профиля через fs_profile_create возвращает ошибку (а не success)
        prof_tag = "fs" + "_" + "profile_create"
        res_dup_prof = client.post(
            f"/api/projects/{p1}/execute?profile_id={prof1}",
            json={"xml_content": f'<{prof_tag} name="default" />', "allow_management": True},
        )
        assert res_dup_prof.status_code == 200
        assert res_dup_prof.json()["error_count"] == 1
        assert res_dup_prof.json()["results"][0]["success"] is False

        # 5. Импорт конфига отбрасывает абсолютные пути и пути с буквой диска
        cfg = os.path.join(temp_dir, "fs_orchestrator_config.json")
        with open(cfg, "w", encoding="utf-8") as f:
            json.dump({
                "project_name": "P1",
                "profiles": [{
                    "name": "default",
                    "rules": {
                        "/etc/passwd": "writable",
                        "C:/Windows/win.ini": "writable",
                        "C:relative_drive.txt": "writable",
                        "safe/app.py": "writable",
                    },
                }],
            }, f)
        res_imp = client.post("/api/projects/import-config", json={"config_path": cfg})
        assert res_imp.status_code == 200
        assert repo.get_profile_rules(prof1) == {"safe/app.py": "writable"}

        # 6. is_test_file распознает *.test.ts и *.spec.ts
        assert ctx.is_test_file("components.test.ts") is True
        assert ctx.is_test_file("app.spec.ts") is True
        assert ctx.is_test_file("contest.py") is False
