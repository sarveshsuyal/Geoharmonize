"""
Attribute harmonization engine.

Different sources name the same concept differently:
  Dataset A: survey_no        Dataset B: survey_number
  Dataset C: SurveyNumber     Dataset D: khasra_no

Provides:
  - Canonical field mapping (configurable via AttributeMappingRule or defaults)
  - Normalized string comparison (whitespace, casing, punctuation)
  - Numeric comparison with configurable tolerance
  - Explicit null/missing value handling (missing != mismatch)
  - Explainable field-by-field similarity breakdown
"""
import difflib
import re
from typing import Any, Dict, Optional, Tuple

CANONICAL_FIELDS = ["parcel_id", "survey_number", "property_id", "area", "land_use", "ownership_reference"]

DEFAULT_MAPPINGS = {
    "CADASTRAL": {
        "survey_no": "survey_number", "survey_number": "survey_number", "surveynumber": "survey_number",
        "khasra_no": "survey_number", "parcel_no": "parcel_id", "parcel_id": "parcel_id",
        "area_sqm": "area", "area": "area", "land_use": "land_use", "landuse": "land_use",
        "owner_ref": "ownership_reference", "owner": "ownership_reference", "holder_name": "ownership_reference",
    },
    "MUNICIPAL": {
        "property_no": "property_id", "property_id": "property_id", "prop_ref": "property_id",
        "plot_no": "parcel_id", "parcel_id": "parcel_id", "zone": "land_use", "usage": "land_use",
        "area_m2": "area", "area": "area",
    },
    "REVENUE": {
        "khasra_no": "survey_number", "khasra_number": "survey_number", "survey_no": "survey_number",
        "khata_no": "ownership_reference", "owner": "ownership_reference", "holder_name": "ownership_reference",
        "area_ha": "area", "area": "area", "landuse_type": "land_use", "land_use": "land_use",
    },
    "DRONE": {
        "parcel_id": "parcel_id", "candidate_id": "parcel_id", "area_sqm": "area", "area": "area",
    },
}


def normalize_string(val: Any) -> str:
    """Strip whitespace, lowercase, remove non-alphanumeric punctuation."""
    if val is None:
        return ""
    s = str(val).strip().lower()
    # Normalize common abbreviations and whitespace
    s = re.sub(r"[_\-\/\s]+", " ", s)
    return s.strip()


def string_similarity(val_a: Any, val_b: Any) -> float:
    """
    Calculate similarity between two string representations (0.0 to 1.0).
    Handles exact matches, whitespace/case differences, and typos.
    """
    if val_a is None or val_b is None:
        return 0.0
    s_a = normalize_string(val_a)
    s_b = normalize_string(val_b)
    if not s_a and not s_b:
        return 1.0
    if not s_a or not s_b:
        return 0.0
    if s_a == s_b:
        return 1.0
    # Token equality or subsequence
    if s_a in s_b or s_b in s_a:
        len_ratio = min(len(s_a), len(s_b)) / max(len(s_a), len(s_b))
        return round(0.85 * len_ratio, 3)
    # SequenceMatcher for typos / Levenshtein-like distance
    ratio = difflib.SequenceMatcher(None, s_a, s_b).ratio()
    return round(ratio, 3)


def numeric_similarity(val_a: Any, val_b: Any, tolerance_pct: float = 0.10) -> float:
    """
    Calculate similarity between two numeric values with tolerance (0.0 to 1.0).
    """
    try:
        a = float(val_a)
        b = float(val_b)
    except (TypeError, ValueError):
        return 0.0

    if a == 0 and b == 0:
        return 1.0
    max_val = max(abs(a), abs(b))
    if max_val == 0:
        return 1.0

    diff = abs(a - b)
    rel_diff = diff / max_val
    if rel_diff <= tolerance_pct:
        # Full or near-full score within tolerance
        return round(1.0 - (rel_diff / tolerance_pct) * 0.15, 3)

    return round(max(0.0, 1.0 - rel_diff), 3)


def map_to_canonical_attributes(raw_props: dict, dataset_type: str = "CADASTRAL") -> dict:
    canonical = {}
    unmapped = {}

    db_rules = {}
    try:
        from .models import AttributeMappingRule
        db_rules = {
            r.source_field_name.lower(): r.canonical_field_name
            for r in AttributeMappingRule.objects.filter(dataset_type=dataset_type)
        }
    except Exception:
        pass

    defaults = DEFAULT_MAPPINGS.get(dataset_type, {})

    for raw_key, value in (raw_props or {}).items():
        key_lower = str(raw_key).lower()
        canonical_field = db_rules.get(key_lower) or defaults.get(key_lower)
        if canonical_field:
            canonical[canonical_field] = value
        else:
            unmapped[raw_key] = value

    canonical["_unmapped_fields"] = unmapped
    return canonical


def map_to_canonical_attributes_offline(raw_props: dict, dataset_type: str = "CADASTRAL") -> dict:
    canonical = {}
    unmapped = {}
    defaults = DEFAULT_MAPPINGS.get(dataset_type, {})
    for raw_key, value in (raw_props or {}).items():
        canonical_field = defaults.get(str(raw_key).lower())
        if canonical_field:
            canonical[canonical_field] = value
        else:
            unmapped[raw_key] = value
    canonical["_unmapped_fields"] = unmapped
    return canonical


class AttributeComparisonEngine:
    """
    Compares two property dictionaries dynamically.
    Returns explainable breakdown and overall score.
    """

    NUMERIC_FIELDS = {"area", "area_sqm", "area_m2", "area_ha", "perimeter", "calculated_area"}

    def compare(self, props_a: dict, props_b: dict, dataset_type_a: str = "CADASTRAL", dataset_type_b: str = "CADASTRAL") -> dict:
        canonical_a = map_to_canonical_attributes_offline(props_a, dataset_type_a)
        canonical_b = map_to_canonical_attributes_offline(props_b, dataset_type_b)

        fields_detail = {}
        explanations = []
        scores = []
        weights = []

        # Compare canonical fields first
        checked_fields = set()
        for field in CANONICAL_FIELDS:
            checked_fields.add(field)
            val_a = canonical_a.get(field)
            val_b = canonical_b.get(field)

            # Explicit null handling: if missing on BOTH, ignore
            if val_a is None and val_b is None:
                continue

            # If missing on one side: treat as partial/neutral, not a hard zero penalty
            if val_a is None or val_b is None:
                fields_detail[field] = {
                    "val_a": val_a,
                    "val_b": val_b,
                    "score": 0.5,
                    "status": "MISSING_IN_ONE_SOURCE",
                    "explanation": f"Field '{field}' present in one source but missing in other.",
                }
                explanations.append(f"'{field}' only present in one source.")
                scores.append(0.5)
                weights.append(0.5)  # reduced weight for partial information
                continue

            # Both present: compute similarity
            if field in self.NUMERIC_FIELDS:
                score = numeric_similarity(val_a, val_b)
                status = "EXACT" if score == 1.0 else ("SIMILAR" if score >= 0.85 else "DIFFERS")
            else:
                score = string_similarity(val_a, val_b)
                status = "EXACT" if score == 1.0 else ("SIMILAR" if score >= 0.85 else "DIFFERS")

            weight = 2.0 if field in ("survey_number", "parcel_id") else 1.0
            scores.append(score)
            weights.append(weight)

            fields_detail[field] = {
                "val_a": val_a,
                "val_b": val_b,
                "score": score,
                "status": status,
                "explanation": f"'{field}': '{val_a}' vs '{val_b}' (score: {score:.2f})",
            }
            if score >= 0.95:
                explanations.append(f"'{field}' matches ({val_a}).")
            elif score >= 0.70:
                explanations.append(f"'{field}' closely matches ('{val_a}' ~ '{val_b}').")
            else:
                explanations.append(f"'{field}' differs ('{val_a}' vs '{val_b}').")

        # Also check common raw fields that were unmapped
        unmapped_a = canonical_a.get("_unmapped_fields", {})
        unmapped_b = canonical_b.get("_unmapped_fields", {})
        common_unmapped = set(unmapped_a.keys()) & set(unmapped_b.keys())
        for raw_k in common_unmapped:
            if raw_k in checked_fields:
                continue
            va, vb = unmapped_a[raw_k], unmapped_b[raw_k]
            if va is None and vb is None:
                continue
            s = string_similarity(va, vb)
            scores.append(s)
            weights.append(1.0)
            fields_detail[raw_k] = {
                "val_a": va,
                "val_b": vb,
                "score": s,
                "status": "UNMAPPED_MATCH",
                "explanation": f"Unmapped field '{raw_k}' similarity: {s:.2f}",
            }

        if weights:
            total_weight = sum(weights)
            overall_score = round(sum(s * w for s, w in zip(scores, weights)) / total_weight, 3)
        else:
            overall_score = 0.5  # Neutral when no comparable attributes exist

        return {
            "overall_similarity": overall_score,
            "fields": fields_detail,
            "explanations": explanations,
        }
