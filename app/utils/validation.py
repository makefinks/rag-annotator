import json
from jsonschema import validate
from pathlib import Path

def load_json_schema(schema_path):
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_ground_truth(data, schema_path=None):
    """
    Validates the given data dict against the ground truth schema.
    Raises ValidationError if invalid.
    """
    if schema_path is None:
        # Default location 
        app_dir = Path(__file__).resolve().parent.parent
        schema_path = app_dir / "resources" / "ground_truth_schema.json"
    schema = load_json_schema(schema_path)
    validate(instance=data, schema=schema)
