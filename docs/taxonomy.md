# Feature taxonomy

Mathen cards currently use a free-form feature `category`. G1 adds a
backward-compatible controlled vocabulary for new producers without migrating
the reviewed cards or changing the card schema.

## New feature dimensions

The Python API in `mathen.taxonomy` accepts these dimensions:

| Field        | Controlled values                                                                                                                                                                        |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `kind`       | `boundary`, `control`, `interface`, `mechanism`, `model`, `property`, `state`, `workflow`                                                                                                |
| `domain`     | `build`, `communication`, `coordination`, `data`, `deployment`, `execution`, `integration`, `language`, `media`, `observability`, `reliability`, `resource`, `security`, `storage`, `ui` |
| `layer`      | `application`, `control`, `data`, `interface`, `platform`, `runtime`, `storage`, `system`                                                                                                |
| `pattern_id` | Any proposed or registered lowercase hyphenated identifier                                                                                                                               |

`pattern_id` is deliberately open. A reviewer can propose a new pattern ID
before that pattern is added to a future registry. Invalid `kind`, `domain`, and
`layer` values are rejected so that spelling mistakes do not silently become
new taxonomy values.

## Compatibility and normalization

Existing cards remain valid with their `category` fields. Every category value
currently present in `data/systems/` is included in
`mathen.taxonomy.CATEGORY_ALIASES`. `category_alias()` translates a legacy
category into all four new fields, and `normalize_feature_taxonomy()` accepts a
legacy `{"category": ...}` object by default.

Normalization is deterministic:

```python
from mathen.taxonomy import normalize_feature_taxonomy

normalize_feature_taxonomy(
    {
        "kind": "architecture",
        "domain": "networking",
        "layer": "api",
        "pattern_id": "Proposed Network Pattern",
    }
)
# {
#   "kind": "model",
#   "domain": "communication",
#   "layer": "interface",
#   "pattern_id": "proposed-network-pattern",
# }
```

Use `validate_feature_taxonomy()` when invalid input should raise
`TaxonomyValidationError`, or `is_valid_feature_taxonomy()` for a boolean
check. Pass `allow_legacy_category=False` for a new producer that must use the
controlled fields, and `require_pattern_id=True` when a complete pattern
reference is required.

This module is an additive migration seam. It does not mass-migrate the 654
existing cards, and `category` remains the compatibility field until a later
schema and storage migration explicitly adopts the new dimensions.
