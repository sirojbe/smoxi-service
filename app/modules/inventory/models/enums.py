"""Inventory movement types."""

from __future__ import annotations

from enum import StrEnum


class StockMovementType(StrEnum):
    """Types of inventory stock movements."""

    IN = "in"
    OUT = "out"
    ADJUST = "adjust"
    TRANSFER = "transfer"
