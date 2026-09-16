import unittest

from src.code_entities import SourceLocation
from src.file_connections import build_file_connections
from src.import_references import ImportReference, ResolvedImport


class FileConnectionTests(unittest.TestCase):
    def test_groups_imports_and_preserves_original_references(self):
        first = ImportReference(
            source_file_id=1,
            module="helpers",
            imported_name="clean",
            alias=None,
            level=0,
            location=SourceLocation("main.py", 1, 1),
        )
        second = ImportReference(
            source_file_id=1,
            module="helpers",
            imported_name="format",
            alias="format_text",
            level=0,
            location=SourceLocation("main.py", 2, 2),
        )

        result = build_file_connections(
            [
                ResolvedImport(first, 2),
                ResolvedImport(second, 2),
            ]
        )

        # Multiple imports between the same files should form one connection.
        self.assertEqual(len(result), 1)
        connection = result[0]
        self.assertEqual(connection.importer_file_id, 1)
        self.assertEqual(connection.imported_file_id, 2)

        # Preserve all original evidence in input order.
        self.assertEqual(connection.references, [first, second])

    def test_sorts_connections_and_preserves_reverse_and_self_connections(self):
        imports = []
        for source_id, target_id in [(2, 1), (1, 2), (1, 1)]:
            reference = ImportReference(
                source_file_id=source_id,
                module=f"module_{target_id}",
                imported_name=None,
                alias=None,
                level=0,
                location=SourceLocation(f"module_{source_id}.py", 1, 1),
            )
            imports.append(ResolvedImport(reference, target_id))

        result = build_file_connections(imports)

        # Reverse directions and self-imports remain distinct, sorted connections.
        self.assertEqual(
            [
                (connection.importer_file_id, connection.imported_file_id)
                for connection in result
            ],
            [(1, 1), (1, 2), (2, 1)],
        )

        # Each connection should retain evidence for its own source and target.
        expected_references = {
            (item.reference.source_file_id, item.target_file_id): item.reference
            for item in imports
        }
        for connection in result:
            key = (
                connection.importer_file_id,
                connection.imported_file_id,
            )
            self.assertEqual(connection.references, [expected_references[key]])

    def test_skips_unresolved_imports_without_losing_resolved_ones(self):
        reference = ImportReference(
            source_file_id=1,
            module="helpers",
            imported_name=None,
            alias=None,
            level=0,
            location=SourceLocation("main.py", 1, 1),
        )

        result = build_file_connections(
            [
                ResolvedImport(reference, None),
                ResolvedImport(reference, 2),
            ]
        )

        # Only the resolved import should contribute a connection and evidence.
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].importer_file_id, 1)
        self.assertEqual(result[0].imported_file_id, 2)
        self.assertEqual(result[0].references, [reference])

        # Entirely unresolved input should produce no connections.
        self.assertEqual(
            build_file_connections([ResolvedImport(reference, None)]),
            [],
        )

    def test_empty_imports_produce_no_connections(self):
        # Empty input should produce an empty result.
        self.assertEqual(build_file_connections([]), [])
