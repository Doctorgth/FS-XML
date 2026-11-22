import os
import sqlite3
import subprocess
import sys
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from core.sandbox import Sandbox, SecurityException
from server.database.repository import DatabaseRepository
from server.services.context_service import ContextService
from server.services.profile_service import ProfileService
from server.services.project_service import ProjectService

# Роутер создается изолированно внутри register_routes


class CreateProjectRequest(BaseModel):
    name: str
    root_dir: str


class UpdateProjectDirRequest(BaseModel):
    root_dir: str


class SaveFileContentRequest(BaseModel):
    content: str


class CreateSnapshotRequest(BaseModel):
    name: str
    for_all_profiles: bool = False


class RollbackChangeRequest(BaseModel):
    force: bool = False


class CreateProfileRequest(BaseModel):
    name: str


class UpdateFileRuleRequest(BaseModel):
    rel_path: str
    state: str


class BulkUpdateFileRulesRequest(BaseModel):
    rules: List[UpdateFileRuleRequest]


class ExecuteXmlRequest(BaseModel):
    xml_content: str
    allow_management: bool = False


class ImportConfigRequest(BaseModel):
    config_path: str
    root_dir: Optional[str] = None


class SetBackgroundRequest(BaseModel):
    file_path: str


def _run_hidden_subprocess(cmd: List[str]) -> subprocess.CompletedProcess:
    kwargs: dict = {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    kwargs["env"] = env
    if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(cmd, **kwargs)


def _open_native_folder_dialog(title: str = "Выберите корневую папку проекта") -> Optional[str]:
    try:
        import webview
        if getattr(webview, "windows", None):
            dialog_type = getattr(getattr(webview, "FileDialog", None), "FOLDER", None)
            if dialog_type is None:
                dialog_type = getattr(webview, "FOLDER_DIALOG", 20)
            result = webview.windows[0].create_file_dialog(dialog_type)
            if result:
                return os.path.normpath(result[0]).replace("\\", "/")
            return None
    except Exception:
        pass

    code = (
        "import tkinter as tk; from tkinter import filedialog; "
        "r = tk.Tk(); r.withdraw(); r.attributes('-topmost', True); "
        "r.focus_force(); "
        f"f = filedialog.askdirectory(parent=r, title={title!r}); "
        "print(f if f else '')"
    )
    res = _run_hidden_subprocess([sys.executable, "-c", code])
    if res.returncode == 0:
        folder_selected = res.stdout.strip()
        return os.path.normpath(folder_selected).replace("\\", "/") if folder_selected else None

    if sys.platform == "win32":
        ps_script = (
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$d = New-Object System.Windows.Forms.FolderBrowserDialog; "
            f"$d.Description = '{title}'; "
            "if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $d.SelectedPath }"
        )
        ps_res = _run_hidden_subprocess(["powershell", "-NoProfile", "-STA", "-Command", ps_script])
        if ps_res.returncode == 0:
            selected = ps_res.stdout.strip()
            return os.path.normpath(selected).replace("\\", "/") if selected else None
        raise RuntimeError(ps_res.stderr.strip() or res.stderr.strip() or "Failed to open folder dialog")

    raise RuntimeError(res.stderr.strip() or "Failed to open folder dialog")


def _open_native_file_dialog(title: str, pywebview_types: tuple, tk_types: list, ps_filter: str) -> Optional[str]:
    try:
        import webview
        if getattr(webview, "windows", None):
            dialog_type = getattr(getattr(webview, "FileDialog", None), "OPEN", None)
            if dialog_type is None:
                dialog_type = getattr(webview, "OPEN_DIALOG", 10)
            result = webview.windows[0].create_file_dialog(
                dialog_type, allow_multiple=False, file_types=pywebview_types
            )
            if result:
                return os.path.normpath(result[0]).replace("\\", "/")
            return None
    except Exception:
        pass

    code = (
        "import tkinter as tk; from tkinter import filedialog; "
        "r = tk.Tk(); r.withdraw(); r.attributes('-topmost', True); "
        "r.focus_force(); "
        f"f = filedialog.askopenfilename(parent=r, title={title!r}, filetypes={tk_types!r}); "
        "print(f if f else '')"
    )
    res = _run_hidden_subprocess([sys.executable, "-c", code])
    if res.returncode == 0:
        file_selected = res.stdout.strip()
        return os.path.normpath(file_selected).replace("\\", "/") if file_selected else None

    if sys.platform == "win32":
        ps_script = (
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$d = New-Object System.Windows.Forms.OpenFileDialog; "
            f"$d.Title = '{title}'; "
            f"$d.Filter = '{ps_filter}'; "
            "if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $d.FileName }"
        )
        ps_res = _run_hidden_subprocess(["powershell", "-NoProfile", "-STA", "-Command", ps_script])
        if ps_res.returncode == 0:
            selected = ps_res.stdout.strip()
            return os.path.normpath(selected).replace("\\", "/") if selected else None
        raise RuntimeError(ps_res.stderr.strip() or res.stderr.strip() or "Failed to open file dialog")

    raise RuntimeError(res.stderr.strip() or "Failed to open file dialog")


def register_routes(
    repo: DatabaseRepository,
    project_service: ProjectService,
    profile_service: ProfileService,
    context_service: ContextService
):
    api_router = APIRouter(prefix="/api")

    def _assert_profile_belongs_to_project(project_id: int, profile_id: int) -> None:
        profiles = repo.list_profiles(project_id)
        if not any(p.id == profile_id for p in profiles):
            raise HTTPException(
                status_code=404,
                detail=f"Профиль {profile_id} не найден в проекте {project_id}."
            )

    @api_router.get("/projects")
    def get_projects():
        return repo.list_projects()

    @api_router.post("/projects")
    def create_project(req: CreateProjectRequest):
        clean_name = req.name.strip()
        if not clean_name:
            raise HTTPException(status_code=400, detail="Название проекта не может быть пустым.")
        clean_dir = os.path.normpath(
            os.path.abspath(os.path.expanduser(req.root_dir.strip().strip('"').strip("'")))
        ).replace("\\", "/")
        if not os.path.isdir(clean_dir):
            raise HTTPException(status_code=400, detail=f"Директория '{clean_dir}' не существует на диске.")
        try:
            return repo.create_project(clean_name, clean_dir)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка создания проекта: {str(e)}")

    @api_router.delete("/projects/{project_id}")
    def delete_project(project_id: int):
        ok = repo.delete_project(project_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"success": True}

    @api_router.put("/projects/{project_id}/directory")
    def update_project_dir(project_id: int, req: UpdateProjectDirRequest):
        if not repo.get_project(project_id):
            raise HTTPException(status_code=404, detail="Project not found")
        clean_dir = os.path.normpath(
            os.path.abspath(os.path.expanduser(req.root_dir.strip().strip('"').strip("'")))
        ).replace("\\", "/")
        if not os.path.isdir(clean_dir):
            raise HTTPException(status_code=400, detail="Directory does not exist on disk")
        try:
            with repo._get_connection() as conn:
                conn.execute("UPDATE projects SET root_dir = ? WHERE id = ?", (clean_dir, project_id))
                conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail=f"Директория '{clean_dir}' уже используется другим проектом.")
        return {"success": True, "root_dir": clean_dir}

    @api_router.post("/system/select-folder")
    def open_system_folder_dialog():
        try:
            folder_selected = _open_native_folder_dialog("Выберите корневую папку проекта")
            return {"folder": folder_selected}
        except Exception as e:
            return {"folder": None, "error": str(e)}

    @api_router.get("/projects/{project_id}/profiles")
    def get_profiles(project_id: int):
        return profile_service.list_profiles(project_id)

    @api_router.post("/projects/{project_id}/profiles")
    def create_profile(project_id: int, req: CreateProfileRequest):
        if not repo.get_project(project_id):
            raise HTTPException(status_code=404, detail="Project not found")
        clean_name = req.name.strip()
        if not clean_name:
            raise HTTPException(status_code=400, detail="Имя профиля не может быть пустым.")
        try:
            return profile_service.create_profile(project_id, clean_name)
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail=f"Профиль '{clean_name}' уже существует в проекте.")

    @api_router.delete("/profiles/{profile_id}")
    def delete_profile_endpoint(profile_id: int):
        ok = repo.delete_profile(profile_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Profile not found")
        return {"success": True}

    @api_router.get("/ignore/global")
    def get_global_ignore():
        path = "fsignore_global"
        content = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        return {"content": content}

    @api_router.post("/ignore/global")
    def save_global_ignore(req: SaveFileContentRequest):
        with open("fsignore_global", "w", encoding="utf-8") as f:
            f.write(req.content)
        context_service.ignore.reload_global_rules()
        return {"success": True}

    @api_router.get("/projects/{project_id}/ignore/project")
    def get_project_ignore(project_id: int):
        project = repo.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        path = os.path.join(project.root_dir, ".fsignore")
        content = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        return {"content": content}

    @api_router.post("/projects/{project_id}/ignore/project")
    def save_project_ignore(project_id: int, req: SaveFileContentRequest):
        project = repo.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        path = os.path.join(project.root_dir, ".fsignore")
        with open(path, "w", encoding="utf-8") as f:
            f.write(req.content)
        return {"success": True}

    @api_router.get("/profiles/{profile_id}/files")
    def get_profile_files(profile_id: int, project_id: int):
        project = repo.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        _assert_profile_belongs_to_project(project_id, profile_id)
        rules = profile_service.get_rules(profile_id)
        return context_service.build_file_tree(project.root_dir, rules)

    @api_router.post("/profiles/{profile_id}/files")
    def update_file_rule(profile_id: int, req: UpdateFileRuleRequest):
        profile_service.set_rule(profile_id, req.rel_path, req.state)
        return {"success": True}

    @api_router.post("/profiles/{profile_id}/files/bulk")
    def update_file_rules_bulk(profile_id: int, req: BulkUpdateFileRulesRequest):
        pairs = [(r.rel_path, r.state) for r in req.rules]
        profile_service.set_rules_bulk(profile_id, pairs)
        return {"success": True, "updated": len(pairs)}

    @api_router.get("/projects/{project_id}/dump")
    def get_dump(project_id: int, profile_id: int, include_unmarked: bool = False, ignore_tests: bool = False):
        project = repo.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        _assert_profile_belongs_to_project(project_id, profile_id)
        rules = profile_service.get_rules(profile_id)
        dump_text = context_service.generate_dump(project.root_dir, rules, include_unmarked, ignore_tests)
        dump_path = os.path.join(project.root_dir, "context_dump.txt")
        with open(dump_path, "w", encoding="utf-8", newline="") as f:
            f.write(dump_text)
        return {"dump": dump_text, "dump_path": dump_path.replace("\\", "/")}

    @api_router.post("/projects/{project_id}/execute")
    def execute_xml(project_id: int, profile_id: int, req: ExecuteXmlRequest):
        if not repo.get_project(project_id):
            raise HTTPException(status_code=404, detail="Project not found")
        _assert_profile_belongs_to_project(project_id, profile_id)
        try:
            return project_service.execute_patch(
                project_id,
                profile_id,
                req.xml_content,
                req.allow_management
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка выполнения XML: {str(e)}")

    @api_router.get("/projects/{project_id}/history")
    def get_history(project_id: int):
        return repo.list_sessions(project_id)

    @api_router.get("/sessions/{session_id}")
    def get_session_details(session_id: int):
        return repo.get_session_details(session_id)

    @api_router.post("/records/{record_id}/rollback")
    def rollback_record(record_id: int, req: RollbackChangeRequest):
        with repo._get_connection() as conn:
            rec = conn.execute("SELECT * FROM change_records WHERE id = ?", (record_id,)).fetchone()
            if not rec:
                raise HTTPException(status_code=404, detail="Record not found")

            sess = conn.execute("SELECT project_id FROM execution_sessions WHERE id = ?", (rec["session_id"],)).fetchone()
            project = repo.get_project(sess["project_id"])

        if rec["command_tag"] not in ("fs_create", "fs_edit") or not rec["target_path"]:
            raise HTTPException(
                status_code=400,
                detail=f"Откат для команды '{rec['command_tag']}' не поддерживается."
            )

        try:
            abs_path = Sandbox.resolve_safe_path(project.root_dir, rec["target_path"])
        except SecurityException as e:
            raise HTTPException(status_code=403, detail=str(e))

        # Проверяем наличие файла на диске
        if not os.path.exists(abs_path):
            raise HTTPException(status_code=400, detail="Target file no longer exists on disk")

        with open(abs_path, "r", encoding="utf-8", errors="replace", newline="") as f:
            current_disk = f.read()

        # Детекция ручных правок: если диск отличается от того, что записала нейросеть (new_snapshot)
        is_manually_edited = False
        if rec["new_snapshot"] is not None:
            if current_disk.replace("\r\n", "\n") != rec["new_snapshot"].replace("\r\n", "\n"):
                is_manually_edited = True

        if is_manually_edited and not req.force:
            return {
                "success": False,
                "manual_edited": True,
                "message": "Файл был изменен вручную после применения нейросетью. Требуется подтверждение перезаписи."
            }

        # Выполняем откат к original_snapshot (удаление файла строго только для fs_create)
        if rec["command_tag"] == "fs_create" and rec["original_snapshot"] is None:
            try:
                os.remove(abs_path)
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Failed to remove created file: {err}")
        elif rec["original_snapshot"] is not None:
            with open(abs_path, "w", encoding="utf-8", newline="") as f:
                f.write(rec["original_snapshot"])
        else:
            raise HTTPException(status_code=400, detail="Original snapshot is missing for rollback")

        # Обновляем статус в БД
        with repo._get_connection() as conn:
            conn.execute("UPDATE change_records SET status = 'rolled_back' WHERE id = ?", (record_id,))
            conn.commit()

        return {"success": True, "manual_edited": False}

    @api_router.post("/records/{record_id}/reapply")
    def reapply_record(record_id: int):
        with repo._get_connection() as conn:
            rec = conn.execute("SELECT * FROM change_records WHERE id = ?", (record_id,)).fetchone()
            if not rec:
                raise HTTPException(status_code=404, detail="Record not found")

            sess = conn.execute("SELECT project_id FROM execution_sessions WHERE id = ?", (rec["session_id"],)).fetchone()
            project = repo.get_project(sess["project_id"])

        if rec["command_tag"] not in ("fs_create", "fs_edit") or not rec["target_path"]:
            raise HTTPException(
                status_code=400,
                detail=f"Повторное применение для команды '{rec['command_tag']}' не поддерживается."
            )

        if rec["new_snapshot"] is None:
            raise HTTPException(status_code=400, detail="No new_snapshot saved for reapply")

        try:
            abs_path = Sandbox.resolve_safe_path(project.root_dir, rec["target_path"])
        except SecurityException as e:
            raise HTTPException(status_code=403, detail=str(e))
        parent_dir = os.path.dirname(abs_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        with open(abs_path, "w", encoding="utf-8", newline="") as f:
            f.write(rec["new_snapshot"])

        with repo._get_connection() as conn:
            conn.execute("UPDATE change_records SET status = 'success' WHERE id = ?", (record_id,))
            conn.commit()

        return {"success": True}

    @api_router.get("/projects/{project_id}/file-content")
    def get_project_file_content(project_id: int, rel_path: str):
        project = repo.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        try:
            abs_path = Sandbox.resolve_safe_path(project.root_dir, rel_path)
            if not os.path.isfile(abs_path):
                raise HTTPException(status_code=404, detail="File not found on disk")
            if context_service.is_binary_file(abs_path):
                return {"content": "# [БИНАРНЫЙ ФАЙЛ]", "is_binary": True}
            with open(abs_path, "r", encoding="utf-8", errors="replace", newline="") as f:
                return {"content": f.read(), "is_binary": False}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # API Снапшотов проекта
    @api_router.get("/projects/{project_id}/snapshots")
    def get_snapshots(project_id: int):
        return repo.list_snapshots(project_id)

    @api_router.post("/projects/{project_id}/snapshots")
    def create_snapshot(project_id: int, profile_id: int, req: CreateSnapshotRequest):
        import json
        project = repo.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        _assert_profile_belongs_to_project(project_id, profile_id)

        target_profile_id = None if req.for_all_profiles else profile_id

        # Собираем отмеченные файлы
        profiles_to_collect = []
        if req.for_all_profiles:
            profiles_to_collect = repo.list_profiles(project_id)
        else:
            profiles_to_collect = [p for p in repo.list_profiles(project_id) if p.id == profile_id]

        snapshot_payload = {
            "profiles": {},
            "files": {}
        }

        for prof in profiles_to_collect:
            rules = repo.get_profile_rules(prof.id)
            snapshot_payload["profiles"][prof.id] = {
                "name": prof.name,
                "rules": rules
            }
            for rel_path, state in rules.items():
                if state in ("writable", "readonly"):
                    try:
                        abs_p = Sandbox.resolve_safe_path(project.root_dir, rel_path)
                        if os.path.isfile(abs_p) and not context_service.is_binary_file(abs_p):
                            with open(abs_p, "r", encoding="utf-8", errors="replace", newline="") as f:
                                snapshot_payload["files"][rel_path] = f.read()
                    except Exception:
                        pass

        snap_id = repo.create_snapshot(
            project_id=project_id,
            profile_id=target_profile_id,
            name=req.name,
            data_json=json.dumps(snapshot_payload, ensure_ascii=False)
        )
        return {"success": True, "id": snap_id}

    @api_router.post("/snapshots/{snapshot_id}/restore")
    def restore_snapshot(snapshot_id: int):
        import json
        snap = repo.get_snapshot(snapshot_id)
        if not snap:
            raise HTTPException(status_code=404, detail="Snapshot not found")

        project = repo.get_project(snap["project_id"])
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        data = json.loads(snap["snapshot_data"])

        # Проверяем все пути перед записью на диск
        resolved_files = []
        try:
            for rel_path, content in data.get("files", {}).items():
                abs_p = Sandbox.resolve_safe_path(project.root_dir, rel_path)
                resolved_files.append((abs_p, content))
        except SecurityException as e:
            raise HTTPException(status_code=403, detail=str(e))

        # Восстанавливаем файлы на диск
        for abs_p, content in resolved_files:
            parent_dir = os.path.dirname(abs_p)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            with open(abs_p, "w", encoding="utf-8", newline="") as f:
                f.write(content)

        # Восстанавливаем профили и очищаем старые правила перед записью правил снапшота
        for prof_id_str, p_info in data.get("profiles", {}).items():
            existing = [p for p in repo.list_profiles(project.id) if p.name == p_info["name"]]
            target_p = existing[0] if existing else repo.create_profile(project.id, p_info["name"])
            repo.clear_profile_rules(target_p.id)
            for rel_path, state in p_info.get("rules", {}).items():
                if state in ("writable", "readonly"):
                    repo.set_profile_file_rule(target_p.id, rel_path, state)

        return {"success": True}

    @api_router.delete("/snapshots/{snapshot_id}")
    def delete_snapshot_endpoint(snapshot_id: int):
        ok = repo.delete_snapshot(snapshot_id)
        return {"success": ok}

    @api_router.delete("/projects/{project_id}/history")
    def clear_history(project_id: int):
        repo.clear_project_history(project_id)
        return {"success": True}

    @api_router.post("/projects/{project_id}/open-folder")
    def open_project_folder(project_id: int):
        project = repo.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if not os.path.isdir(project.root_dir):
            raise HTTPException(status_code=400, detail="Project directory does not exist on disk")
        try:
            import platform
            import subprocess
            system = platform.system()
            if system == "Windows":
                os.startfile(os.path.normpath(project.root_dir))
            elif system == "Darwin":
                subprocess.Popen(["open", project.root_dir])
            else:
                subprocess.Popen(["xdg-open", project.root_dir])
            return {"success": True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to open folder: {str(e)}")

    @api_router.post("/projects/{project_id}/config/save")
    def save_project_config(project_id: int):
        import json
        project = repo.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if not os.path.isdir(project.root_dir):
            raise HTTPException(status_code=400, detail="Project directory does not exist on disk")

        profiles = repo.list_profiles(project_id)
        config_data = {
            "version": "1.0",
            "project_name": project.name,
            "profiles": []
        }
        for prof in profiles:
            rules = repo.get_profile_rules(prof.id)
            config_data["profiles"].append({
                "name": prof.name,
                "is_default": prof.is_default,
                "rules": rules
            })

        config_path = os.path.join(project.root_dir, "fs_orchestrator_config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

        return {"success": True, "config_path": config_path.replace("\\", "/")}

    @api_router.post("/system/select-config-file")
    def open_config_file_dialog():
        try:
            file_selected = _open_native_file_dialog(
                title="Выберите файл конфигурации",
                pywebview_types=("JSON config (*.json)", "All files (*.*)"),
                tk_types=[("JSON config", "*.json"), ("All files", "*.*")],
                ps_filter="JSON config (*.json)|*.json|All files (*.*)|*.*",
            )
            return {"file_path": file_selected}
        except Exception as e:
            return {"file_path": None, "error": str(e)}

    @api_router.post("/projects/import-config")
    def import_project_config(req: ImportConfigRequest):
        import json
        clean_config_path = os.path.abspath(os.path.expanduser(req.config_path.strip().strip('"').strip("'")))
        if not os.path.isfile(clean_config_path):
            raise HTTPException(status_code=404, detail=f"Файл конфигурации '{clean_config_path}' не найден.")

        try:
            with open(clean_config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка чтения JSON конфигурации: {str(e)}")

        if not isinstance(config_data, dict) or not isinstance(config_data.get("profiles"), list):
            raise HTTPException(status_code=400, detail="Некорректный формат файла конфигурации.")

        target_root = req.root_dir if req.root_dir else os.path.dirname(clean_config_path)
        clean_root = os.path.normpath(
            os.path.abspath(os.path.expanduser(target_root.strip().strip('"').strip("'")))
        ).replace("\\", "/")
        if not os.path.isdir(clean_root):
            raise HTTPException(status_code=400, detail=f"Директория проекта '{clean_root}' не существует.")

        norm_target = os.path.normcase(os.path.abspath(clean_root))
        existing_project = None
        for proj in repo.list_projects():
            if os.path.normcase(os.path.abspath(proj.root_dir)) == norm_target:
                existing_project = proj
                break

        project_name = str(config_data.get("project_name") or "").strip()
        if not project_name:
            project_name = os.path.basename(clean_root) or "Imported Project"

        if existing_project:
            project = existing_project
        else:
            project = repo.create_project(project_name, clean_root)

        existing_profiles = {p.name: p for p in repo.list_profiles(project.id)}
        imported_profiles = 0
        imported_rules = 0

        for prof_entry in config_data.get("profiles", []):
            if not isinstance(prof_entry, dict):
                continue
            prof_name = str(prof_entry.get("name") or "").strip()
            if not prof_name:
                continue

            if prof_name in existing_profiles:
                target_prof = existing_profiles[prof_name]
            else:
                target_prof = repo.create_profile(project.id, prof_name)
                existing_profiles[prof_name] = target_prof

            repo.clear_profile_rules(target_prof.id)
            rules = prof_entry.get("rules", {})
            if isinstance(rules, dict):
                for rel_path, state in rules.items():
                    if state in ("writable", "readonly"):
                        try:
                            Sandbox.resolve_safe_path(clean_root, str(rel_path))
                        except SecurityException:
                            continue
                        norm_rel = Sandbox.normalize_rel_path(str(rel_path))
                        repo.set_profile_file_rule(target_prof.id, norm_rel, state)
                        imported_rules += 1
            imported_profiles += 1

        return {
            "success": True,
            "project": project,
            "imported_profiles": imported_profiles,
            "imported_rules": imported_rules
        }

    def _save_background_from_path(file_path: str) -> str:
        import shutil
        clean_path = os.path.abspath(os.path.expanduser(file_path.strip().strip('"').strip("'")))
        if not os.path.isfile(clean_path):
            raise HTTPException(status_code=404, detail=f"Файл '{clean_path}' не найден.")

        os.makedirs("images", exist_ok=True)
        filename = os.path.basename(clean_path)
        if filename in ("FS-XML.ico", "FS-XML.png"):
            filename = f"custom_{filename}"

        dest_path = os.path.join("images", filename)
        if os.path.realpath(clean_path) != os.path.realpath(dest_path):
            shutil.copy2(clean_path, dest_path)

        repo.set_setting("background_image", filename)
        return filename

    @api_router.get("/settings/background")
    def get_background_setting():
        saved = repo.get_setting("background_image")
        enabled_val = repo.get_setting("background_enabled", "true")
        is_enabled = enabled_val.lower() in ("true", "1", "yes")

        if saved and os.path.isfile(os.path.join("images", saved)):
            return {
                "filename": saved,
                "background_url": f"/images/{saved}",
                "enabled": is_enabled,
            }
        return {
            "filename": "background.png",
            "background_url": "/images/background.png",
            "enabled": is_enabled,
        }

    @api_router.put("/settings/background/toggle")
    def toggle_background_setting(enabled: bool):
        repo.set_setting("background_enabled", "true" if enabled else "false")
        return {"success": True, "enabled": enabled}

    @api_router.post("/settings/background")
    def set_background_setting(req: SetBackgroundRequest):
        filename = _save_background_from_path(req.file_path)
        return {"success": True, "filename": filename, "background_url": f"/images/{filename}"}

    @api_router.post("/settings/background/select")
    def select_background_image():
        try:
            file_selected = _open_native_file_dialog(
                title="Выберите фоновое изображение",
                pywebview_types=("Изображения (*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif)", "Все файлы (*.*)"),
                tk_types=[("Изображения", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"), ("Все файлы", "*.*")],
                ps_filter="Изображения (*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif)|*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif|Все файлы (*.*)|*.*",
            )
            if not file_selected:
                return {"selected": False, "filename": None, "background_url": None}
            filename = _save_background_from_path(file_selected)
            return {"selected": True, "filename": filename, "background_url": f"/images/{filename}"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @api_router.get("/prompt")
    def get_system_prompt():
        prompt_path = "FS-XML.txt"
        if not os.path.exists(prompt_path):
            return {"prompt": "Prompt file FS-XML.txt not found."}
        with open(prompt_path, "r", encoding="utf-8", errors="replace") as f:
            return {"prompt": f.read()}

    return api_router