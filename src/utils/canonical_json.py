import json

def to_canonical_json(data: dict) -> bytes:
    """
    Serializes a dictionary to canonical JSON format:
    - Sorted keys
    - No spaces around separators
    - UTF-8 encoded
    - ASCII characters not escaped unless necessary
    """
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")
