# Discovers files and applies exlusions
import os
from pathlib import Path


def discover_python_files(
    root: Path, excluded_dirs: set[str] | None = None
) -> list[Path]:
    if not root.exists():
        raise FileNotFoundError(root)
    if not root.is_dir():
        raise NotADirectoryError(root)

    # Exclusions
    exclusions = {".git", "__pycache__", ".venv", "venv", "env"}
    if excluded_dirs:
        exclusions.update(excluded_dirs)

    # Discovery
    discovered_files = []
    for file_root, dirnames, files in os.walk(root):
        dirnames[:] = [
            name for name in dirnames if name not in exclusions
        ]  # Skip exlusions

        for filename in files:
            if filename.endswith(".py"):
                full_path = Path(file_root) / filename
                relative_path = full_path.relative_to(root)
                discovered_files.append(relative_path)

    # Sorted alpha on path string
    return sorted(discovered_files, key=lambda path: path.as_posix())
