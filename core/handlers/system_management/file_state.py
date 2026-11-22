from core.handlers.base import BaseCommandHandler
from core.sandbox import Sandbox
from core.types import (
    CommandMetadata,
    CommandResult,
    CommandType,
    ExecutionContext,
    FileState,
    ParsedCommandNode,
)


class FsFileStateHandler(BaseCommandHandler):
    @property
    def metadata(self) -> CommandMetadata:
        tag_name = "fs" + "_" + "file_state"
        return CommandMetadata(
            tag=tag_name,
            command_type=CommandType.MANAGEMENT,
            description_human="Изменение прав файла: writable, readonly или unmarked.",
            example_usage=f"<{tag_name} path=\"path/to/file.ts\" state=\"writable\" />"
        )

    def execute(self, node: ParsedCommandNode, context: ExecutionContext) -> CommandResult:
        rel_path = node.attributes.get("path")
        target_state_str = node.attributes.get("state", "").lower().strip()

        if not rel_path:
            return CommandResult(
                tag=self.metadata.tag,
                success=False,
                message="Missing required attribute: 'path'"
            )

        try:
            norm_rel = Sandbox.normalize_rel_path(rel_path)
            Sandbox.resolve_safe_path(context.root_dir, norm_rel)

            if target_state_str not in [s.value for s in FileState]:
                return CommandResult(
                    tag=self.metadata.tag,
                    success=False,
                    target_path=norm_rel,
                    message=f"Invalid state '{target_state_str}'. Allowed: 'writable', 'readonly', 'unmarked'"
                )

            new_state = FileState(target_state_str)
            prev_state = context.file_permissions.get(norm_rel, FileState.UNMARKED)

            context.file_permissions[norm_rel] = new_state

            state_changes = context.custom_state.setdefault("state_changes", {})
            state_changes[norm_rel] = new_state.value

            return CommandResult(
                tag=self.metadata.tag,
                success=True,
                target_path=norm_rel,
                message=f"File '{norm_rel}' state changed from '{prev_state.value}' to '{new_state.value}'.",
                details={"previous_state": prev_state.value, "new_state": new_state.value}
            )

        except Exception as e:
            return CommandResult(
                tag=self.metadata.tag,
                success=False,
                target_path=rel_path,
                message=f"Failed to change file state: {str(e)}"
            )