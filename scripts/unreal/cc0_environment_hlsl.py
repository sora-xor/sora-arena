"""The Custom HLSL nodes of the CC0 environment masters, with their signatures.

``import_cc0_environment.py`` builds each Custom expression from a ``CUSTOM``
entry and wires exactly the declared inputs, in order. The input types are the
types UE 5.8 gives the wired pins: ``lwc3`` is a large-world position, which the
translator passes as a demoted ``float3`` plus its ``FWSVector3``.
``translator_function`` writes the function the 5.8 material translator
(``FHLSLMaterialTranslator::CustomExpression``) generates for a node, so
``check_cc0_custom_hlsl.py`` can compile the same code on the host.
"""

from __future__ import annotations

from dataclasses import dataclass

# Dominant-axis planar projection of the world position in centimetres: one
# texture fetch per map, oriented so text/grain reads upright on walls.
HLSL_PROJECT = """
float3 a = abs(N);
if (a.z >= a.x && a.z >= a.y) return float2(P.x, -P.y);
if (a.x >= a.y) return float2((N.x >= 0.0 ? -1.0 : 1.0) * P.y, -P.z);
return float2((N.y >= 0.0 ? 1.0 : -1.0) * P.x, -P.z);
"""

# The DirectX tangent-space normal in the same projection frame, re-orthogonalised
# against the geometric normal so slopes keep their shading. +R is +U, +G is +V.
HLSL_PROJECTED_NORMAL = """
float3 g = normalize(N);
float3 a = abs(g);
float3 tu = float3(1.0, 0.0, 0.0);
float3 tv = float3(0.0, -1.0, 0.0);
if (!(a.z >= a.x && a.z >= a.y)) {
    tv = float3(0.0, 0.0, -1.0);
    if (a.x >= a.y) tu = float3(0.0, g.x >= 0.0 ? -1.0 : 1.0, 0.0);
    else tu = float3(g.y >= 0.0 ? 1.0 : -1.0, 0.0, 0.0);
}
tu = normalize(tu - g * dot(g, tu));
tv = normalize(tv - g * dot(g, tv));
return normalize(NormalTS.x * tu + NormalTS.y * tv + NormalTS.z * g);
"""

HLSL_DETAIL = """
return normalize(float3(Base.xy + Detail.xy * Strength, Base.z));
"""

# Height blend of layer B over layer A: the ARM occlusion of A is the height
# proxy (crevices first when HeightFromCrevices is 1), vertex red paints coverage.
HLSL_BLEND = """
float coverage = saturate(Coverage * lerp(1.0, VertexR, VertexColorBlend) + TopFacingBias * saturate(Nz));
float h = lerp(ArmA.r, 1.0 - ArmA.r, HeightFromCrevices);
float alpha = saturate((h + 2.0 * coverage - 1.5) * Contrast + 0.5);
float roughA = lerp(RoughMinA, RoughMaxA, ArmA.g);
float roughB = lerp(RoughMinB, RoughMaxB, ArmB.g);
NormalOut = normalize(lerp(NormalA, NormalB, alpha));
ArmOut = float3(lerp(ArmA.r, ArmB.r, alpha), lerp(roughA, roughB, alpha), lerp(ArmA.b, ArmB.b, alpha));
return lerp(ColorA, ColorB * TintB, alpha);
"""

# Grading, macro variation and the shared rain response. Wet surfaces darken by
# WetDarkening and lose roughness toward WetRoughness (story bible 15.1: wet
# timber 0.2-0.35, albedo -25-35%); puddles gather on flat, low, macro-dark
# ground when PuddleAmount rises.
HLSL_FINISH = """
float lum = dot(Albedo, float3(0.2126, 0.7152, 0.0722));
float3 albedo = lerp(Albedo, lum.xxx, Desaturation) * Tint;
float macro = saturate(0.5 * (MacroA + MacroB));
float signedMacro = macro * 2.0 - 1.0;
albedo *= 1.0 + MacroStrength * signedMacro;
float rough = saturate(lerp(RoughMin, RoughMax, Arm.g) * (1.0 + MacroRoughness * signedMacro));
float ao = lerp(1.0, Arm.r, AOStrength);
float metal = saturate(Arm.b * MetallicScale);
float3 n = float3(NormalTS.xy * NormalStrength, NormalTS.z);
float exposure = lerp(0.65, 1.0, saturate(Nz));
float wet = saturate(max(BaseWetness, Wetness * WetnessResponse)) * exposure;
float lowness = 0.5 * (1.0 - Arm.r) + 0.5 * (1.0 - macro);
float flatness = saturate((Nz - 0.85) * 6.67);
float puddle = saturate((PuddleAmount * PuddleResponse * 1.2 - (1.0 - lowness)) * 8.0) * flatness;
wet = max(wet, puddle);
albedo *= 1.0 - WetDarkening * wet;
rough = lerp(rough, min(rough, WetRoughness), wet);
rough = lerp(rough, 0.04, puddle);
metal *= 1.0 - puddle;
RoughnessOut = rough;
MetallicOut = metal;
AOOut = ao;
NormalOut = normalize(lerp(n, float3(0.0, 0.0, 1.0), puddle));
return max(albedo, 0.0);
"""

# Emissive washi: blackbody colour at unit luminance, fibre-thickness
# transmission and a per-object flicker phase.
HLSL_LANTERN = """
float3 colour = BlackBody / pow(0.0004 * TemperatureK, 4.0);
float transmission = lerp(TransmissionMax, TransmissionMin, saturate(Thickness));
float phase = dot(ObjectPosition, float3(0.0131, 0.0173, 0.0113));
float t = Time * FlickerSpeed;
float flicker = 1.0 + FlickerAmount * (0.6 * sin(t * 7.3 + phase) + 0.4 * sin(t * 13.1 + phase * 1.9));
return colour * Intensity * GlobalIntensity * transmission * flicker;
"""


@dataclass(frozen=True)
class Custom:
    description: str
    code: str
    output: str               # float1 | float2 | float3
    inputs: tuple             # ((name, type), ...) in pin order; type: float | float3 | lwc3
    outputs: tuple = ()       # additional outputs ((name, type), ...)


def _floats(*names):
    return tuple((name, "float") for name in names)


CUSTOM = {
    "project": Custom("SORA world projection (cm)", HLSL_PROJECT, "float2", (("P", "lwc3"), ("N", "float3"))),
    "projected_normal": Custom("SORA projected normal to world", HLSL_PROJECTED_NORMAL, "float3",
                               (("NormalTS", "float3"), ("N", "float3"))),
    "detail": Custom("SORA detail normal", HLSL_DETAIL, "float3",
                     (("Base", "float3"), ("Detail", "float3"), ("Strength", "float"))),
    "blend": Custom(
        "SORA height blend", HLSL_BLEND, "float3",
        (("ColorA", "float3"), ("NormalA", "float3"), ("ArmA", "float3"), ("ColorB", "float3"),
         ("NormalB", "float3"), ("ArmB", "float3"), ("VertexR", "float"), ("Nz", "float"))
        + _floats("Coverage", "VertexColorBlend", "TopFacingBias", "HeightFromCrevices", "Contrast")
        + (("TintB", "float3"),) + _floats("RoughMinA", "RoughMaxA", "RoughMinB", "RoughMaxB"),
        (("NormalOut", "float3"), ("ArmOut", "float3"))),
    "finish": Custom(
        "SORA environment finish", HLSL_FINISH, "float3",
        (("Albedo", "float3"), ("NormalTS", "float3"), ("Arm", "float3"), ("MacroA", "float"), ("MacroB", "float"),
         ("Nz", "float"), ("Tint", "float3"))
        + _floats("Desaturation", "RoughMin", "RoughMax", "AOStrength", "NormalStrength", "MetallicScale",
                  "MacroStrength", "MacroRoughness", "Wetness", "PuddleAmount", "WetnessResponse", "BaseWetness",
                  "WetDarkening", "WetRoughness", "PuddleResponse"),
        (("RoughnessOut", "float"), ("MetallicOut", "float"), ("AOOut", "float"), ("NormalOut", "float3"))),
    "lantern": Custom(
        "SORA lantern paper emission", HLSL_LANTERN, "float3",
        (("BlackBody", "float3"),) + _floats("TemperatureK", "Thickness", "TransmissionMin", "TransmissionMax")
        + (("ObjectPosition", "lwc3"),) + _floats("Time", "FlickerSpeed", "FlickerAmount", "Intensity",
                                                   "GlobalIntensity")),
}

# Translator spellings (HLSLMaterialTranslator.cpp, CustomExpression).
_MATERIAL_TYPE = {"float": "MaterialFloat", "float1": "MaterialFloat", "float2": "MaterialFloat2",
                  "float3": "MaterialFloat3", "float4": "MaterialFloat4"}


def translator_function(custom: Custom, index: int) -> str:
    """The pixel-shader function UE 5.8 generates for ``custom`` as its ``index``-th Custom expression."""
    declaration = ""
    for name, kind in custom.inputs:
        if kind == "lwc3":
            declaration += f",float3 {name}, FWSVector3 LWC{name}"
        else:
            declaration += f",{_MATERIAL_TYPE[kind]} {name}"
    for name, kind in custom.outputs:
        declaration += f", inout {_MATERIAL_TYPE[kind]} {name}"
    code = custom.code.strip()
    if "return" not in code:
        code = f"return {code};"
    return (f"{_MATERIAL_TYPE[custom.output]} CustomExpression{index}"
            f"(FMaterialPixelParameters Parameters{declaration})\n{{\n{code}\n}}\n")
