from abc import ABC, abstractmethod
from core.types import CommandMetadata, CommandResult, ExecutionContext, ParsedCommandNode


class BaseCommandHandler(ABC):
    @property
    @abstractmethod
    def metadata(self) -> CommandMetadata:
        pass

    @abstractmethod
    def execute(self, node: ParsedCommandNode, context: ExecutionContext) -> CommandResult:
        pass