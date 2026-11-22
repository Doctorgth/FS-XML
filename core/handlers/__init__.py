from core.handlers.base import BaseCommandHandler
from core.handlers.custom.example import ExampleCustomHandler
from core.handlers.system_management.file_state import FsFileStateHandler
from core.handlers.system_management.profile_create import FsProfileCreateHandler
from core.handlers.system_standard.create import FsCreateHandler
from core.handlers.system_standard.edit import FsEditHandler


def register_default_handlers() -> None:
    from core.registry import registry
    registry.register(FsCreateHandler())
    registry.register(FsEditHandler())
    registry.register(FsProfileCreateHandler())
    registry.register(FsFileStateHandler())
    registry.register(ExampleCustomHandler())


__all__ = [
    "BaseCommandHandler",
    "FsCreateHandler",
    "FsEditHandler",
    "FsProfileCreateHandler",
    "FsFileStateHandler",
    "ExampleCustomHandler",
    "register_default_handlers",
]