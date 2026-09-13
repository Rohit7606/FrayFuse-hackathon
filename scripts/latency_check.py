import json
import sys
import time
import urllib.request


def measure(name, path, method="GET", payload=None):
    url = f"http://127.0.0.1:8000{path}"
    req = urllib.request.Request(url, method=method)
    if payload:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(payload).encode("utf-8")

    t0 = time.time()
    try:
        with urllib.request.urlopen(req) as resp:
            resp.read()
            status = resp.status
    except OSError as e:
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

    # Budgets, not targets. On the committed 412-node network a warm
    # /api/simulate measures ~350-420ms and /api/intervene ~700-790ms; the
    # latter is roughly double because it scores the network twice, before and
    # after the funding, to build the delta. These ceilings sit at about twice
    # the observed worst case, so they catch a real regression without going
    # red on an ordinary demo machine. Re-measure before tightening them.
    SIMULATE_BUDGET_MS = 800
    INTERVENE_BUDGET_MS = 1600

    failed = False
    if sim_ms > SIMULATE_BUDGET_MS:
        print(f"WARNING: /api/simulate exceeded {SIMULATE_BUDGET_MS}ms ({sim_ms:.1f}ms)")
        failed = True
    if int_ms > INTERVENE_BUDGET_MS:
        print(f"WARNING: /api/intervene exceeded {INTERVENE_BUDGET_MS}ms ({int_ms:.1f}ms)")
        failed = True

    if failed:
        sys.exit(1)

if __name__ == "__main__":
    main()
