"""API configuration — one place for all tunables."""

import os

# Path to the network JSON file. The entire real-data switch is this one env var.
NETWORK_PATH = os.getenv("FRAYFUSE_NETWORK", "data/mock/network.json")

# Origins permitted by CORS — frontend dev servers
CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
