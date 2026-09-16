import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.code_entities import EntityType, SourceLocation
from src.entity_ids import EntityIdAllocator
from src.python_analyser import (
    extract_classes_and_methods,
    extract_top_level_functions,
    parse_python_file,
)


class PythonAnalyserTests(unittest.TestCase):
    def test_parses_tree_assignment_from_python_file(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "temp.py"
            source_path.write_text("answer = 42\n", encoding="utf-8")

            result = parse_python_file(root, Path("temp.py"))

            # Parsing should return a module containing one top-level assignment.
            self.assertIsInstance(result, ast.Module)
            self.assertEqual(len(result.body), 1)
            self.assertIsInstance(result.body[0], ast.Assign)

    def test_syntax_error_identifies_source_file(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "broken.py"
            source_path.write_text("def broken('\n", encoding="utf-8")

            # Invalid Python syntax should raise a SyntaxError.
            with self.assertRaises(SyntaxError) as caught:
                parse_python_file(root, Path("broken.py"))

            # The error should identify the file containing the invalid syntax.
            self.assertEqual(caught.exception.filename, "broken.py")

    def test_does_not_execute_source(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "temp.py"
            source_path.write_text(
                "raise RuntimeError('This source must not execute')", encoding="utf-8"
            )

            result = parse_python_file(root, Path("temp.py"))

            # The raise statement should be represented in the tree without being executed.
            self.assertEqual(len(result.body), 1)  # Check only contains one statement
            self.assertIsInstance(
                result.body[0], ast.Raise
            )  # Contains raise node if only parsed

    def test_extracts_top_level_function_entity(self):
        tree = ast.parse("def greet():\n   return 'hello'\n")
        allocator = EntityIdAllocator()

        parent_file_id = allocator.allocate()

        functions = extract_top_level_functions(
            tree, Path("example.py"), parent_file_id, allocator
        )

        # Exactly one function should be extracted.
        self.assertEqual(len(functions), 1)
        function = functions[0]

        # The entity should preserve the function name and identify it as a function.
        self.assertEqual(function.name, "greet")
        self.assertEqual(function.entity_type, EntityType.FUNCTION)

        # The function should belong to the containing file.
        self.assertEqual(function.parent_id, parent_file_id)

        # The source location should identify the file and inclusive function line range.
        self.assertEqual(function.location, SourceLocation("example.py", 1, 2))

        # The function should have an ID distinct from its containing file.
        self.assertNotEqual(function.id, parent_file_id)

    def test_extracts_only_top_level_functions_in_source_order(self):
        tree = ast.parse(
            "def outer():\n"
            "    def nested():\n"
            "        pass\n"
            "\n"
            "class Example:\n"
            "    def method(self):\n"
            "        pass\n"
            "\n"
            "async def fetch():\n"
            "    pass\n"
        )

        allocator = EntityIdAllocator()
        parent_file_id = allocator.allocate()
        functions = extract_top_level_functions(
            tree, Path("example.py"), parent_file_id, allocator
        )

        # Include ordinary and async top-level functions in source order,
        # excluding nested functions and class methods.
        self.assertEqual([function.name for function in functions], ["outer", "fetch"])


def test_extracts_classes_and_methods_with_correct_parents(self):
    tree = ast.parse(
        "class First:\n"
        "    def run(self):\n"
        "        pass\n"
        "\n"
        "class Second:\n"
        "    async def run(self):\n"
        "        pass\n"
    )
    allocator = EntityIdAllocator()
    file_id = allocator.allocate()
    result = extract_classes_and_methods(tree, Path("example.py"), file_id, allocator)

    # Both classes and their methods should be extracted in source order.
    self.assertEqual(len(result), 4)
    self.assertEqual(
        [entity.name for entity in result],
        ["First", "run", "Second", "run"],
    )
    first_class, first_method, second_class, second_method = result

    # Ordinary and async methods should both be identified as methods.
    self.assertEqual(
        [entity.entity_type for entity in result],
        [
            EntityType.CLASS,
            EntityType.METHOD,
            EntityType.CLASS,
            EntityType.METHOD,
        ],
    )

    # Both classes should belong to the containing file.
    self.assertEqual(first_class.parent_id, file_id)
    self.assertEqual(second_class.parent_id, file_id)

    # Each same-named method should belong to its own class.
    self.assertEqual(first_method.parent_id, first_class.id)
    self.assertEqual(second_method.parent_id, second_class.id)

    # Every extracted entity should have a unique ID distinct from the file ID.
    entity_ids = [entity.id for entity in result]
    self.assertEqual(len(set(entity_ids)), 4)
    self.assertNotIn(file_id, entity_ids)

    # Class source ranges should include their method definitions.
    self.assertEqual(first_class.location, SourceLocation("example.py", 1, 3))
    self.assertEqual(second_class.location, SourceLocation("example.py", 5, 7))

    # Each method should retain its own inclusive source line range.
    self.assertEqual(first_method.location, SourceLocation("example.py", 2, 3))
    self.assertEqual(second_method.location, SourceLocation("example.py", 6, 7))


def test_excludes_nested_definitions_from_direct_methods(self):
    tree = ast.parse(
        "class Outer:\n"
        "    def run(self):\n"
        "        def helper():\n"
        "            pass\n"
        "\n"
        "    class Nested:\n"
        "        def inner_method(self):\n"
        "            pass\n"
    )
    allocator = EntityIdAllocator()
    file_id = allocator.allocate()
    result = extract_classes_and_methods(tree, Path("example.py"), file_id, allocator)

    # Extract only the top-level class and its direct method.
    self.assertEqual(
        [entity.name for entity in result],
        ["Outer", "run"],
    )
    self.assertEqual(
        [entity.entity_type for entity in result],
        [EntityType.CLASS, EntityType.METHOD],
    )

    # The direct method should belong to Outer, not the file.
    self.assertEqual(result[1].parent_id, result[0].id)
