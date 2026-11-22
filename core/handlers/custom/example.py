from core.handlers.base import BaseCommandHandler
from core.types import (
    CommandMetadata,
    CommandResult,
    CommandType,
    ExecutionContext,
    ParsedCommandNode,
)


class ExampleCustomHandler(BaseCommandHandler):
    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            tag="example",
            command_type=CommandType.CUSTOM,
            description_human="Пример пользовательского обработчика расширения функционала.",
            example_usage="<example action=\"echo\">some data</example>"
        )

    def execute(self, node: ParsedCommandNode, context: ExecutionContext) -> CommandResult:
        action = node.attributes.get("action", "default")
        payload = node.inner_text.strip()

        return CommandResult(
            tag=self.metadata.tag,
            success=True,
            message=f"Custom command executed. Action: '{action}'. Payload length: {len(payload)}",
            details={
                "action": action,
                "payload": payload,
                "active_profile": context.active_profile
            }
        )