"""CPU evaluation of the real timber graphs against the frozen Blender source.

Run: python3 -B -m unittest scripts/unreal/test_timber_uv_roundtrip.py

Asymmetric, repeating test images make wrong row selection observable. These
tests model FBX's (U, 1-V) conversion and image sampling, not GPU filtering or
saved mesh UVs. No Unreal/Blender module or asset-write code is executed.
"""
import ast
import math
from pathlib import Path
from types import SimpleNamespace
import unittest

import scripts.unreal.test_dojo_timber_admission as fixtures


def vector_op(a, b, operation):
    if isinstance(a, tuple) or isinstance(b, tuple):
        size = len(a) if isinstance(a, tuple) else len(b)
        a = a if isinstance(a, tuple) else (a,) * size
        b = b if isinstance(b, tuple) else (b,) * size
        return tuple(operation(x, y) for x, y in zip(a, b))
    return operation(a, b)


def image_sample(name, uv, blender=False, nearest=False):
    """Top-down file rows; Blender's image UV has its origin at the bottom."""
    width, height, offset = {"Fibre": (11, 9, 3), "RingNoise": (7, 5, 13),
                             "RingRandom": (8, 6, 29)}[name]
    u, v = uv[:2]
    if blender:
        v = 1.0 - v

    def pixel(x, y):
        x, y = x % width, y % height
        return tuple(((x * 17 + y * 31 + x * y * 7 + offset + c * 43) % 251) / 250.0 for c in range(3))

    if nearest:
        return pixel(math.floor(u * width), math.floor(v * height))
    x, y = u * width - 0.5, v * height - 0.5
    ix, iy = math.floor(x), math.floor(y)
    tx, ty = x - ix, y - iy
    return tuple((1 - ty) * ((1 - tx) * a + tx * b) + ty * ((1 - tx) * c + tx * d)
                 for a, b, c, d in zip(pixel(ix, iy), pixel(ix + 1, iy), pixel(ix, iy + 1), pixel(ix + 1, iy + 1)))


def evaluate(node, imported_uvs, parameters):
    """Evaluate only the actual UE graph operations feeding ring/LUT samples."""
    def value(pin=""):
        return evaluate(node.inputs[pin][0], imported_uvs, parameters)

    kind = node.kind.removeprefix("MaterialExpression")
    if kind == "TextureCoordinate":
        return imported_uvs[node.props["coordinate_index"]]
    if kind == "Constant":
        return node.props["r"]
    if kind == "ScalarParameter":
        return parameters.get(node.props["parameter_name"], node.props["default_value"])
    if kind == "ComponentMask":
        selected = tuple(v for channel, v in zip("rgba", value()) if node.props[channel])
        return selected[0] if len(selected) == 1 else selected
    if kind == "AppendVector":
        a, b = value("A"), value("B")
        return (a if isinstance(a, tuple) else (a,)) + (b if isinstance(b, tuple) else (b,))
    if kind == "OneMinus":
        return vector_op(1.0, value(), lambda a, b: a - b)
    binary = {"Add": lambda a, b: a + b, "Subtract": lambda a, b: a - b,
              "Multiply": lambda a, b: a * b, "Divide": lambda a, b: a / b}
    if kind in binary:
        return vector_op(value("A"), value("B") if "B" in node.inputs else node.props["const_b"], binary[kind])
    if kind == "Length":
        return math.sqrt(sum(v * v for v in value()))
    if kind == "Frac":
        return value() - math.floor(value())
    if kind == "Floor":
        return math.floor(value())
    if kind == "TextureSample":
        name = node.props["texture"].kind
        return image_sample(name, value("UVs"), nearest=name == "RingRandom")
    raise AssertionError(f"Unmodelled graph operation: {kind}")


class BlenderMath:
    """Numeric adapter for the unmodified Blender material's ring expressions."""
    def __init__(self, uvs):
        self.uvs = uvs

    def uv(self, name):
        return (*self.uvs[{"UV0": 0, "UVLogQ": 2, "UVLogZ": 3}[name]], 0.0)

    def node(self, name, operation):
        assert (name, operation) == ("ShaderNodeVectorMath", "LENGTH")
        result = SimpleNamespace(outputs={})
        result.inputs = [result]
        return result

    def link(self, value, target):
        target.outputs["Value"] = math.sqrt(sum(v * v for v in value))

    vxyz = sep = staticmethod(lambda v: v)
    xyz = staticmethod(lambda x, y, z: (x, y, z))
    add = staticmethod(lambda a, b: a + b)
    sub = staticmethod(lambda a, b: a - b)
    mul = staticmethod(lambda a, b: a * b)
    div = staticmethod(lambda a, b: a / b)
    vmul = staticmethod(lambda v, k: tuple(x * k for x in v))
    m = staticmethod(lambda op, v: v - math.floor(v) if op == "FRACT" else math.floor(v))

    @staticmethod
    def smoothstep(value, lo, hi):
        t = max(0.0, min(1.0, (value - lo) / (hi - lo)))
        return t * t * (3.0 - 2.0 * t)


def blender_reference(source_uvs, ring_width):
    # Execute the real, frozen source through its year lookup. Avoid copying
    # the phase formula/constants into the test as a second implementation.
    path = Path(__file__).resolve().parents[1] / "art/sora_timber_lookdev.py"
    method = next(n for n in ast.parse(path.read_text()).body
                  if isinstance(n, ast.FunctionDef) and n.name == "timber_material")
    prefix = []
    for statement in method.body:
        prefix.append(statement)
        if isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "year" for t in statement.targets):
            break
    else:
        raise AssertionError("Blender source no longer has the expected year lookup")
    ns = {"name": "reference", "preset": "test", "PRESETS": {"test": {"ring_width": ring_width, "latewood": 0.24}},
          "L": SimpleNamespace(NB=lambda name: BlenderMath(source_uvs)),
          "shared": {k: k for k in ("Fibre", "RingNoise", "RingRandom")},
          "_tex": lambda nb, name, uv, closest=False: SimpleNamespace(
              outputs={"Color": image_sample(name, uv, blender=True, nearest=closest)})}
    exec(compile(ast.Module(body=prefix, type_ignores=[]), str(path), "exec"), ns)
    return ns


class TimberUVRoundtrip(unittest.TestCase):
    def graph(self, fallback):
        ns, shared, _, nodes, _, _ = fixtures.TimberMaterialInputs().graph()
        ns["timber_master"]("M_SoraTimber", shared, fallback)
        return nodes

    def contexts(self):
        # Metric coordinates exceed [0,1]; signed pith offsets and wrap seams
        # must survive. Use multiple per-log widths, not only the default.
        for uv0, q, seed, width in (
                ((0.137, 1.375), (-0.074, 0.121), 0.173, 0.0019),
                ((-0.423, 6.811), (0.103, -0.058), 0.913, 0.0014),
                ((1.0003, -0.002), (-0.001, -0.203), 0.001, 0.0024),
                ((-1.25, 2.75), (0.0, 0.0), 0.0, 0.0017)):
            source = {0: uv0, 1: (0.137, 0.847), 2: q, 3: (6.2, seed)}
            imported = {i: (u, 1.0 - v) for i, (u, v) in source.items()}
            yield source, imported, {"RingWidth": width}

    def test_baseline_phase_and_texture_values_match_frozen_blender_source(self):
        for fallback in (False, True):
            nodes = self.graph(fallback)
            phase = next(n.inputs[""][0] for n in nodes if n.kind == "MaterialExpressionFloor")
            samples = [n for n in nodes if n.kind == "MaterialExpressionTextureSample"]
            for source, imported, parameters in self.contexts():
                with self.subTest(fallback=fallback, source=source):
                    reference = blender_reference(source, parameters["RingWidth"])
                    self.assertAlmostEqual(evaluate(phase, imported, parameters), reference["phase"], places=9)
                    fibre = [n for n in samples if n.props["texture"].kind == "Fibre"]
                    for a, b in zip(evaluate(fibre[0], imported, parameters), reference["fibre"].outputs["Color"]):
                        self.assertAlmostEqual(a, b, places=11)
                    self.assertAlmostEqual(evaluate(fibre[1], imported, parameters)[2], reference["drift"], places=11)
                    year = next(n for n in samples if n.props["texture"].kind == "RingRandom")
                    self.assertAlmostEqual(evaluate(year, imported, parameters)[0], reference["year"], places=11)

    def test_signed_log_offsets_and_seed_are_data_not_wrapped_texture_uvs(self):
        nodes = self.graph(False)
        radius = next(n for n in nodes if n.kind == "MaterialExpressionLength")
        for source, imported, parameters in self.contexts():
            q = evaluate(radius.inputs[""][0], imported, parameters)
            for a, b in zip(q, source[2]):
                self.assertAlmostEqual(a, b, places=14)

    def test_fibre_metric_scaling_precedes_image_coordinate_conversion(self):
        nodes = self.graph(False)
        fibre = [n for n in nodes if n.props.get("texture") and n.props["texture"].kind == "Fibre"]
        for source, imported, parameters in self.contexts():
            for tile in (0.25, 0.37):
                parameters["FibreTileMeters"] = tile
                for node, scale in zip(fibre, (1.0 / tile, 0.11)):
                    actual = evaluate(node.inputs["UVs"][0], imported, parameters)
                    expected = (source[0][0] * scale, 1.0 - source[0][1] * scale)
                    for a, b in zip(actual, expected):
                        self.assertAlmostEqual(a, b, places=13)

    def test_baked_uv1_masks_and_normals_keep_the_imported_coordinate(self):
        nodes = self.graph(True)
        samples = {n.props.get("parameter_name"): n for n in nodes
                   if n.kind == "MaterialExpressionTextureSampleParameter2D"}
        self.assertEqual(set(samples), {"MasksMap", "NormalMap"})
        for _, imported, parameters in self.contexts():
            for node in samples.values():
                self.assertEqual(evaluate(node.inputs["UVs"][0], imported, parameters), imported[1])


if __name__ == "__main__":
    unittest.main()
