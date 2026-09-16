from dataclasses import dataclass

from src.code_entities import CodeEntity
from src.import_references import ImportReference


@dataclass
class RepositoryAnalysis:
    entities: list[CodeEntity]
    imports: list[ImportReference]
