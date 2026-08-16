import ast
import py_compile
import unittest
from pathlib import Path

ROOT = Path(__file__).parent
MODULE = ROOT / 'community_features.py'

class CommunityChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse(MODULE.read_text(encoding='utf-8'))

    def test_syntax_and_registration(self):
        py_compile.compile(str(MODULE), doraise=True)
        py_compile.compile(str(ROOT / 'bot.py'), doraise=True)
        functions = {node.name for node in ast.walk(self.tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertIn('register_community_handlers', functions)

    def test_callback_sizes(self):
        self.assertLessEqual(len('community:item:999'.encode()), 64)
        self.assertLessEqual(len('community:cat:99'.encode()), 64)

    def test_unique_feature_titles(self):
        titles = []
        for node in self.tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == '_RAW':
                        raw = ast.literal_eval(node.value)
                        for rows in raw.values():
                            titles.extend(row[0] for row in rows)
        self.assertEqual(len(titles), 60)
        self.assertEqual(len(titles), len(set(titles)))

if __name__ == '__main__':
    unittest.main(verbosity=2)
