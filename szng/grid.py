"""Адаптивная симметричная сетка: 3 слота выше + 3 ниже текущей цены.

Шаг слота — от ATR(H4): в тренде зоны разъезжаются, в боковике сжимаются.
Жёсткая лестница в пипсах ломается, когда волатильность золота меняется
в два раза; ATR-шаг переживает это автоматически. Диапазон зажат в
GRID_MIN_DIST..GRID_MAX_DIST, чтобы сетка не уехала за горизонт.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .data import atr
from .models import Zone


def current_price(df: pd.DataFrame) -> float | None:
    if df is None or df.empty:
        return None
    return float(df["close"].iloc[-1])


def slot_step(df: pd.DataFrame) -> float:
    a = atr(df)
    if a.empty or not np.isfinite(a.iloc[-1]) or a.iloc[-1] <= 0:
        return (config.GRID_MIN_DIST + config.GRID_MAX_DIST) / 2.0
    s = float(a.iloc[-1]) * config.GRID_SLOT_MIN_ATR
    return max(config.GRID_MIN_DIST, min(config.GRID_MAX_DIST, s))


def _pick_slot(cands: list[Zone], low: float, high: float,
               taken: list[Zone], price: float, side: str) -> Zone | None:
    """Лучшая зона слота по final_score; уже взятые исключаем."""
    tol = (high - low) * config.GRID_TOLERANCE
    lo, hi = max(0.0, low - tol), high + tol
    pool = [z for z in cands
            if lo <= abs(z.price - price) <= hi and z not in taken
            and not any(abs(z.price - t.price) < (z.top - z.bottom) for t in taken)]
    if not pool:
        return None
    pool.sort(key=lambda z: (z.final_score(), -abs(z.price - price)), reverse=True)
    pick = pool[0]
    pick.display_side = side
    return pick


def build_grid(zones: list[Zone], df: pd.DataFrame) -> list[Zone]:
    """3 слота сверху + 3 снизу. Пустой слот не залипает: окно следующего
    слота сдвигается номинально, а не от несуществующей предыдущей зоны."""
    price = current_price(df)
    if price is None or not zones:
        return []
    step = slot_step(df)
    selected: list[Zone] = []
    for side, sign in (("ABOVE", 1), ("BELOW", -1)):
        cands = [z for z in zones if (z.price - price) * sign > 0 and z.state != "INVALIDATED"]
        prev = 0.0
        taken_side: list[Zone] = []
        for slot in range(config.ZONES_PER_SIDE):
            anchor = prev if prev > 0 else 0.0
            nominal_prev = slot * step  # опора для пустого предыдущего слота
            low = anchor + step if anchor > 0 else step
            if anchor == 0.0 and prev == 0.0 and slot > 0:
                low = nominal_prev + step
            high = low + step
            pick = _pick_slot(cands, low, high, taken_side + selected, price, side)
            if pick is not None:
                taken_side.append(pick)
                selected.append(pick)
                prev = abs(pick.price - price)
    return selected
