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
            self.assertEqual(len(result), 6)
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

    def test_creates_nested_folders_and_reuses_shared_parent(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package/services").mkdir(parents=True)
            (root / "package/services/first.py").touch()
            (root / "package/services/second.py").touch()

            result = analyse_python_repository(root)

            # Create two folders and two files, without duplicate folders.
            self.assertEqual(len(result), 4)
            folders = {
                entity.location.path: entity
                for entity in result
                if entity.entity_type == EntityType.FOLDER
            }
            self.assertEqual(set(folders), {"package", "package/services"})

            # The outer folder has no parent; the inner folder belongs to it.
            package = folders["package"]
            services = folders["package/services"]
            self.assertIsNone(package.parent_id)
            self.assertEqual(services.parent_id, package.id)

            # Folder locations preserve relative paths without source line ranges.
            self.assertEqual(package.location, SourceLocation("package"))
            self.assertEqual(services.location, SourceLocation("package/services"))

            # Both files should reuse the same immediate parent folder.
            files = [
                entity for entity in result if entity.entity_type == EntityType.FILE
            ]
            self.assertEqual(len(files), 2)
            for file_entity in files:
                self.assertEqual(file_entity.parent_id, services.id)

            # Folders and files should all have distinct IDs.
            self.assertEqual(len({entity.id for entity in result}), 4)


if __name__ == "__main__":
    root = Path("C:/dev/repos/PythonTranslator")
    entities = analyse_python_repository(root)

    print(f"\nRepository: {root}")
    print(f"Total entities: {len(entities)}")

    # Summarize each supported entity category.
    for kind in EntityType:
        count = sum(entity.entity_type == kind for entity in entities)
        print(f"  {kind.value}: {count}")

    print("\nHierarchy")
    print("=" * 80)

    # Group entities by parent so each appears beneath its container.
    children = {}
    for entity in entities:
        children.setdefault(entity.parent_id, []).append(entity)

    def print_children(parent_id, depth=0):
        siblings = sorted(
            children.get(parent_id, []),
            key=lambda entity: (
                entity.location.path,
                entity.location.start_line or 0,
                entity.id,
            ),
        )

        for entity in siblings:
            indent = "    " * depth
            location = entity.location
            lines = (
                f"{location.start_line}–{location.end_line}"
                if location.start_line is not None
                else "not applicable"
            )

            print(f"{indent}[{entity.entity_type.value.upper()}] {entity.name}")
            print(f"{indent}  ID: {entity.id} | Parent: {entity.parent_id}")
            print(f"{indent}  Path: {location.path} | Lines: {lines}")
            print()

            print_children(entity.id, depth + 1)

    print_children(None)

    if not entities:
        print("No supported Python files found.")
