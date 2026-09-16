# Discovers files and applies exlusions
import os
from pathlib import Path


def discover_python_files(root: Path) -> list[Path]:
    # Exclusions
    excluded_dirs = {".git", "__pycache__", ".venv", "venv", "env"}

    # Discovery
    discovered_files = []
    for file_root, dirnames, files in os.walk(root):
        dirnames[:] = [
            name for name in dirnames if name not in excluded_dirs
        ]  # Skip exlusions

        for filename in files:
            if filename.endswith(".py"):
                full_path = Path(file_root) / filename
                relative_path = full_path.relative_to(root)
                discovered_files.append(relative_path)

    # Sorted alpha on path string
    return sorted(discovered_files, key=lambda path: path.as_posix())
