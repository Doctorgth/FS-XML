from core.handlers.base import BaseCommandHandler
from core.types import (
    CommandMetadata,
    CommandResult,
    CommandType,
    ExecutionContext,
    ParsedCommandNode,
)


class FsProfileCreateHandler(BaseCommandHandler):
    @property
    def metadata(self) -> CommandMetadata:
        tag_name = "fs" + "_" + "profile_create"
        return CommandMetadata(
            tag=tag_name,
            command_type=CommandType.MANAGEMENT,
            description_human="Создание нового профиля конфигурации файлов.",
            example_usage=f"<{tag_name} name=\"BackendFocus\" />"
        )

    def execute(self, node: ParsedCommandNode, context: ExecutionContext) -> CommandResult:
        profile_name = node.attributes.get("name", "").strip()
        if not profile_name:
            return CommandResult(
                tag=self.metadata.tag,
                success=False,
                message="Missing required attribute 'name' for new profile."
            )

        existing_profiles = context.custom_state.get("existing_profiles", [])
        if profile_name in existing_profiles:
            return CommandResult(
                tag=self.metadata.tag,
                success=False,
                message=f"Profile '{profile_name}' already exists in project."
            )

        created_profiles = context.custom_state.setdefault("created_profiles", [])
        if profile_name in created_profiles:
            return CommandResult(
                tag=self.metadata.tag,
                success=False,
                message=f"Profile '{profile_name}' already exists in current session."
            )

        created_profiles.append(profile_name)

        return CommandResult(
            tag=self.metadata.tag,
            success=True,
            message=f"Profile '{profile_name}' created successfully.",
            details={"profile_name": profile_name}
        )