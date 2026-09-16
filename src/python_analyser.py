# Reads python source coude and extracts code entities
import ast
import tokenize
from pathlib import Path

from src.code_entities import CodeEntity, EntityType, SourceLocation
from src.entity_ids import EntityIdAllocator
from src.import_references import ImportReference


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


def extract_imports(
    tree: ast.Module,
    relative_path: Path,
    file_id: int,
) -> list[ImportReference]:
    imports = []

    for node in ast.walk(tree):
        # Normal imports
        if isinstance(node, ast.Import):
            location = SourceLocation(
                path=relative_path.as_posix(),
                start_line=node.lineno,
                end_line=node.end_lineno,
            )
            for imported in node.names:
                import_reference = ImportReference(
                    source_file_id=file_id,
                    module=imported.name,
                    imported_name=None,
                    alias=imported.asname,
                    level=0,
                    location=location,
                )
                imports.append(import_reference)

        # Import from
        elif isinstance(node, ast.ImportFrom):
            location = SourceLocation(
                path=relative_path.as_posix(),
                start_line=node.lineno,
                end_line=node.end_lineno,
            )
            for imported in node.names:
                import_reference = ImportReference(
                    source_file_id=file_id,
                    module=node.module,
                    imported_name=imported.name,
                    alias=imported.asname,
                    level=node.level,
                    location=location,
                )
                imports.append(import_reference)

    return imports
