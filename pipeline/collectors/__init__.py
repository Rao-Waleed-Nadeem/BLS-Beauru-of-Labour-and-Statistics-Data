"""Collector package exports.

Exports are lazy so registry dataclasses can be imported without pulling in
collector runtime dependencies and scheduler modules during package init.
"""

__all__ = [
    "CalendarCollector",
    "CalendarRegistryLoader",
    "CalendarRegistryEntry",
    "ArchiveCollector",
    "ArchiveRegistryLoader",
    "ArchiveRegistryEntry",
    "RSSCollector",
    "RSSRegistryLoader",
    "RSSRegistryEntry",
    "HTMLCollector",
    "HTMLRegistryLoader",
    "HTMLRegistryEntry",
    "APICollector",
    "SeriesRegistryLoader",
    "SeriesRegistryEntry",
]


def __getattr__(name: str):
    if name == "CalendarCollector":
        from .calendar_collector import CalendarCollector

        return CalendarCollector
    if name in {"CalendarRegistryLoader", "CalendarRegistryEntry"}:
        from .calendar_registry_loader import CalendarRegistryEntry, CalendarRegistryLoader

        return {
            "CalendarRegistryLoader": CalendarRegistryLoader,
            "CalendarRegistryEntry": CalendarRegistryEntry,
        }[name]
    if name == "ArchiveCollector":
        from .archive_collector import ArchiveCollector

        return ArchiveCollector
    if name in {"ArchiveRegistryLoader", "ArchiveRegistryEntry"}:
        from .archive_registry_loader import ArchiveRegistryEntry, ArchiveRegistryLoader

        return {
            "ArchiveRegistryLoader": ArchiveRegistryLoader,
            "ArchiveRegistryEntry": ArchiveRegistryEntry,
        }[name]
    if name == "RSSCollector":
        from .rss_collector import RSSCollector

        return RSSCollector
    if name in {"RSSRegistryLoader", "RSSRegistryEntry"}:
        from .rss_registry_loader import RSSRegistryEntry, RSSRegistryLoader

        return {
            "RSSRegistryLoader": RSSRegistryLoader,
            "RSSRegistryEntry": RSSRegistryEntry,
        }[name]
    if name == "HTMLCollector":
        from .html_collector import HTMLCollector

        return HTMLCollector
    if name in {"HTMLRegistryLoader", "HTMLRegistryEntry"}:
        from .html_registry_loader import HTMLRegistryEntry, HTMLRegistryLoader

        return {
            "HTMLRegistryLoader": HTMLRegistryLoader,
            "HTMLRegistryEntry": HTMLRegistryEntry,
        }[name]
    if name == "APICollector":
        from .api_collector import APICollector

        return APICollector
    if name in {"SeriesRegistryLoader", "SeriesRegistryEntry"}:
        from .series_registry_loader import SeriesRegistryEntry, SeriesRegistryLoader

        return {
            "SeriesRegistryLoader": SeriesRegistryLoader,
            "SeriesRegistryEntry": SeriesRegistryEntry,
        }[name]
    raise AttributeError(name)
