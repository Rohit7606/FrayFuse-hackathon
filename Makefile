# Convenience targets. Everything here is a shortcut for a command already
# documented in AGENTS.md §5.2 — nothing is only runnable through make.
.PHONY: demo api web test lint mocks determinism

NETWORK ?= data/mock/network.json

# Start the API and the frontend together — PERSON_B.md §7.
# Windows is the demo machine, so the runner is PowerShell.
demo:
	pwsh -File scripts/demo.ps1 -Network $(NETWORK) || powershell -File scripts/demo.ps1 -Network $(NETWORK)

# No --reload: the file watcher can restart the backend mid-presentation.
api:
	FRAYFUSE_NETWORK=$(NETWORK) python -m uvicorn api.main:app --port 8000

web:
	cd web && npm run dev:live

test:
	python -m pytest tests/ -q

lint:
	ruff check .
	cd web && npm run lint

mocks:
	python scripts/refresh_web_mocks.py

# Same input must give byte-identical output — AGENTS.md §3.1.
determinism:
	python -m engine.pipeline $(NETWORK) --json > /tmp/ff1.json
	python -m engine.pipeline $(NETWORK) --json > /tmp/ff2.json
	diff /tmp/ff1.json /tmp/ff2.json && echo DETERMINISTIC
