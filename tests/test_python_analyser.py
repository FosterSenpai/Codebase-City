import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.code_entities import EntityType, SourceLocation
from src.entity_ids import EntityIdAllocator
from src.python_analyser import extract_top_level_functions, parse_python_file


class PythonAnalyserTests(unittest.TestCase):
    def test_parses_tree_assignment_from_python_file(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "temp.py"
            source_path.write_text("answer = 42\n", encoding="utf-8")

            result = parse_python_file(root, Path("temp.py"))
            self.assertIsInstance(result, ast.Module)
            self.assertEqual(len(result.body), 1)
            self.assertIsInstance(result.body[0], ast.Assign)

    def test_syntax_error_identifies_source_file(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "broken.py"
            source_path.write_text("def broken('\n", encoding="utf-8")

            with self.assertRaises(SyntaxError) as caught:
                parse_python_file(root, Path("broken.py"))

            self.assertEqual(caught.exception.filename, "broken.py")

    def test_does_not_execute_source(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "temp.py"
            source_path.write_text(
                "raise RuntimeError('This source must not execute')", encoding="utf-8"
            )

            result = parse_python_file(root, Path("temp.py"))
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

        self.assertEqual(len(functions), 1)  # Only one found

        function = functions[0]
        self.assertEqual(function.name, "greet")
        self.assertEqual(function.entity_type, EntityType.FUNCTION)
        self.assertEqual(function.parent_id, parent_file_id)
        self.assertEqual(function.location, SourceLocation("example.py", 1, 2))
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

        self.assertEqual([function.name for function in functions], ["outer", "fetch"])
