from dataclasses import dataclass

from src.import_references import ImportReference, ResolvedImport


@dataclass
class FileConnection:
    importer_file_id: int
    imported_file_id: int
    references: list[ImportReference]


def build_file_connections(imports: list[ResolvedImport]) -> list[FileConnection]:
    connections: dict[tuple[int, int], FileConnection] = {}

    for item in imports:
        if item.target_file_id is None:
            continue

        # Group by importer and imported file ids
        key = (item.reference.source_file_id, item.target_file_id)

        if key not in connections:
            connections[key] = FileConnection(
                importer_file_id=key[0], imported_file_id=key[1], references=[]
            )

        connections[key].references.append(item.reference)

    return [connections[key] for key in sorted(connections)]
