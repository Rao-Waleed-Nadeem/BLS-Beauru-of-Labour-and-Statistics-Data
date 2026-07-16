"""Registry package.

This file is intentionally light to avoid circular imports.

This module stays import-light so registry helpers can be imported without
eagerly loading the rest of the BLS pipeline.
"""

__all__ = [
    "DatasetRegistryEntry",
    "ProgramRegistryEntry",
    "UrlRegistryEntry",
    "RegistryCache",
    "RegistryLoader",
    "RegistryParser",
    "RegistryValidator",
]


def __getattr__(name: str):
    if name in {"DatasetRegistryEntry", "ProgramRegistryEntry", "UrlRegistryEntry"}:
        from .models import DatasetRegistryEntry, ProgramRegistryEntry, UrlRegistryEntry

        return {
            "DatasetRegistryEntry": DatasetRegistryEntry,
            "ProgramRegistryEntry": ProgramRegistryEntry,
            "UrlRegistryEntry": UrlRegistryEntry,
        }[name]

    if name == "RegistryCache":
        from .cache import RegistryCache

        return RegistryCache
    if name == "RegistryLoader":
        from .loader import RegistryLoader

        return RegistryLoader
    if name == "RegistryParser":
        from .parser import RegistryParser

        return RegistryParser
    if name == "RegistryValidator":
        from .validator import RegistryValidator

        return RegistryValidator

    raise AttributeError(name)

