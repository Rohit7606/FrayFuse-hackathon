"""Contagion propagation — the core of FrayFuse.

Stress propagates from buyers to suppliers (against goods flow),
scaled by exposure_pct and damped by cash_buffer_days.  Synchronous
update with sorted iteration for determinism.
"""
