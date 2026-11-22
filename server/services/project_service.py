import os
from typing import Dict, List, Optional
from core.engine import CoreEngine
from core.types import ExecutionContext, FileState
from server.database.models import ChangeRecordModel, ProjectModel
from server.database.repository import DatabaseRepository
from server.services.context_service import ContextService


class ProjectService:
    def __init__(
        self,
        repo: DatabaseRepository,
        context_service: ContextService,
        engine: CoreEngine
    ) -> None:
        self.repo = repo
        self.context_service = context_service
        self.engine = engine

    def get_project_permissions(self, profile_id: int) -> Dict[str, FileState]:
        raw_rules = self.repo.get_profile_rules(profile_id)
        perms = {}
        for path, state in raw_rules.items():
            if state == "writable":
                perms[path] = FileState.WRITABLE
            elif state == "readonly":
                perms[path] = FileState.READONLY
            else:
                perms[path] = FileState.UNMARKED
        return perms

    def execute_patch(
        self,
        project_id: int,
        profile_id: int,
        raw_xml: str,
        allow_management: bool
    ) -> dict:
        project = self.repo.get_project(project_id)
        if not project:
            raise ValueError(f"Project with id {project_id} not found.")

        perms = self.get_project_permissions(profile_id)
        existing_profiles = [p.name for p in self.repo.list_profiles(project_id)]
        context = ExecutionContext(
            root_dir=project.root_dir,
            active_profile=str(profile_id),
            file_permissions=perms,
            allow_management=allow_management,
            custom_state={"existing_profiles": existing_profiles},
        )

        batch_result = self.engine.execute_batch(raw_xml, context)

        import json
        if batch_result.total_commands == 0:
            no_cmd_msg = "Не найдено ни одной распознанной XML-команды. Проверьте корректность тегов."
            err_data = json.dumps({"message": no_cmd_msg}, ensure_ascii=False)
            records = [
                ChangeRecordModel(
                    command_tag="parser",
                    target_path=None,
                    status="error",
                    error_details=err_data,
                    original_snapshot=None,
                    new_snapshot=None
                )
            ]
            session_id = self.repo.record_session(
                project_id=project_id,
                profile_id=profile_id,
                status="error",
                total_commands=0,
                error_count=1,
                records=records
            )
            return {
                "session_id": session_id,
                "status": "error",
                "total_commands": 0,
                "error_count": 1,
                "results": [
                    {
                        "tag": "parser",
                        "success": False,
                        "target_path": None,
                        "message": no_cmd_msg,
                        "details": {}
                    }
                ]
            }

        status_str = "success" if batch_result.is_all_successful else (
            "partial_error" if batch_result.success_count > 0 else "error"
        )

        records = []
        for res in batch_result.results:
            # Если произошла ошибка, сериализуем детали поиска и замены в error_details
            err_data = None
            if not res.success:
                err_payload = {
                    "message": res.message,
                    "search_block": res.details.get("search_block", ""),
                    "replace_block": res.details.get("replace_block", ""),
                }
                if res.original_snapshot is None and res.details.get("actual_disk_content"):
                    err_payload["actual_disk_content"] = res.details.get("actual_disk_content", "")
                err_data = json.dumps(err_payload, ensure_ascii=False)

            records.append(
                ChangeRecordModel(
                    command_tag=res.tag,
                    target_path=res.target_path,
                    status="success" if res.success else "error",
                    error_details=err_data,
                    original_snapshot=res.original_snapshot,
                    new_snapshot=res.new_snapshot
                )
            )

        session_id = self.repo.record_session(
            project_id=project_id,
            profile_id=profile_id,
            status=status_str,
            total_commands=batch_result.total_commands,
            error_count=batch_result.error_count,
            records=records
        )

        for path, new_state in context.file_permissions.items():
            self.repo.set_profile_file_rule(profile_id, path, new_state.value)

        created_profiles = context.custom_state.get("created_profiles", [])
        for prof_name in created_profiles:
            try:
                self.repo.create_profile(project_id, prof_name)
            except Exception:
                pass

        return {
            "session_id": session_id,
            "status": status_str,
            "total_commands": batch_result.total_commands,
            "error_count": batch_result.error_count,
            "results": [
                {
                    "tag": r.tag,
                    "success": r.success,
                    "target_path": r.target_path,
                    "message": r.message,
                    "details": r.details
                }
                for r in batch_result.results
            ]
        }