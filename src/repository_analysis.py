from dataclasses import dataclass

from src.code_entities import CodeEntity
from src.import_references import ResolvedImport


@dataclass
class RepositoryAnalysis:
    entities: list[CodeEntity]
    imports: list[ResolvedImport]
