import unittest

from src.code_entities import CodeEntity, EntityType, SourceLocation
from src.import_resolver import build_module_index


class ModuleIndexTests(unittest.TestCase):
    def test_indexes_modules_and_packages(self):
        entities = [
            CodeEntity(
                id=1,
                name="main.py",
                entity_type=EntityType.FILE,
                location=SourceLocation("main.py"),
            ),
            CodeEntity(
                id=2,
                name="helpers.py",
                entity_type=EntityType.FILE,
                location=SourceLocation("package/helpers.py"),
            ),
            CodeEntity(
                id=3,
                name="__init__.py",
                entity_type=EntityType.FILE,
                location=SourceLocation("package/__init__.py"),
            ),
        ]

        result = build_module_index(entities)

        # Convert file paths into dotted names and packages into directory names.
        self.assertEqual(
            result,
            {"main": 1, "package.helpers": 2, "package": 3},
        )

    def test_ignores_non_file_entities(self):
        entities = [
            CodeEntity(
                id=index,
                name="example",
                entity_type=kind,
                location=SourceLocation("example.py"),
            )
            for index, kind in enumerate(
                (
                    EntityType.FOLDER,
                    EntityType.CLASS,
                    EntityType.FUNCTION,
                    EntityType.METHOD,
                ),
                start=1,
            )
        ]

        # Folders and symbols should not become importable file entries.
        self.assertEqual(build_module_index(entities), {})

    def test_skips_root_package_without_module_name(self):
        entities = [
            CodeEntity(
                id=1,
                name="__init__.py",
                entity_type=EntityType.FILE,
                location=SourceLocation("__init__.py"),
            ),
        ]

        # A root-level package has no name under the current import-root convention.
        self.assertEqual(build_module_index(entities), {})

    def test_rejects_duplicate_module_names(self):
        entities = [
            CodeEntity(
                id=1,
                name="package.py",
                entity_type=EntityType.FILE,
                location=SourceLocation("package.py"),
            ),
            CodeEntity(
                id=2,
                name="__init__.py",
                entity_type=EntityType.FILE,
                location=SourceLocation("package/__init__.py"),
            ),
        ]

        # Reject ambiguous mappings instead of silently overwriting an entry.
        with self.assertRaises(ValueError) as caught:
            build_module_index(entities)

        # Identify the module name responsible for the collision.
        self.assertIn("package", str(caught.exception))

    def test_empty_entities_produce_empty_index(self):
        # An empty repository should produce an empty lookup.
        self.assertEqual(build_module_index([]), {})
