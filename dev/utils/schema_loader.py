import os
import json

class SchemaLoader:
    def __init__(self, schema_dir: str) -> None:
        self.cur_dir = os.path.dirname(os.path.realpath(__file__))
        self.schema_dir = schema_dir
    
    def load_output_schema(self, filename: str) -> dict:
        schema_filename = f"{filename}_output.json"
        full_schema_dir = os.path.join(self.cur_dir, self.schema_dir, schema_filename)
        with open(full_schema_dir, 'r', encoding="utf-8") as f:
            schema = json.load(f)
        return schema