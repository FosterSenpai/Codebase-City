import unittest

from src.code_entities import CodeEntity, EntityType, SourceLocation
from src.import_references import ImportReference
from src.import_resolver import build_module_index, resolve_import_target


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

    def test_resolves_exact_module_with_or_without_alias(self):
        for alias in (None, "helpers"):
            with self.subTest(alias=alias):
                reference = ImportReference(
                    source_file_id=1,
                    module="package.helpers",
                    imported_name=None,
                    alias=alias,
                    level=0,
                    location=SourceLocation("main.py", 1, 1),
                )

                result = resolve_import_target(reference, {"package.helpers": 7})

                # Aliases should not change the destination module's file ID.
                self.assertEqual(result, 7)

    def test_unmatched_module_does_not_fall_back_to_parent(self):
        reference = ImportReference(
            source_file_id=1,
            module="package.missing",
            imported_name=None,
            alias=None,
            level=0,
            location=SourceLocation("main.py", 1, 1),
        )

        # A matching parent package is not a match for the requested module.
        self.assertIsNone(resolve_import_target(reference, {"package": 7}))

    def test_unsupported_import_forms_remain_unresolved(self):
        cases = [
            ("package", None, 1),
            (None, None, 0),
        ]

        for module, imported_name, level in cases:
            with self.subTest(module=module, imported_name=imported_name, level=level):
                reference = ImportReference(
                    source_file_id=1,
                    module=module,
                    imported_name=imported_name,
                    alias=None,
                    level=level,
                    location=SourceLocation("main.py", 1, 1),
                )

                # Forms outside the current resolver's scope return None.
                self.assertIsNone(resolve_import_target(reference, {"package": 7}))

    def test_resolves_absolute_from_import_candidates(self):
        cases = [
            ("module only", {"package": 7}, 7),
            ("submodule only", {"package.helpers": 8}, 8),
            ("both candidates", {"package": 7, "package.helpers": 8}, None),
            ("neither candidate", {}, None),
        ]

        for label, module_index, expected in cases:
            with self.subTest(case=label):
                reference = ImportReference(
                    source_file_id=1,
                    module="package",
                    imported_name="helpers",
                    alias="tools",
                    level=0,
                    location=SourceLocation("main.py", 1, 1),
                )

                result = resolve_import_target(reference, module_index)

                # Resolve a single candidate; leave ambiguous or missing targets unresolved.
                self.assertEqual(result, expected)

    def test_wildcard_import_targets_module_only(self):
        reference = ImportReference(
            source_file_id=1,
            module="package",
            imported_name="*",
            alias=None,
            level=0,
            location=SourceLocation("main.py", 1, 1),
        )

        # A wildcard should resolve to the module itself.
        self.assertEqual(
            resolve_import_target(reference, {"package": 7}),
            7,
        )

        # A fabricated submodule named "*" must not be considered a target.
        self.assertIsNone(resolve_import_target(reference, {"package.*": 8}))

    def test_resolves_relative_imports_from_containing_package(self):
        cases = [
            (
                "current package",
                "package/services/worker.py",
                "helpers",
                "clean",
                1,
                "package.services.helpers",
            ),
            (
                "parent package",
                "package/services/worker.py",
                "shared",
                "settings",
                2,
                "package.shared",
            ),
            (
                "unnamed module",
                "package/services/worker.py",
                None,
                "helpers",
                1,
                "package.services.helpers",
            ),
            (
                "package initializer",
                "package/services/__init__.py",
                "helpers",
                "clean",
                1,
                "package.services.helpers",
            ),
            (
                "wildcard",
                "package/services/worker.py",
                "helpers",
                "*",
                1,
                "package.services.helpers",
            ),
        ]

        for label, path, module, name, level, target in cases:
            with self.subTest(case=label):
                reference = ImportReference(
                    source_file_id=1,
                    module=module,
                    imported_name=name,
                    alias=None,
                    level=level,
                    location=SourceLocation(path, 1, 1),
                )

                # Resolve relative imports using the source file's package context.
                self.assertEqual(
                    resolve_import_target(reference, {target: 7}),
                    7,
                )

    def test_relative_imports_cannot_escape_package_hierarchy(self):
        cases = [
            ("root file", "main.py", 1),
            ("beyond top package", "package/worker.py", 2),
            ("beyond nested package", "package/services/worker.py", 3),
        ]

        for label, path, level in cases:
            with self.subTest(case=label):
                reference = ImportReference(
                    source_file_id=1,
                    module="helpers",
                    imported_name="clean",
                    alias=None,
                    level=level,
                    location=SourceLocation(path, 1, 1),
                )

                # Invalid relative levels must not fall back to an absolute module.
                self.assertIsNone(resolve_import_target(reference, {"helpers": 7}))

    def test_relative_import_with_two_candidates_remains_unresolved(self):
        reference = ImportReference(
            source_file_id=1,
            module=None,
            imported_name="helpers",
            alias=None,
            level=1,
            location=SourceLocation("package/worker.py", 1, 1),
        )

        # Preserve the ambiguity rule after converting a relative module name.
        self.assertIsNone(
            resolve_import_target(
                reference,
                {"package": 7, "package.helpers": 8},
            )
        )
