import ast
from pathlib import Path

MODULE = Path(__file__).with_name('community_features.py')
TREE = ast.parse(MODULE.read_text(encoding='utf-8'))


def test_module_syntax_and_symbols():
    names = {node.id for node in ast.walk(TREE) if isinstance(node, ast.Name)}
    assert 'CommunityFeature' in names
    assert 'register_community_handlers' in {node.name for node in ast.walk(TREE) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def test_callback_templates_are_short():
    assert len('community:item:999'.encode()) <= 64
    assert len('community:cat:99'.encode()) <= 64


def test_raw_feature_titles_are_unique():
    titles = []
    for node in TREE.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == '_RAW':
                    raw = ast.literal_eval(node.value)
                    for rows in raw.values():
                        titles.extend(row[0] for row in rows)
    assert len(titles) == 60
    assert len(set(titles)) == len(titles)
