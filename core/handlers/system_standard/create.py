import os
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


class FsCreateHandler(BaseCommandHandler):
    @property
    def metadata(self) -> CommandMetadata:
        tag_name = "fs" + "_" + "create"
        return CommandMetadata(
            tag=tag_name,
            command_type=CommandType.STANDARD,
            description_human="Создание нового файла. Возвращает ошибку, если файл уже существует.",
            example_usage=f"<{tag_name} path=\"path/to/file.ext\">\ncontent\n</{tag_name}>"
        )

    def execute(self, node: ParsedCommandNode, context: ExecutionContext) -> CommandResult:
        rel_path = node.attributes.get("path")
        if not rel_path:
            return CommandResult(
                tag=self.metadata.tag,
                success=False,
                message="Missing required attribute: 'path'"
            )

        try:
            abs_path = Sandbox.resolve_safe_path(context.root_dir, rel_path)
            norm_rel = Sandbox.normalize_rel_path(rel_path)

            if os.path.exists(abs_path):
                return CommandResult(
                    tag=self.metadata.tag,
                    success=False,
                    target_path=norm_rel,
                    message=f"Collision Error: File '{norm_rel}' already exists on disk. Use edit command instead."
                )

            os.makedirs(os.path.dirname(abs_path), exist_ok=True)

            content = node.inner_text
            if content.startswith("\r\n"):
                content = content[2:]
            elif content.startswith("\n"):
                content = content[1:]

            with open(abs_path, "w", encoding="utf-8", newline="") as f:
                f.write(content)

            context.file_permissions[norm_rel] = FileState.WRITABLE

            return CommandResult(
                tag=self.metadata.tag,
                success=True,
                target_path=norm_rel,
                message=f"File '{norm_rel}' successfully created.",
                original_snapshot=None,
                new_snapshot=content
            )
        except Exception as e:
            return CommandResult(
                tag=self.metadata.tag,
                success=False,
                target_path=rel_path,
                message=f"Create operation failed: {str(e)}"
            )