import json
import time
import urllib.request
import sys

def measure(name, path, method="GET", payload=None):
    url = f"http://localhost:8000{path}"
    req = urllib.request.Request(url, method=method)
    if payload:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(payload).encode("utf-8")
    
    t0 = time.time()
    try:
        with urllib.request.urlopen(req) as resp:
            resp.read()
            status = resp.status
    except Exception as e:
        status = str(e)
    t1 = time.time()
    
    latency_ms = (t1 - t0) * 1000
    print(f"{name:15} | {status} | {latency_ms:6.1f}ms")
    return latency_ms

def main():
    print("Endpoint        | Status | Latency")
    print("----------------+--------+---------")
    measure("health", "/health")
    measure("network", "/api/network")
    measure("at-risk", "/api/at-risk")
    
    sim_ms = measure("simulate", "/api/simulate", "POST", {"scenario": {"stress_overrides": [], "interventions": []}})
    int_ms = measure("intervene", "/api/intervene", "POST", {
        "interventions": [{"node_id": "N042", "amount_cr": 4.8}],
        "baseline_scenario": {"stress_overrides": [], "interventions": []}
    })
    
    failed = False
    if sim_ms > 250:
        print(f"WARNING: /api/simulate exceeded 250ms ({sim_ms:.1f}ms)")
        failed = True
    if int_ms > 500:
        print(f"WARNING: /api/intervene exceeded 500ms ({int_ms:.1f}ms)")
        failed = True
        
    if failed:
        sys.exit(1)

if __name__ == "__main__":
    main()
