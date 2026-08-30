"""Данные: CSV, ресемплинг, ATR, синтетика для тестов."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

REQUIRED_COLUMNS = ["time", "open", "high", "low", "close"]


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing columns: {missing}")
    df["time"] = pd.to_datetime(df["time"])
    if "tick_volume" not in df.columns:
        df["tick_volume"] = 1.0
    return df.sort_values("time").reset_index(drop=True)


def resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    agg = df.set_index("time").resample(rule).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last",
         "tick_volume": "sum"}
    ).dropna().reset_index()
    return agg


def atr(df: pd.DataFrame, period: int | None = None) -> pd.Series:
    """True Range, сглаженный простым средним (min_periods=1 — без NaN-ямы в начале)."""
    period = period or config.ATR_PERIOD
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=1).mean()


def synthetic(n: int = 600, seed: int = 7, start: float = 4400.0) -> pd.DataFrame:
    """Синтетический H4-ряд с зашитыми уровнями: цена mean-revert'ит к ним,
    поэтому вокруг уровней образуются настоящие кластеры касаний и отскоки."""
    rng = np.random.default_rng(seed)
    levels = [4315.0, 4345.0, 4375.0, 4425.0, 4455.0, 4485.0]
    prices = np.empty(n)
    p = start
    for i in range(n):
        pull = sum((lv - p) * 0.8 for lv in levels if abs(lv - p) < 12.0)
        p += rng.normal(0.0, 1.6) + pull
        prices[i] = p
    opens = np.roll(prices, 1)
    opens[0] = prices[0]
    highs = np.maximum(opens, prices) + np.abs(rng.normal(0, 0.8, n))
    lows = np.minimum(opens, prices) - np.abs(rng.normal(0, 0.8, n))
    vol = np.abs(rng.normal(100.0, 30.0, n))
    idx = pd.date_range("2026-01-01", periods=n, freq="4h")
    return pd.DataFrame({"time": idx, "open": opens, "high": highs,
                         "low": lows, "close": prices, "tick_volume": vol})
