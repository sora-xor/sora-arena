"""Strict offline goods/count entries shared by importer and data qualification."""

FIELDS = {"item_ja", "item_en", "qty", "unit_ja", "unit_en"}


def validate_registry(registry, beat_type, params, ext):
    has_mode = "registry_mode" in ext
    if has_mode and ext["registry_mode"] != "record_only":
        raise ValueError("registry_mode must be record_only when present")
    if registry is None:
        if has_mode:
            raise ValueError("registry_mode requires a goods entry")
        return
    if beat_type != "production_task" and not (beat_type == "horseback_ride" and params.get("mode") == "cargo"):
        raise ValueError("only production tasks and cargo rides write the registry")
    if not isinstance(registry, dict) or set(registry) != FIELDS:
        raise ValueError("registry takes item_ja, item_en, qty, unit_ja and unit_en")
    for key in FIELDS - {"qty"}:
        if not isinstance(registry[key], str) or not registry[key].strip():
            raise ValueError(f"registry {key} needs non-empty text")
    if type(registry["qty"]) is not int or not 0 < registry["qty"] <= 2**31 - 1:
        raise ValueError("registry quantity must be a positive 32-bit integer")
