"""Жизненный цикл зон: снапшот меняется только на закрытии H4.

FRESH → TESTED (касание тенью) → либо живёт дальше, либо INVALIDATED
(пробой телом). Каждое касание умножает freshness на FRESHNESS_TEST_DECAY —
лимитные ордера исполняются, зона «съедается». Прокол тенью — не инвалидация.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import config
from .models import Zone


def load_snapshot(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        return {"version": config.SNAPSHOT_VERSION, "last_bar": "", "zones": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"version": config.SNAPSHOT_VERSION, "last_bar": "", "zones": []}
    except (json.JSONDecodeError, OSError):
        return {"version": config.SNAPSHOT_VERSION, "last_bar": "", "zones": []}


def save_snapshot(zones: list[Zone], last_bar: str, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps({
        "version": config.SNAPSHOT_VERSION,
        "last_bar": last_bar,
        "zone_count": len(zones),
        "zones": [z.to_dict() for z in zones],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)  # атомарная запись: читатель никогда не увидит полуфайл


def apply_lifecycle(zones: list[Zone], new_bars: pd.DataFrame) -> list[Zone]:
    """Прогоняет новые бары по зонам: касания съедают freshness, пробой убивает."""
    alive: list[Zone] = []
    for z in zones:
        dead = False
        for _, bar in new_bars.iterrows():
            h, l = float(bar["high"]), float(bar["low"])
            op, cl = float(bar["open"]), float(bar["close"])
            if l <= z.top and h >= z.bottom:  # касание тенью
                z.test_count += 1
                z.state = "TESTED"
                z.freshness = round(max(config.FRESHNESS_MIN,
                                        z.freshness * config.FRESHNESS_TEST_DECAY), 4)
            body_break = (op < z.bottom and cl > z.top) or (op > z.top and cl < z.bottom)
            if body_break:
                z.state = "INVALIDATED"
                dead = True
                break
        if not dead:
            alive.append(z)
    return alive


def should_update(snapshot: dict, df: pd.DataFrame) -> bool:
    """Снапшот пересчитываем только когда появилась новая закрытая свеча."""
    if df.empty:
        return False
    last_bar = str(df["time"].iloc[-1])
    return snapshot.get("last_bar", "") != last_bar
