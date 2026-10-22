import re
from typing import Dict, List, Optional, Any, Set, Tuple

# Mapping of units to (canonical_unit, multiplier_to_base, category)
# Base units: "g" for weight, "ml" for volume, "pcs" for count
UNIT_TABLE = {
    # Weight
    "kg": ("g", 1000.0, "weight", "kg"),
    "kgs": ("g", 1000.0, "weight", "kg"),
    "kilo": ("g", 1000.0, "weight", "kg"),
    "kilos": ("g", 1000.0, "weight", "kg"),
    "kilogram": ("g", 1000.0, "weight", "kg"),
    "kilograms": ("g", 1000.0, "weight", "kg"),
    "किलो": ("g", 1000.0, "weight", "kg"),
    "किलोग्राम": ("g", 1000.0, "weight", "kg"),
    "केजी": ("g", 1000.0, "weight", "kg"),
    "g": ("g", 1.0, "weight", "g"),
    "gm": ("g", 1.0, "weight", "g"),
    "gms": ("g", 1.0, "weight", "g"),
    "gram": ("g", 1.0, "weight", "g"),
    "grams": ("g", 1.0, "weight", "g"),
    "ग्राम": ("g", 1.0, "weight", "g"),

    # Volume
    "l": ("ml", 1000.0, "volume", "L"),
    "lt": ("ml", 1000.0, "volume", "L"),
    "ltr": ("ml", 1000.0, "volume", "L"),
    "ltrs": ("ml", 1000.0, "volume", "L"),
    "liter": ("ml", 1000.0, "volume", "L"),
    "liters": ("ml", 1000.0, "volume", "L"),
    "litre": ("ml", 1000.0, "volume", "L"),
    "litres": ("ml", 1000.0, "volume", "L"),
    "लीटर": ("ml", 1000.0, "volume", "L"),
    "ml": ("ml", 1.0, "volume", "ml"),
    "mls": ("ml", 1.0, "volume", "ml"),
    "milliliter": ("ml", 1.0, "volume", "ml"),
    "milliliters": ("ml", 1.0, "volume", "ml"),
    "millilitre": ("ml", 1.0, "volume", "ml"),
    "millilitres": ("ml", 1.0, "volume", "ml"),
    "मिलीलीटर": ("ml", 1.0, "volume", "ml"),
}

# Regex to capture measurement values and unit names
_UNIT_KEYS = sorted(UNIT_TABLE.keys(), key=len, reverse=True)
_UNIT_PATTERN_STR = "|".join(re.escape(k) for k in _UNIT_KEYS)
MEASUREMENT_REGEX = re.compile(
    rf'(?<![a-zA-Z0-9])(\d+(?:[.,]\d+)?)\s*({_UNIT_PATTERN_STR})(?![a-zA-Z0-9])',
    re.IGNORECASE,
)


def parse_single_measurement(value_str: str, unit_str: str) -> Optional[Dict[str, Any]]:
    """Normalizes a value string and unit string into a standardized measurement record."""
    clean_unit = unit_str.strip().lower()
    mapping = UNIT_TABLE.get(clean_unit)
    if not mapping:
        return None
    try:
        val = float(value_str.replace(",", "."))
    except (ValueError, TypeError):
        return None

    canonical_base, multiplier, category, display_unit = mapping
    base_value = val * multiplier

    # Format human-friendly display
    if val.is_integer():
        display_val = f"{int(val)}"
    else:
        display_val = f"{val:g}"
    display = f"{display_val} {display_unit}"

    return {
        "raw_value": val,
        "raw_unit": unit_str,
        "base_unit": canonical_base,
        "base_value": base_value,
        "category": category,
        "display": display,
    }


def extract_measurement(text: str) -> Optional[Dict[str, Any]]:
    """Extracts the first explicit product measurement (weight/volume) from text."""
    if not text:
        return None
    match = MEASUREMENT_REGEX.search(text)
    if not match:
        return None
    return parse_single_measurement(match.group(1), match.group(2))


def extract_all_measurements(text: str) -> List[Dict[str, Any]]:
    """Extracts all unique measurements from a string (e.g. title, snippet, body)."""
    if not text:
        return []
    results = []
    seen_bases = set()
    for match in MEASUREMENT_REGEX.finditer(text):
        parsed = parse_single_measurement(match.group(1), match.group(2))
        if parsed:
            key = (parsed["category"], round(parsed["base_value"], 2))
            if key not in seen_bases:
                seen_bases.add(key)
                results.append(parsed)
    return results


def strip_measurement(text: str) -> str:
    """Removes the measurement token from product text to produce clean base product name."""
    if not text:
        return ""
    cleaned = MEASUREMENT_REGEX.sub("", text)
    # Also clean dangling words like "of", "packet", "pack"
    cleaned = re.sub(r'\b(?:of|pack(?:et)?|box|bottle)\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def are_measurements_equal(m1: Dict[str, Any], m2: Dict[str, Any]) -> bool:
    """Checks whether two measurements represent the identical quantity (e.g. 1 kg == 1000 g)."""
    if not m1 or not m2:
        return False
    if m1.get("category") != m2.get("category"):
        return False
    return abs(m1.get("base_value", 0.0) - m2.get("base_value", 0.0)) < 1e-3


def analyze_measurement_matches(
    requested_text: str,
    candidate_texts: List[str],
) -> Dict[str, Any]:
    """
    Analyzes whether candidate texts (search result titles/snippets, inventory names)
    contain the exact requested measurement, or if only other measurements exist.
    """
    requested_meas = extract_measurement(requested_text)
    if not requested_meas:
        return {
            "has_requested_measurement": False,
            "requested_measurement": None,
            "exact_found": False,
            "other_measurements": [],
            "status": "no_measurement_requested",
        }

    exact_found = False
    other_measurements_map: Dict[Tuple[str, float], str] = {}

    for cand in candidate_texts:
        if not cand:
            continue
        c_measurements = extract_all_measurements(cand)
        for cm in c_measurements:
            if are_measurements_equal(requested_meas, cm):
                exact_found = True
            elif cm.get("category") == requested_meas.get("category"):
                key = (cm["category"], round(cm["base_value"], 2))
                other_measurements_map[key] = cm["display"]

    # Sort other measurements ascending by base value
    sorted_others = [
        other_measurements_map[k]
        for k in sorted(other_measurements_map.keys(), key=lambda x: x[1])
    ]

    status = (
        "exact_matched"
        if exact_found
        else ("measurement_mismatch" if sorted_others else "none_found")
    )

    return {
        "has_requested_measurement": True,
        "requested_measurement": requested_meas["display"],
        "exact_found": exact_found,
        "other_measurements": sorted_others,
        "status": status,
    }

