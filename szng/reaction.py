"""Память реакций: на каждом прошлом касании зоны измеряем реальный отскок.

Касание с отскоком 0.5×ATR и больше — доказанная реакция: зона не просто
стоит на графике, она работала. Это главный факт для confirmation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .data import atr
from .models import Zone


def measure_reactions(zone: Zone, df: pd.DataFrame) -> list[dict]:
    """Для каждого бара, пересёкшего зону тенью, меряем ход в сторону зоны
    за REACTION_LOOKAHEAD баров. direction берём из meta (bullish=поддержка)."""
    direction = zone.meta.get("direction", "")
    if not direction:
        direction = "bullish" if zone.kind == "WICK" and zone.meta.get("wick_side") == "low" else ""
    if not direction:
        return []
    a = atr(df)
    reactions: list[dict] = []
    la = config.REACTION_LOOKAHEAD
    for i in range(len(df)):
        bar = df.iloc[i]
        if not (float(bar["low"]) <= zone.top and float(bar["high"]) >= zone.bottom):
            continue
        atr_i = float(a.iloc[i]) if np.isfinite(a.iloc[i]) and a.iloc[i] > 0 else 1.0
        fwd = df.iloc[i + 1: i + 1 + la]
        if fwd.empty:
            continue
        if direction == "bullish":
            bounce = float(fwd["high"].max()) - zone.price
        else:
            bounce = zone.price - float(fwd["low"].min())
        if bounce >= config.MIN_REACTION_ATR * atr_i:
            reactions.append({"time": str(bar["time"]), "bounce": round(bounce, 2)})
    return reactions


def confirmation_from_reactions(reactions: list[dict]) -> float:
    """0.5 база + 0.125 за каждую доказанную реакцию, потолок 1.0."""
    return min(1.0, 0.5 + 0.125 * len(reactions))


def confirmation_from_profile(node: str) -> float:
    """Профиль объёма на уровне: HVN +0.25, LVN -0.25 к базе."""
    return {"HVN": 0.25, "LVN": -0.25}.get(node, 0.0)
