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

    # Parse files
    for relative_path in discovered_files:
        location = SourceLocation(path=relative_path.as_posix())
        file_entity = CodeEntity(
            id=allocator.allocate(),
            name=relative_path.name,
            entity_type=EntityType.FILE,
            location=location,
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
