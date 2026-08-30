"""Volume-at-price профиль: сколько объёма прошло на каждом ценовом уровне.

Источник истины для «жива ли зона»: уровень на HVN — реальная проторговка,
уровень в LVN — ценовая пустота, цена пройдёт транзитом.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def build_profile(df: pd.DataFrame, bins: int | None = None) -> pd.DataFrame:
    """Распределяет объём каждой свечи равномерно по её диапазону high..low."""
    bins = bins or config.PROFILE_BINS
    if df.empty:
        return pd.DataFrame(columns=["price", "volume"])
    lo, hi = float(df["low"].min()), float(df["high"].max())
    if hi <= lo:
        return pd.DataFrame(columns=["price", "volume"])
    edges = np.linspace(lo, hi, bins + 1)
    vol = np.zeros(bins)
    step = (hi - lo) / bins
    for _, row in df.iterrows():
        h, l, v = float(row["high"]), float(row["low"]), float(row.get("tick_volume", 1.0))
        if h <= l:
            i = min(int((l - lo) / step), bins - 1)
            vol[i] += v
            continue
        i0 = max(0, int((l - lo) / step))
        i1 = min(bins - 1, int((h - lo) / step))
        per_bin = v / max(1, (i1 - i0 + 1))
        vol[i0:i1 + 1] += per_bin
    return pd.DataFrame({"price": (edges[:-1] + edges[1:]) / 2, "volume": vol})


def profile_value_at(profile: pd.DataFrame, price: float) -> float:
    """Объём на ближайшей к price строке профиля."""
    if profile.empty:
        return 0.0
    idx = (profile["price"] - price).abs().idxmin()
    return float(profile.loc[idx, "volume"])


def hvn_lvn(profile: pd.DataFrame) -> tuple[float, float]:
    """Пороги HVN/LVN как доли от среднего объёма на строку."""
    if profile.empty or profile["volume"].mean() == 0:
        return 0.0, 0.0
    avg = float(profile["volume"].mean())
    return avg * config.HVN_RATIO, avg * config.LVN_RATIO


def node_type(profile: pd.DataFrame, price: float) -> str:
    """HVN | LVN | NORM для цены."""
    if profile.empty:
        return "NORM"
    hvn, lvn = hvn_lvn(profile)
    v = profile_value_at(profile, price)
    if v >= hvn:
        return "HVN"
    if v <= lvn:
        return "LVN"
    return "NORM"


def poc(profile: pd.DataFrame) -> float | None:
    """Point of Control — цена с максимальным объёмом."""
    if profile.empty:
        return None
    return float(profile.loc[profile["volume"].idxmax(), "price"])
