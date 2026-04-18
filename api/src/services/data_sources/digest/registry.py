"""Registry mapping DataSourceType values to digest extractor classes."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseDigestExtractor

# Lazy-loaded to avoid circular imports at module load time.
# Add new extractors here — that's the only change needed to support a new source type.
_EXTRACTOR_MAP: dict[str, str] = {
    "SLACK": "src.services.data_sources.digest.slack_extractor.SlackDigestExtractor",
    "GMAIL": "src.services.data_sources.digest.gmail_extractor.GmailDigestExtractor",
    "GITHUB": "src.services.data_sources.digest.github_extractor.GithubDigestExtractor",
}


def get_extractor(source_type: str) -> "BaseDigestExtractor | None":
    """
    Return an instantiated extractor for the given source type, or None if unsupported.

    Args:
        source_type: DataSourceType value (e.g. "SLACK", "GMAIL").
    """
    import importlib

    dotted = _EXTRACTOR_MAP.get(source_type.upper())
    if not dotted:
        return None

    module_path, class_name = dotted.rsplit(".", 1)
    mod = importlib.import_module(module_path)
    cls = getattr(mod, class_name)
    return cls()


def supported_source_types() -> list[str]:
    """Return all source types that have a registered extractor."""
    return list(_EXTRACTOR_MAP.keys())
