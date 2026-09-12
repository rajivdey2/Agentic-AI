"""Optimizer: candidate generation, objective calculators, and OR-Tools solver.

The solver ranks feasible fulfillment plans for at-risk orders using a
weighted objective (cost, delivery time, carbon) subject to capacity and
constraint caps.  If OR-Tools is unavailable or the problem is infeasible, a
deterministic greedy heuristic serves as the fallback.
"""
from __future__ import annotations

from optimizer.solvers import solve
from optimizer.candidates import build_candidates, CandidatePlan