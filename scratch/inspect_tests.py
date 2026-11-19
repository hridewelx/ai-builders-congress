import ast
from pathlib import Path

test_files = sorted(Path("tests").glob("test_*.py"))
for tf in test_files:
    print(f"\nFILE: {tf.name}")
    code = tf.read_text(encoding="utf-8")
    tree = ast.parse(code)
    doc = ast.get_docstring(tree)
    if doc:
        print(f"  Module Doc: {doc.strip().splitlines()[0]}")
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            fn_doc = ast.get_docstring(node)
            fn_summary = fn_doc.strip().splitlines()[0] if fn_doc else "Asserts expected behavior"
            print(f"  - {node.name}: {fn_summary}")

