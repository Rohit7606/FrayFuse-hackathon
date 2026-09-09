import json
import sys
import urllib.request
import jsonschema

def load_schema():
    with open("schema.json", "r", encoding="utf-8") as f:
        return json.load(f)

def validate_endpoint(schema, def_name, name, path, payload=None):
    url = f"http://localhost:8000{path}"
    req = urllib.request.Request(url, method="POST" if payload else "GET")
    if payload:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(payload).encode("utf-8")
    
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"FAIL: {name} returned error: {e}")
        sys.exit(1)
        
    try:
        # validate against the specific definition in schema.json
        # JSONSchema doesn't natively expose definitions as root schemas in python 
        # without referencing, so we construct a wrapper schema
        wrapper = {
            "$schema": schema.get("$schema", "http://json-schema.org/draft-07/schema#"),
            "$ref": f"#/definitions/{def_name}",
            "definitions": schema.get("definitions", {})
        }
        jsonschema.validate(instance=data, schema=wrapper)
        print(f"PASS: {name} validated against {def_name}")
    except jsonschema.exceptions.ValidationError as e:
        print(f"FAIL: {name} schema validation failed!")
        print(e.message)
        sys.exit(1)

def check_health():
    url = "http://localhost:8000/health"
    try:
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read().decode())
            print(f"PASS: /health -> status: {data['status']}, network: {data['network']}, nodes: {data['nodes']}")
    except Exception as e:
        print(f"FAIL: /health returned error: {e}")
        sys.exit(1)

def main():
    schema = load_schema()
    
    print("Running Pre-Flight Checks...")
    check_health()
    validate_endpoint(schema, "NetworkResponse", "GET /api/network", "/api/network")
    validate_endpoint(schema, "AtRiskResponse", "GET /api/at-risk", "/api/at-risk")
    
    validate_endpoint(schema, "ScoredNetwork", "POST /api/simulate", "/api/simulate", {"scenario": {"stress_overrides": [], "interventions": []}})
    validate_endpoint(schema, "InterveneResponse", "POST /api/intervene", "/api/intervene", {
        "interventions": [{"node_id": "N042", "amount_cr": 4.8}],
        "baseline_scenario": {"stress_overrides": [], "interventions": []}
    })
    
    print("\nALL PREFLIGHT CHECKS PASSED.")
    sys.exit(0)

if __name__ == "__main__":
    main()
