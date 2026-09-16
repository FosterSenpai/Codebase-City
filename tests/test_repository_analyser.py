import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.code_entities import EntityType, SourceLocation
from src.repository_analyser import analyse_python_repository


class RepositoryAnalyserTests(unittest.TestCase):
    def test_analyses_multiple_files_with_correct_parents(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "first.py").write_text(
                "def greet():\n    pass\n",
                encoding="utf-8",
            )
            (root / "package").mkdir()
            (root / "package/second.py").write_text(
                "class Greeter:\n    def greet(self):\n        pass\n",
                encoding="utf-8",
            )

            result = analyse_python_repository(root)

            # Extract both files and all three declared symbols.
            self.assertEqual(len(result), 5)
            files = [
                entity for entity in result if entity.entity_type == EntityType.FILE
            ]
            self.assertEqual(
                [entity.location.path for entity in files],
                ["first.py", "package/second.py"],
            )
            first_file, second_file = files

            # File names should exclude their directory paths.
            self.assertEqual(first_file.name, "first.py")
            self.assertEqual(second_file.name, "second.py")

            # Extract one function, one class, and one method.
            symbols = {}
            for kind in (
                EntityType.FUNCTION,
                EntityType.CLASS,
                EntityType.METHOD,
            ):
                matches = [entity for entity in result if entity.entity_type == kind]
                self.assertEqual(len(matches), 1)
                symbols[kind] = matches[0]

            function = symbols[EntityType.FUNCTION]
            class_entity = symbols[EntityType.CLASS]
            method = symbols[EntityType.METHOD]

            # Preserve symbol names, including names shared across files.
            self.assertEqual(function.name, "greet")
            self.assertEqual(class_entity.name, "Greeter")
            self.assertEqual(method.name, "greet")

            # Symbols should reference their actual containing file or class.
            self.assertEqual(function.parent_id, first_file.id)
            self.assertEqual(class_entity.parent_id, second_file.id)
            self.assertEqual(method.parent_id, class_entity.id)

            # All entities should receive unique IDs across both files.
            self.assertEqual(len({entity.id for entity in result}), len(result))

            # Preserve repository-relative source paths and symbol line ranges.
            self.assertEqual(function.location, SourceLocation("first.py", 1, 2))
            self.assertEqual(
                class_entity.location,
                SourceLocation("package/second.py", 1, 3),
            )
            self.assertEqual(
                method.location,
                SourceLocation("package/second.py", 2, 3),
            )
