import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.python_analyser import parse_python_file


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
