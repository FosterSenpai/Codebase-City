from dataclasses import dataclass

from src.code_entities import CodeEntity
from src.file_connections import FileConnection
from src.import_references import ResolvedImport


@dataclass
class RepositoryAnalysis:
    entities: list[CodeEntity]
    imports: list[ResolvedImport]
    connections: list[FileConnection]
    import_cycles: list[list[int]]
