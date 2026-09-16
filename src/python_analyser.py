# Reads python source coude and extracts code entities
import ast
import tokenize
from pathlib import Path


def parse_python_file(root: Path, relative_path: Path) -> ast.Module:
    with tokenize.open(root / relative_path) as source_file:
        source = source_file.read()

    return ast.parse(source, filename=relative_path.as_posix())
