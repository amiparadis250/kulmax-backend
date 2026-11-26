"""One package per feature (vertical slice). See CLAUDE.md for the rules."""

import importlib
import importlib.util
import pkgutil
from types import ModuleType


def import_feature_modules(module_name: str) -> list[ModuleType]:
    """Import `app.features.<feature>.<module_name>` for every feature that has it.

    Used by Alembic (`models`) and the worker (`jobs`) so new features are picked up
    without editing a central list.
    """
    modules: list[ModuleType] = []
    for info in sorted(pkgutil.iter_modules(__path__), key=lambda i: i.name):
        if not info.ispkg:
            continue
        full_name = f"{__name__}.{info.name}.{module_name}"
        if importlib.util.find_spec(full_name) is not None:
            modules.append(importlib.import_module(full_name))
    return modules
