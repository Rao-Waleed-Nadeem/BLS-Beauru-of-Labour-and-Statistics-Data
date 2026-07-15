"""Registry package.

This file is intentionally light to avoid circular imports.

Tests import `pipeline.registry.*` from the top-level compatibility package,
not from here, but this module must still be safe when imported by other
BLS pipeline code.
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

