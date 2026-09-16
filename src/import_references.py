from dataclasses import dataclass

from src.code_entities import SourceLocation


@dataclass
class ImportReference:
    """Record an import declaration before resolving its destination."""

    source_file_id: int
    module: str | None
    imported_name: str | None
    alias: str | None
    level: int
    location: SourceLocation
