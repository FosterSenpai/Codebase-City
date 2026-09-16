from pathlib import Path

from src.code_entities import CodeEntity, EntityType, SourceLocation
from src.entity_ids import EntityIdAllocator
from src.file_connections import build_file_connections
from src.file_metrics import FileMetrics
from src.import_cycles import find_import_cycles
from src.import_references import ResolvedImport
from src.import_resolver import build_module_index, resolve_import_target
from src.python_analyser import (
    extract_classes_and_methods,
    extract_imports,
    extract_top_level_functions,
    parse_python_file,
)
from src.repository_analysis import RepositoryAnalysis
from src.repository_scanner import discover_python_files


def analyse_python_repository(root: Path) -> RepositoryAnalysis:
    allocator = EntityIdAllocator()
    discovered_files = discover_python_files(root)
    entities = []
    imports = []
    file_metrics: list[FileMetrics] = []
    folder_ids: dict[Path, int] = {}  # Lookup for already stored folders

    # Parse files
    for relative_path in discovered_files:
        location = SourceLocation(path=relative_path.as_posix())
        parent_id = _get_or_create_folder_id(
            relative_path.parent, allocator, folder_ids, entities
        )
        file_entity = CodeEntity(
            id=allocator.allocate(),
            name=relative_path.name,
            entity_type=EntityType.FILE,
            location=location,
            parent_id=parent_id,
        )
        entities.append(file_entity)

        # Parsing file for functions, classes and methods
        tree, line_count = parse_python_file(root, relative_path)
        file_metrics.append(FileMetrics(file_id=file_entity.id, line_count=line_count))
        entities.extend(
            extract_top_level_functions(tree, relative_path, file_entity.id, allocator)
        )
        entities.extend(
            extract_classes_and_methods(tree, relative_path, file_entity.id, allocator)
        )
        imports.extend(extract_imports(tree, relative_path, file_entity.id))

    module_index = build_module_index(entities)

    # resolve each reference against module index
    resolved_imports = []
    for reference in imports:
        resolved_import = ResolvedImport(
            reference=reference,
            target_file_id=resolve_import_target(reference, module_index),
        )
        resolved_imports.append(resolved_import)

    # Import connections
    connections = build_file_connections(resolved_imports)
    import_cycles = find_import_cycles(connections)

    return RepositoryAnalysis(
        entities=entities,
        imports=resolved_imports,
        connections=connections,
        import_cycles=import_cycles,
        file_metrics=file_metrics,
    )


def _get_or_create_folder_id(
    folder_path: Path,
    allocator: EntityIdAllocator,
    folder_ids: dict[Path, int],
    entities: list[CodeEntity],
) -> int | None:
    # File at root level
    if folder_path == Path("."):
        return None

    # Reuse existing folders
    if folder_path in folder_ids:
        return folder_ids[folder_path]

    # Get parent folders ID recursively
    # Build outwards -> inwards
    parent_id = _get_or_create_folder_id(
        folder_path.parent, allocator, folder_ids, entities
    )

    folder_entity = CodeEntity(
        id=allocator.allocate(),
        name=folder_path.name,
        entity_type=EntityType.FOLDER,
        location=SourceLocation(folder_path.as_posix()),
        parent_id=parent_id,
    )

    # Update entities and created folder ids
    entities.append(folder_entity)
    folder_ids[folder_path] = folder_entity.id

    return folder_entity.id  # Caller uses as parent
