"""API configuration — one place for all tunables."""

import os

# Path to the network JSON file. The entire real-data switch is this one env var.
NETWORK_PATH = os.getenv("FRAYFUSE_NETWORK", "data/mock/network.json")

# Origins permitted by CORS — frontend dev servers.
#
# Both spellings of every port. `localhost` and `127.0.0.1` are different
# origins to a browser, so listing only one means the app dies with an opaque
# CORS error the moment somebody opens the other — a blank screen on stage with
# nothing on it to say why. Vite prints both spellings when started with
# --host, which is exactly when the wrong one gets clicked.
#
# FRAYFUSE_CORS_ORIGINS overrides the list entirely, comma-separated, for a
# deployment that serves the frontend from somewhere else.
_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("FRAYFUSE_CORS_ORIGINS", ",".join(_DEV_ORIGINS)).split(",")
    if origin.strip()
]
