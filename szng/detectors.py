"""Детекторы зон: order blocks, wick-кластеры, sweep ликвидности, FVG.

Главный детектор — импульсный: сильная свеча, после которой цена ушла,
оставляет order block (последняя противоположная свеча перед импульсом).
Это принципиально сильнее «теней подряд»: фитиль — след, order block — причина.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .data import atr
from .models import Zone, utc_now


def _mk(price, top, bottom, kind, tf, born, meta=None, confluences=None):
    return Zone(price=round(price, 2), top=round(top, 2), bottom=round(bottom, 2),
                kind=kind, tf=tf, born_at=born, meta=meta or {},
                confluences=confluences or [])


def find_impulses(df: pd.DataFrame) -> list[int]:
    """Индексы импульсных свечей: тело > IMPULSE_BODY_ATR × ATR,
    закрытие в крайней части диапазона."""
    if len(df) < config.ATR_PERIOD + 2:
        return []
    a = atr(df)
    body = (df["close"] - df["open"]).abs()
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    close_pos = (df["close"] - df["low"]) / rng
    idx = []
    for i in range(1, len(df)):
        if not np.isfinite(a.iloc[i]) or a.iloc[i] <= 0:
            continue
        if body.iloc[i] < config.IMPULSE_BODY_ATR * a.iloc[i]:
            continue
        if close_pos.iloc[i] >= config.IMPULSE_CLOSE_POS or close_pos.iloc[i] <= 1 - config.IMPULSE_CLOSE_POS:
            idx.append(i)
    return idx


def detect_order_blocks(df: pd.DataFrame, tf: str = "H4") -> list[Zone]:
    """Bullish OB: последняя медвежья свеча перед бычьим импульсом (поддержка).
    Bearish OB: последняя бычья свеча перед медвежьим импульсом (сопротивление).
    Сила импульса и ход после него сохраняются в meta — scoring их подхватит."""
    zones: list[Zone] = []
    impulses = find_impulses(df)
    a = atr(df)
    for i in impulses:
        bullish = df["close"].iloc[i] > df["open"].iloc[i]
        ob_idx = None
        for j in range(i - 1, max(0, i - config.OB_SEARCH_BACK) - 1, -1):
            opposite = df["close"].iloc[j] < df["open"].iloc[j] if bullish else df["close"].iloc[j] > df["open"].iloc[j]
            if opposite:
                ob_idx = j
                break
        if ob_idx is None:
            continue
        bar = df.iloc[ob_idx]
        top, bottom = float(bar["high"]), float(bar["low"])
        if top <= bottom:
            continue
        price = (top + bottom) / 2.0
        # сила смещения: ход после импульса в ATR
        fwd = df.iloc[i + 1: i + 1 + config.OB_MOVE_BARS]
        move = 0.0
        if not fwd.empty:
            move = (float(fwd["high"].max()) - price) if bullish else (price - float(fwd["low"].min()))
        atr_i = float(a.iloc[i]) if np.isfinite(a.iloc[i]) and a.iloc[i] > 0 else 1.0
        meta = {
            "direction": "bullish" if bullish else "bearish",
            "impulse_body_atr": round(abs(float(df["close"].iloc[i] - df["open"].iloc[i])) / atr_i, 2),
            "move_after_atr": round(move / atr_i, 2),
        }
        zones.append(_mk(price, top, bottom, "OB", tf, str(bar["time"]),
                         meta=meta, confluences=["order_block"]))
    return zones


def detect_wick_clusters(df: pd.DataFrame, tf: str = "H4") -> list[Zone]:
    """Наследие SZP: кластеры верхних/нижних теней. Запасной детектор —
    ловит уровни там, где импульсной свечи не было, но цена отбивалась."""
    if len(df) < config.WICK_MIN_TOUCHES + 1:
        return []
    a = atr(df)
    tol = float(a.iloc[-1]) * config.WICK_CLUSTER_TOL_ATR
    tol = max(tol, 0.5)
    zones: list[Zone] = []
    for side in ("high", "low"):
        pts = sorted(float(x) for x in df[side])
        cluster = [pts[0]]
        def flush(cl):
            if len(cl) >= config.WICK_MIN_TOUCHES:
                c = float(np.median(cl))
                zones.append(_mk(c, c + tol / 2, c - tol / 2, "WICK", tf, "",
                                 meta={"touches": len(cl), "wick_side": side},
                                 confluences=[f"wick_cluster_{side}"]))
        for p in pts[1:]:
            if p - cluster[-1] <= tol:
                cluster.append(p)
            else:
                flush(cluster)
                cluster = [p]
        flush(cluster)
    return zones


def detect_sweeps(df: pd.DataFrame, tf: str = "H4") -> list[Zone]:
    """Sweep: тень пробила прошлый экстремум, закрытие вернулось — стопы сняты,
    за уровнем стоял крупный интерес. Зона — на сметённом экстремуме."""
    zones: list[Zone] = []
    a = atr(df)
    lb = config.SWEEP_LOOKBACK
    for i in range(lb, len(df)):
        hist = df.iloc[i - lb:i]
        ref_hi, ref_lo = float(hist["high"].max()), float(hist["low"].min())
        bar = df.iloc[i]
        atr_i = float(a.iloc[i]) if np.isfinite(a.iloc[i]) and a.iloc[i] > 0 else 1.0
        if float(bar["high"]) > ref_hi and float(bar["close"]) < ref_hi:
            zones.append(_mk(ref_hi, ref_hi + 0.25 * atr_i, ref_hi - 0.25 * atr_i,
                             "SWEEP", tf, str(bar["time"]),
                             meta={"direction": "bearish"}, confluences=["sweep_high"]))
        if float(bar["low"]) < ref_lo and float(bar["close"]) > ref_lo:
            zones.append(_mk(ref_lo, ref_lo + 0.25 * atr_i, ref_lo - 0.25 * atr_i,
                             "SWEEP", tf, str(bar["time"]),
                             meta={"direction": "bullish"}, confluences=["sweep_low"]))
    return zones


def detect_fvgs(df: pd.DataFrame, tf: str = "H4") -> list[Zone]:
    """Fair Value Gap: трёхсвечный дисбаланс (low[i+1] > high[i-1] и наоборот).
    FVG отдельно не рисуем — это confluence: усиливает зону, попавшую в gap."""
    zones: list[Zone] = []
    for i in range(1, len(df) - 1):
        p, n = df.iloc[i - 1], df.iloc[i + 1]
        if float(n["low"]) > float(p["high"]):  # бычий FVG — поддержка
            mid = (float(n["low"]) + float(p["high"])) / 2.0
            zones.append(_mk(mid, float(n["low"]), float(p["high"]), "FVG", tf,
                             str(df.iloc[i]["time"]), confluences=["fvg_bullish"]))
        elif float(n["high"]) < float(p["low"]):  # медвежий FVG — сопротивление
            mid = (float(n["high"]) + float(p["low"])) / 2.0
            zones.append(_mk(mid, float(p["low"]), float(n["high"]), "FVG", tf,
                             str(df.iloc[i]["time"]), confluences=["fvg_bearish"]))
    return zones


def detect_all(df: pd.DataFrame, tf: str = "H4") -> list[Zone]:
    return (detect_order_blocks(df, tf) + detect_wick_clusters(df, tf)
            + detect_sweeps(df, tf) + detect_fvgs(df, tf))
