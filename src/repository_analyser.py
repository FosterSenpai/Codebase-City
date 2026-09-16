from pathlib import Path

from src.code_entities import CodeEntity, EntityType, SourceLocation
from src.entity_ids import EntityIdAllocator
from src.python_analyser import (
    extract_classes_and_methods,
    extract_top_level_functions,
    parse_python_file,
)
from src.repository_scanner import discover_python_files


def analyse_python_repository(root: Path) -> list[CodeEntity]:
    allocator = EntityIdAllocator()
    discovered_files = discover_python_files(root)
    entities = []
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
        tree = parse_python_file(root, relative_path)
        entities.extend(
            extract_top_level_functions(tree, relative_path, file_entity.id, allocator)
        )
        entities.extend(
            extract_classes_and_methods(tree, relative_path, file_entity.id, allocator)
        )

    return entities


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
