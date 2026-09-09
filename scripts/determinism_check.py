import json
import sys
import urllib.request

def fetch_intervene():
    url = "http://localhost:8000/api/intervene"
    payload = {
        "interventions": [{"node_id": "N042", "amount_cr": 4.8}],
        "baseline_scenario": {"stress_overrides": [], "interventions": []}
    }
    req = urllib.request.Request(url, method="POST")
    req.add_header("Content-Type", "application/json")
    req.data = json.dumps(payload).encode("utf-8")
    with urllib.request.urlopen(req) as response:
        return response.read()

def main():
    try:
        resp1 = fetch_intervene()
        resp2 = fetch_intervene()
    except Exception as e:
        print(f"Failed to reach API: {e}")
        sys.exit(1)

    if resp1 == resp2:
        print("DETERMINISTIC: both identical")
        sys.exit(0)
    else:
        print("NON-DETERMINISTIC: responses differed")
        sys.exit(1)

if __name__ == "__main__":
    main()
