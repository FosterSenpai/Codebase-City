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
