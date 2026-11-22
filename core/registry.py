from __future__ import annotations
from typing import Dict, List, Optional, TYPE_CHECKING
from core.types import CommandMetadata, CommandType

if TYPE_CHECKING:
    from core.handlers.base import BaseCommandHandler


class CommandRegistry:
    def __init__(self) -> None:
        self._handlers: Dict[str, BaseCommandHandler] = {}

    def register(self, handler: BaseCommandHandler) -> None:
        tag = handler.metadata.tag.lower()
        self._handlers[tag] = handler

    def unregister(self, tag: str) -> Optional[BaseCommandHandler]:
        return self._handlers.pop(tag.lower(), None)

    def get_handler(self, tag: str) -> Optional[BaseCommandHandler]:
        return self._handlers.get(tag.lower())

    def get_metadata(self, tag: str) -> Optional[CommandMetadata]:
        handler = self.get_handler(tag)
        return handler.metadata if handler else None

    def list_all(self) -> List[CommandMetadata]:
        return [handler.metadata for handler in self._handlers.values()]

    def list_by_type(self, cmd_type: CommandType) -> List[CommandMetadata]:
        return [
            handler.metadata
            for handler in self._handlers.values()
            if handler.metadata.command_type == cmd_type
        ]


registry = CommandRegistry()