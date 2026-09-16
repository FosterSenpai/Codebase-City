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

            analysis = analyse_python_repository(root)
            result = analysis.entities

            # Extract two files, one folder, and three symbols.
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

            analysis = analyse_python_repository(root)
            result = analysis.entities

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

    def test_collects_imports_with_correct_source_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "first.py").write_text("import os\n", encoding="utf-8")
            (root / "second.py").write_text(
                "from pathlib import Path\n", encoding="utf-8"
            )

            analysis = analyse_python_repository(root)

            # Both files should contribute an import reference.
            self.assertEqual(len(analysis.imports), 2)
            references = {reference.module: reference for reference in analysis.imports}
            self.assertEqual(set(references), {"os", "pathlib"})

            files = {
                entity.location.path: entity
                for entity in analysis.entities
                if entity.entity_type == EntityType.FILE
            }

            # Each import should reference the entity for its containing file.
            self.assertEqual(references["os"].source_file_id, files["first.py"].id)
            self.assertEqual(
                references["pathlib"].source_file_id, files["second.py"].id
            )

            # Preserve ordinary and from-import details through repository analysis.
            self.assertIsNone(references["os"].imported_name)
            self.assertEqual(references["pathlib"].imported_name, "Path")

            # Import locations should remain relative to the repository root.
            self.assertEqual(
                references["os"].location, SourceLocation("first.py", 1, 1)
            )
            self.assertEqual(
                references["pathlib"].location,
                SourceLocation("second.py", 1, 1),
            )


if __name__ == "__main__":
    root = Path("C:/dev/repos/PythonTranslator")
    analysis = analyse_python_repository(root)
    entities = analysis.entities

    print("\n" + "=" * 80)
    print("REPOSITORY ANALYSIS")
    print("=" * 80)
    print(f"Repository: {root}")
    print(f"Entities:   {len(entities)}")
    print(f"Imports:    {len(analysis.imports)}")

    # Summarize each supported entity category.
    print("\nEntity counts:")
    for kind in EntityType:
        count = sum(entity.entity_type == kind for entity in entities)
        print(f"  {kind.value:<10} {count}")

    # Group entities by parent to display their containment hierarchy.
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
            parent = (
                str(entity.parent_id)
                if entity.parent_id is not None
                else "None (repository root)"
            )

            print(f"{indent}[{entity.entity_type.value.upper()}] {entity.name}")
            print(f"{indent}  ID: {entity.id} | Parent: {parent}")
            print(f"{indent}  Path: {location.path} | Lines: {lines}")
            print()

            print_children(entity.id, depth + 1)

    print("\n" + "=" * 80)
    print("ENTITY HIERARCHY")
    print("=" * 80)

    print_children(None)

    if not entities:
        print("No supported Python files found.")

    # Sort import references by file and source line.
    sorted_imports = sorted(
        analysis.imports,
        key=lambda reference: (
            reference.location.path,
            reference.location.start_line or 0,
        ),
    )

    print("\n" + "=" * 80)
    print("IMPORT REFERENCES — DESTINATIONS NOT YET RESOLVED")
    print("=" * 80)

    current_file_id = None

    for reference in sorted_imports:
        # Print a heading when moving to a different source file.
        if reference.source_file_id != current_file_id:
            current_file_id = reference.source_file_id
            print(f"\n[FILE] {reference.location.path}")
            print(f"  Entity ID: {current_file_id}")
            print("-" * 80)

        # Reconstruct a readable declaration for each individual reference.
        if reference.imported_name is None:
            declaration = f"import {reference.module}"
        else:
            module = "." * reference.level + (reference.module or "")
            declaration = f"from {module} import {reference.imported_name}"

        if reference.alias is not None:
            declaration += f" as {reference.alias}"

        print(f"  {declaration}")
        print(
            f"    Lines:         {reference.location.start_line}"
            f"–{reference.location.end_line}"
        )
        print(f"    Module:        {reference.module!r}")
        print(f"    Imported name: {reference.imported_name!r}")
        print(f"    Alias:         {reference.alias!r}")
        print(f"    Relative level: {reference.level}")
        print()

    if not sorted_imports:
        print("No import references found.")

    print("=" * 80)
