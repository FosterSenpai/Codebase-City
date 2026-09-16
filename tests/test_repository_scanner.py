import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.repository_scanner import discover_python_files


class RepositoryScannerTests(unittest.TestCase):
    def test_discovers_python_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)

            # Temp setup
            (root / "zebra.py").touch()
            (root / "notes.txt").touch()
            (root / "package").mkdir()
            (root / "package/helper.py").touch()

            discovered = discover_python_files(root)
            self.assertEqual(discovered, [Path("package/helper.py"), Path("zebra.py")])

    def test_exclusions(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)

            # Temp setup
            (root / "zebra.py").touch()
            (root / "notes.txt").touch()
            (root / "package").mkdir()
            (root / "package/helper.py").touch()

            # Stuff that should be skipped
            for name in (".git", "__pycache__", ".venv", "venv", "env"):
                excluded_directory = root / name
                excluded_directory.mkdir()
                (excluded_directory / "hidden.py").touch()

            discovered = discover_python_files(root)
            self.assertEqual(discovered, [Path("package/helper.py"), Path("zebra.py")])

    def test_empty_directory_returns_empty_list(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)

            discovered = discover_python_files(root)
            self.assertEqual(discovered, [])

    def test_excludes_nested_directories(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)

            # Temp setup
            (root / "package").mkdir()
            (root / "package/keep.py").touch()
            (root / "package/.venv").mkdir()
            (root / "package/.venv/hidden.py").touch()

            discovered = discover_python_files(root)
            self.assertEqual(discovered, [Path("package/keep.py")])
