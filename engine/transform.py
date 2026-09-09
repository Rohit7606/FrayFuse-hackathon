"""Collection CSVs → runtime network.json transform.

This is the ONLY module that knows CSVs exist. No other file imports
pandas for data loading.

Usage:
    python -m engine.transform --in data/real/ --out data/real/network.json
"""
