"""Manhattan distance helper for routing and cost math.

Why here: distances are pure domain geometry (per docs/03 the grid is moved in
"cuadras"/blocks); every solver, rule and the simulator need the same
definition, and it must not depend on anything but stdlib.
"""

from __future__ import annotations


def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    """Return the Manhattan (taxicab) distance between two `(x, y)` points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
