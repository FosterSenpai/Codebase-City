import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.code_entities import EntityType, SourceLocation
from src.entity_ids import EntityIdAllocator
from src.python_analyser import (
    extract_top_level_classes,
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

    def test_extracts_top_level_class_entity(self):
        tree = ast.parse("class Greeter:\n    pass\n")
        allocator = EntityIdAllocator()
        file_id = allocator.allocate()
        result = extract_top_level_classes(tree, Path("example.py"), file_id, allocator)

        # Exactly one class should be extracted.
        self.assertEqual(len(result), 1)
        entity = result[0]

        # The entity should preserve the class name and identify it as a class.
        self.assertEqual(entity.name, "Greeter")
        self.assertEqual(entity.entity_type, EntityType.CLASS)

        # The class should belong to the file and have its own distinct ID.
        self.assertEqual(entity.parent_id, file_id)
        self.assertNotEqual(entity.id, file_id)

        # The source location should identify the file and inclusive class line range.
        self.assertEqual(entity.location, SourceLocation("example.py", 1, 2))
