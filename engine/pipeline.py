"""The single public entry point for the FrayFuse engine.

Person B calls exactly one function: score_network().
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


class UnknownNodeError(Exception):
    """Raised when a scenario references a node_id not present in the network."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        super().__init__(f"{node_id} not in network")


@dataclass(frozen=True)
class StressOverride:
    """Override a node's own_stress value in a scenario."""

    node_id: str
    own_stress: float


@dataclass(frozen=True)
class Intervention:
    """Fund a node to reduce its inherited stress."""

    node_id: str
    amount_cr: float


@dataclass(frozen=True)
class Scenario:
    """An immutable scenario with stress overrides and interventions.

    Frozen and tuple-based so it cannot be mutated mid-scoring.
    """

    stress_overrides: tuple[StressOverride, ...] = ()
    interventions: tuple[Intervention, ...] = ()

    def with_interventions(
        self, interventions: Sequence[Intervention]
    ) -> Scenario:
        """Return a new Scenario with additional interventions appended."""
        return Scenario(
            stress_overrides=self.stress_overrides,
            interventions=self.interventions + tuple(interventions),
        )


def score_network(
    network: dict,
    scenario: Scenario | None = None,
) -> dict:
    """Score a network under an optional scenario.

    Args:
        network:  NetworkInput dict, validated against schema.json
        scenario: stress overrides and interventions; None means baseline

    Returns:
        ScoredNetwork dict, validated against schema.json

    Pure. Deterministic. No I/O, no globals, no mutation of the input.
    """
    raise NotImplementedError("Pipeline not yet implemented — Phase 1 work")
