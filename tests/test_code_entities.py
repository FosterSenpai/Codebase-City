import unittest

from src.code_entities import CodeEntity, EntityType, SourceLocation


class CodeEntityTests(unittest.TestCase):
    def test_entity_without_parent(self) -> None:
        src_loc = SourceLocation("tests/test_code_entities.py")
        file = CodeEntity(1, "test_code_entities.py", EntityType.FILE, src_loc)

        self.assertIsNone(file.parent_id)
        self.assertEqual(file.id, 1)
        self.assertEqual(file.name, "test_code_entities.py")
        self.assertEqual(file.entity_type, EntityType.FILE)
        self.assertEqual(file.location, src_loc)

    def test_entity_with_parent(self) -> None:
        folder_loc = SourceLocation(r"tests")
        folder = CodeEntity(2, "tests_directory", EntityType.FOLDER, folder_loc)
        file_loc = SourceLocation("tests/test_code_entities.py")
        file = CodeEntity(
            1, "test_code_entities.py", EntityType.FILE, file_loc, folder.id
        )

        self.assertEqual(file.parent_id, folder.id)
        self.assertEqual(file.id, 1)
        self.assertEqual(file.name, "test_code_entities.py")
        self.assertEqual(file.entity_type, EntityType.FILE)
        self.assertEqual(file.location, file_loc)

    def test_entity_hierarchy(self) -> None:
        file = CodeEntity(
            id=1,
            name="example.py",
            entity_type=EntityType.FILE,
            location=SourceLocation("example.py"),
        )

        first_class = CodeEntity(
            id=2,
            name="FirstClass",
            entity_type=EntityType.CLASS,
            location=SourceLocation("example.py", 3, 10),
            parent_id=file.id,
        )
        second_class = CodeEntity(
            id=4,
            name="SecondClass",
            entity_type=EntityType.CLASS,
            location=SourceLocation("example.py", 12, 20),
            parent_id=file.id,
        )

        first_method = CodeEntity(
            id=3,
            name="run",
            entity_type=EntityType.METHOD,
            location=SourceLocation("example.py", 5, 7),
            parent_id=first_class.id,
        )
        second_method = CodeEntity(
            id=5,
            name="run",
            entity_type=EntityType.METHOD,
            location=SourceLocation("example.py", 14, 16),
            parent_id=second_class.id,
        )

        self.assertEqual(first_class.parent_id, file.id)
        self.assertEqual(second_class.parent_id, file.id)
        self.assertEqual(first_method.parent_id, first_class.id)
        self.assertEqual(second_method.parent_id, second_class.id)

        self.assertEqual(first_method.name, second_method.name)
        self.assertNotEqual(first_method.id, second_method.id)


class SourceLocationTests(unittest.TestCase):
    def test_line_numbers_default_to_none(self) -> None:
        location = SourceLocation("tests/test_code_entities.py")

        self.assertEqual(location.path, "tests/test_code_entities.py")
        self.assertIsNone(location.start_line)
        self.assertIsNone(location.end_line)

    def test_info_is_preserved(self) -> None:
        location = SourceLocation("tests/test_code_entities.py", 12, 40)

        self.assertEqual(location.path, "tests/test_code_entities.py")
        self.assertEqual(location.start_line, 12)
        self.assertEqual(location.end_line, 40)
