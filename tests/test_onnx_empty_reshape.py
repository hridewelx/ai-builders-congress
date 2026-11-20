"""Model-free guard for the clean-frame fix in ``ml.export_onnx.allow_empty_reshape``.

The clean-frame tests in ``test_detector_onnx.py`` need the 76 MB model, so CI skips them and
nothing protects the fix there. These tests rebuild the one pattern that failed in the exported
Faster R-CNN, a Reshape whose target shape is computed at run time as ``[rows, -1]`` and receives
a zero-row tensor, using a few ONNX nodes. They run in CI in under a second.

Needs ``onnx`` and ``onnxruntime``; the file skips itself when either is missing, so CI
never depends on a 76 MB artifact to protect this fix.
"""
from __future__ import annotations

import numpy as np
import pytest

onnx = pytest.importorskip("onnx")
ort = pytest.importorskip("onnxruntime")

from onnx import TensorProto as T
from onnx import helper

from ml.export_onnx import allow_empty_reshape


def _rows_then_infer_graph(trailing: list[int]) -> onnx.ModelProto:
    """x[N, 20] -> Reshape(x, [N, *trailing]) with N read from x at run time, like torchvision's box decode."""
    nodes = [
        helper.make_node("Shape", ["x"], ["shape"]),
        helper.make_node("Gather", ["shape", "zero"], ["rows"], axis=0),
        helper.make_node("Unsqueeze", ["rows", "axes0"], ["rows1"]),
        helper.make_node("Concat", ["rows1", "tail"], ["target"], axis=0),
        helper.make_node("Reshape", ["x", "target"], ["y"]),
    ]
    inits = [
        helper.make_tensor("zero", T.INT64, [], [0]),
        helper.make_tensor("axes0", T.INT64, [1], [0]),
        helper.make_tensor("tail", T.INT64, [len(trailing)], trailing),
    ]
    graph = helper.make_graph(
        nodes, "rows_then_infer",
        [helper.make_tensor_value_info("x", T.FLOAT, ["N", 20])],
        [helper.make_tensor_value_info("y", T.FLOAT, None)], initializer=inits)
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 9
    return model


def _session(path):
    options = ort.SessionOptions()
    options.log_severity_level = 4
    return ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])


@pytest.fixture()
def paths(tmp_path):
    model = _rows_then_infer_graph([-1])  # the failing pattern: [rows, -1]
    original = tmp_path / "original.onnx"
    patched = tmp_path / "patched.onnx"
    onnx.save(model, str(original))
    onnx.save(model, str(patched))
    return original, patched


def test_unpatched_graph_really_fails_on_zero_rows(paths):
    """If this stops failing, the fix is no longer needed and the premise of the patch is gone."""
    original, _ = paths
    with pytest.raises(Exception, match="cannot be reshaped"):
        _session(original).run(None, {"x": np.zeros((0, 20), np.float32)})


def test_patch_makes_a_zero_row_tensor_a_normal_result(paths):
    _, patched = paths
    assert allow_empty_reshape(patched) == 1
    out = _session(patched).run(None, {"x": np.zeros((0, 20), np.float32)})[0]
    assert out.shape == (0, 20)


def test_patch_does_not_change_non_empty_results(paths):
    original, patched = paths
    allow_empty_reshape(patched)
    x = np.random.default_rng(0).random((7, 20), dtype=np.float32)
    before = _session(original).run(None, {"x": x})[0]
    after = _session(patched).run(None, {"x": x})[0]
    assert np.array_equal(before, after)


def test_patch_is_idempotent(paths):
    _, patched = paths
    assert allow_empty_reshape(patched) == 1
    assert allow_empty_reshape(patched) == 0


def test_a_literal_zero_in_a_constant_shape_is_the_hazard():
    """allowzero=1 changes what a literal 0 means ("copy this dimension" -> "an empty dimension").

    Combined with -1 that is ambiguous, and ONNX Runtime refuses to load the graph. The real graph
    has no such Reshape, which ``constant_zero_reshapes`` below checks on every re-export.
    """
    shape = helper.make_tensor("s", T.INT64, [2], [0, -1])
    node = helper.make_node("Reshape", ["x", "s"], ["y"], allowzero=1)
    graph = helper.make_graph([node], "g", [helper.make_tensor_value_info("x", T.FLOAT, ["N", 20])],
                              [helper.make_tensor_value_info("y", T.FLOAT, None)], initializer=[shape])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 9
    with pytest.raises(Exception, match="(?i)product cannot be 0|invalid target shape"):
        ort.InferenceSession(model.SerializeToString(), providers=["CPUExecutionProvider"])


def constant_zero_reshapes(model) -> list[str]:
    """Names of Reshape nodes whose *constant* target shape contains a literal 0."""
    from onnx import numpy_helper

    constants = {i.name: numpy_helper.to_array(i) for i in model.graph.initializer}
    for node in model.graph.node:
        if node.op_type == "Constant":
            for attr in node.attribute:
                if attr.name == "value":
                    constants[node.output[0]] = numpy_helper.to_array(attr.t)
    return [node.name or node.output[0] for node in model.graph.node
            if node.op_type == "Reshape" and node.input[1] in constants
            and (constants[node.input[1]] == 0).any()]


def test_helper_finds_a_constant_zero_shape():
    shape = helper.make_tensor("s", T.INT64, [2], [0, -1])
    node = helper.make_node("Reshape", ["x", "s"], ["y"], name="flatten_like")
    graph = helper.make_graph([node], "g", [helper.make_tensor_value_info("x", T.FLOAT, None)],
                              [helper.make_tensor_value_info("y", T.FLOAT, None)], initializer=[shape])
    assert constant_zero_reshapes(helper.make_model(graph)) == ["flatten_like"]


def test_shipped_detector_graph_has_no_constant_zero_reshape():
    """Run against the real export when it is present; skipped in CI where data/ is absent."""
    from pathlib import Path

    path = Path("data/models/det_v2.onnx")
    if not path.exists():
        pytest.skip("no ONNX artifact in this checkout")
    assert constant_zero_reshapes(onnx.load(str(path), load_external_data=False)) == []
