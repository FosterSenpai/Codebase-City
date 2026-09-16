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
            references = {
                item.reference.module: item.reference for item in analysis.imports
            }
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

    def test_resolves_later_file_and_preserves_unresolved_imports(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.py").write_text(
                "import z\nimport missing_dependency\n",
                encoding="utf-8",
            )
            (root / "z.py").touch()

            analysis = analyse_python_repository(root)

            files = {
                entity.location.path: entity
                for entity in analysis.entities
                if entity.entity_type == EntityType.FILE
            }

            # Keep both matched and unmatched import references.
            self.assertEqual(len(analysis.imports), 2)
            imports = {item.reference.module: item for item in analysis.imports}
            self.assertEqual(set(imports), {"z", "missing_dependency"})

            # Resolve a target discovered after the importing file.
            self.assertEqual(imports["z"].target_file_id, files["z.py"].id)

            # Unmatched imports remain present without an invented destination.
            self.assertIsNone(imports["missing_dependency"].target_file_id)

            # Both references retain their actual source file.
            for item in analysis.imports:
                self.assertEqual(item.reference.source_file_id, files["a.py"].id)

            # Original import evidence survives resolution.
            self.assertEqual(
                imports["z"].reference.location,
                SourceLocation("a.py", 1, 1),
            )
            self.assertEqual(
                imports["missing_dependency"].reference.location,
                SourceLocation("a.py", 2, 2),
            )

    def test_reports_import_cycles_using_file_entity_ids(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.py").write_text("import b\n", encoding="utf-8")
            (root / "b.py").write_text("import a\n", encoding="utf-8")
            (root / "observer.py").write_text("import a\n", encoding="utf-8")

            analysis = analyse_python_repository(root)
            files = {
                entity.location.path: entity
                for entity in analysis.entities
                if entity.entity_type == EntityType.FILE
            }

            # The mutually importing files should form one circular group.
            self.assertEqual(
                analysis.import_cycles,
                [sorted([files["a.py"].id, files["b.py"].id])],
            )

            # A file importing into the cycle should not become part of it.
            cycle_members = {
                file_id for group in analysis.import_cycles for file_id in group
            }
            self.assertNotIn(files["observer.py"].id, cycle_members)

    def test_unchanged_repository_produces_identical_analysis(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package").mkdir()
            (root / "package/first.py").write_text(
                "from .second import Second\n\ndef run():\n    pass\n",
                encoding="utf-8",
            )
            (root / "package/second.py").write_text(
                "from .first import run\n"
                "\n"
                "class Second:\n"
                "    def execute(self):\n"
                "        pass\n",
                encoding="utf-8",
            )

            first = analyse_python_repository(root)
            second = analyse_python_repository(root)

            # Unchanged input should reproduce entities, IDs, references,
            # connections, and circular groups in the same order.
            self.assertEqual(first, second)

    def test_collects_metrics_for_every_file(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "empty.py").touch()
            (root / "example.py").write_text(
                "# Comment\n\nvalue = 1\n",
                encoding="utf-8",
            )

            analysis = analyse_python_repository(root)
            files = {
                entity.location.path: entity
                for entity in analysis.entities
                if entity.entity_type == EntityType.FILE
            }

            # Every file should receive exactly one measurement record.
            self.assertEqual(len(analysis.file_metrics), 2)
            self.assertEqual(
                {metric.file_id: metric.line_count for metric in analysis.file_metrics},
                {
                    files["empty.py"].id: 0,
                    files["example.py"].id: 3,
                },
            )

    def test_empty_repository_has_no_file_metrics(self):
        with TemporaryDirectory() as directory:
            analysis = analyse_python_repository(Path(directory))

            # No files should produce an empty metrics list without errors.
            self.assertEqual(analysis.file_metrics, [])


if __name__ == "__main__":
    root = Path("C:/dev/repos/PythonTranslator")
    analysis = analyse_python_repository(root)
    entities = analysis.entities
    entities_by_id = {entity.id: entity for entity in entities}

    def print_heading(title):
        print("\n" + "=" * 80)
        print(title)
        print("=" * 80)

    def format_import(reference):
        # Reconstruct one declaration from its recorded evidence.
        if reference.imported_name is None:
            declaration = f"import {reference.module}"
        else:
            module = "." * reference.level + (reference.module or "")
            declaration = f"from {module} import {reference.imported_name}"

        if reference.alias is not None:
            declaration += f" as {reference.alias}"

        return declaration

    def connection_sort_key(connection):
        return (
            entities_by_id[connection.importer_file_id].location.path,
            entities_by_id[connection.imported_file_id].location.path,
        )

    print_heading("REPOSITORY ANALYSIS")
    print(f"Repository:   {root}")
    print(f"Entities:     {len(entities)}")
    print(f"Imports:      {len(analysis.imports)}")
    print(f"Connections:  {len(analysis.connections)}")
    print(f"Cycle groups: {len(analysis.import_cycles)}")

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

    print_heading("ENTITY HIERARCHY")
    print_children(None)

    if not entities:
        print("No supported Python files found.")

    # Sort import results using their original source locations.
    sorted_imports = sorted(
        analysis.imports,
        key=lambda item: (
            item.reference.location.path,
            item.reference.location.start_line or 0,
        ),
    )

    resolved_count = sum(item.target_file_id is not None for item in sorted_imports)
    unresolved_count = len(sorted_imports) - resolved_count

    print_heading("IMPORT RESOLUTION")
    print(f"Resolved:   {resolved_count}")
    print(f"Unresolved: {unresolved_count}")

    current_file_id = None

    for item in sorted_imports:
        reference = item.reference

        # Group imports beneath their source file.
        if reference.source_file_id != current_file_id:
            current_file_id = reference.source_file_id
            print(f"\n[FILE] {reference.location.path}")
            print(f"  Entity ID: {current_file_id}")
            print("-" * 80)

        status = "RESOLVED" if item.target_file_id is not None else "UNRESOLVED"
        print(f"  [{status}] {format_import(reference)}")

        # Unresolved does not necessarily mean external.
        if item.target_file_id is not None:
            target = entities_by_id[item.target_file_id]
            print(f"    Target file:    {target.location.path}")
            print(f"    Target ID:      {target.id}")
        else:
            print("    Target file:    No unambiguous local match")

        print(
            f"    Source lines:   {reference.location.start_line}"
            f"–{reference.location.end_line}"
        )
        print(f"    Module:         {reference.module!r}")
        print(f"    Imported name:  {reference.imported_name!r}")
        print(f"    Alias:          {reference.alias!r}")
        print(f"    Relative level: {reference.level}")
        print()

    if not sorted_imports:
        print("No import references found.")

    sorted_connections = sorted(
        analysis.connections,
        key=connection_sort_key,
    )

    print_heading("FILE CONNECTIONS — IMPORTER -> IMPORTED FILE")
    print("Arrows below mean 'imports'; city roads will use the opposite direction.")

    for connection in sorted_connections:
        importer = entities_by_id[connection.importer_file_id]
        imported = entities_by_id[connection.imported_file_id]

        print(f"\n{importer.location.path} -> {imported.location.path}")
        print(f"  File IDs: {importer.id} -> {imported.id}")
        print(f"  Supporting references: {len(connection.references)}")

        # Preserve every declaration supporting this connection.
        for reference in connection.references:
            print(
                f"    Lines {reference.location.start_line}"
                f"–{reference.location.end_line}: "
                f"{format_import(reference)}"
            )

    if not sorted_connections:
        print("No resolved file connections found.")

    print_heading("CIRCULAR IMPORT GROUPS")

    for number, group in enumerate(analysis.import_cycles, start=1):
        member_ids = set(group)
        print(f"\nGroup {number}: {len(group)} file(s)")

        # Group members are mutually reachable, not necessarily a direct cycle route.
        for file_id in sorted(
            group,
            key=lambda item: entities_by_id[item].location.path,
        ):
            entity = entities_by_id[file_id]
            print(f"  [ID {file_id}] {entity.location.path}")

        print("  Connections within this group:")

        # Print actual connections between the group's members.
        for connection in sorted_connections:
            if (
                connection.importer_file_id in member_ids
                and connection.imported_file_id in member_ids
            ):
                importer = entities_by_id[connection.importer_file_id]
                imported = entities_by_id[connection.imported_file_id]
                print(f"    {importer.location.path} -> {imported.location.path}")

    if not analysis.import_cycles:
        print("No circular import groups found in the resolved connections.")

    print("\n" + "=" * 80)
