# Reads python source coude and extracts code entities
import ast
import tokenize
from pathlib import Path

from src.code_entities import CodeEntity, EntityType, SourceLocation
from src.entity_ids import EntityIdAllocator


def parse_python_file(root: Path, relative_path: Path) -> ast.Module:
    with tokenize.open(root / relative_path) as source_file:
        source = source_file.read()

    return ast.parse(source, filename=relative_path.as_posix())


def extract_top_level_functions(
    tree: ast.Module, relative_path: Path, file_id: int, allocator: EntityIdAllocator
) -> list[CodeEntity]:
    """Extracts top level ordinary and async functions, nested functions and methods are excluded"""

    entities = []

    # Iterating source files tree structure for functions
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            location = SourceLocation(
                path=relative_path.as_posix(),
                start_line=node.lineno,
                end_line=node.end_lineno,
            )
            entity = CodeEntity(
                id=allocator.allocate(),
                name=node.name,
                entity_type=EntityType.FUNCTION,
                location=location,
                parent_id=file_id,
            )
            entities.append(entity)

    return entities


def extract_classes_and_methods(
    tree: ast.Module, relative_path: Path, file_id: int, allocator: EntityIdAllocator
) -> list[CodeEntity]:
    entities = []

    # Iterating source files tree structure for classes
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            # Extracting classes
            class_location = SourceLocation(
                path=relative_path.as_posix(),
                start_line=node.lineno,
                end_line=node.end_lineno,
            )
            class_entity = CodeEntity(
                id=allocator.allocate(),
                name=node.name,
                entity_type=EntityType.CLASS,
                location=class_location,
                parent_id=file_id,
            )
            entities.append(class_entity)

            # Extracting methods
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_location = SourceLocation(
                        path=relative_path.as_posix(),
                        start_line=child.lineno,
                        end_line=child.end_lineno,
                    )
                    method_entity = CodeEntity(
                        id=allocator.allocate(),
                        name=child.name,
                        entity_type=EntityType.METHOD,
                        location=method_location,
                        parent_id=class_entity.id,
                    )

                    entities.append(method_entity)

    return entities


if __name__ == "__main__":
    root = Path("C:/dev/repos/PythonTranslator")
    relative_path = Path("src/speech_handler.py")

    allocator = EntityIdAllocator()
    file_id = allocator.allocate()

    tree = parse_python_file(root, relative_path)

    functions = extract_top_level_functions(tree, relative_path, file_id, allocator)
    classes_and_methods = extract_classes_and_methods(
        tree, relative_path, file_id, allocator
    )

    # Display entities in source order, placing missing line ranges last.
    entities = sorted(
        functions + classes_and_methods,
        key=lambda entity: (
            entity.location.start_line is None,
            entity.location.start_line or 0,
        ),
    )

    # Count classes and methods separately within the combined results.
    class_count = sum(
        entity.entity_type == EntityType.CLASS for entity in classes_and_methods
    )
    method_count = sum(
        entity.entity_type == EntityType.METHOD for entity in classes_and_methods
    )

    print(f"\nFile: {relative_path.as_posix()}")
    print(f"File ID: {file_id}")
    print(
        f"Extracted: {len(functions)} functions, "
        f"{class_count} classes, {method_count} methods"
    )
    print("-" * 72)

    for entity in entities:
        print(f"{entity.entity_type.value.upper()}: {entity.name}")
        print(f"  ID:        {entity.id}")
        print(f"  Parent ID: {entity.parent_id}")
        print(f"  Path:      {entity.location.path}")
        print(f"  Lines:     {entity.location.start_line}–{entity.location.end_line}")
        print()

    if not entities:
        print("No functions, classes, or methods found.")
