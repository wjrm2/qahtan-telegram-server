import ast
from pathlib import Path

source = Path(__file__).with_name("service_catalog.py").read_text(encoding="utf-8")
tree = ast.parse(source)
groups_node = next(node for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_GROUPS" for t in node.targets))
groups = ast.literal_eval(groups_node.value)
services = [name for names in groups.values() for name in names.split(",")]
assert len(services) == 140, len(services)
assert len(groups) == 14, len(groups)
assert len(set(services)) == len(services), "duplicate service name"
for index in range(1, len(services) + 1):
    assert len(f"svc:{index:03d}".encode("utf-8")) <= 64
for category in groups:
    assert len(f"svc_cat:{category}".encode("utf-8")) <= 64
    assert len(f"svc_page:9:{category}".encode("utf-8")) <= 64
print(f"catalog_ok services={len(services)} categories={len(groups)} callbacks_ok=true")
