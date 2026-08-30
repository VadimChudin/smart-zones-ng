"""Walk-forward бэктест: честная проверка без подглядывания вперёд.

На каждом шаге строим зоны только по истории до бара t, потом смотрим
BT_LOOKAHEAD баров вперёд: было ли касание зоны и отскок >= BT_MIN_REACTION ($)
до пробоя. Метрики: hit-rate, средний отскок, статистика по типам зон.

CLI: python -m szng.backtest data/XAUUSD_H4.csv
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

from . import config
from .detectors import detect_all
from .grid import build_grid, current_price
from .models import Zone
from .scoring import score_zones


def _outcome(zone: Zone, future: pd.DataFrame) -> tuple[bool, float]:
    """Касание + отскок до пробоя. Возвращает (hit, bounce_$)."""
    direction = zone.meta.get("direction") or (
        "bullish" if zone.meta.get("wick_side") == "low" else "bearish")
    for i in range(len(future)):
        bar = future.iloc[i]
        h, l, op, cl = float(bar["high"]), float(bar["low"]), float(bar["open"]), float(bar["close"])
        body_break = (op < zone.bottom and cl > zone.top) or (op > zone.top and cl < zone.bottom)
        if body_break:
            return False, 0.0
        if l <= zone.top and h >= zone.bottom:
            fwd = future.iloc[i + 1:]
            if fwd.empty:
                return False, 0.0
            if direction == "bullish":
                bounce = float(fwd["high"].max()) - zone.price
            else:
                bounce = zone.price - float(fwd["low"].min())
            return bounce >= config.BT_MIN_REACTION, round(bounce, 2)
    return False, 0.0


def run_backtest(df: pd.DataFrame) -> dict:
    results = {"steps": 0, "zones": 0, "hits": 0, "bounces": [],
               "by_kind": {}, "by_side": {"ABOVE": [0, 0], "BELOW": [0, 0]}}
    for t in range(config.BT_WARMUP, len(df) - config.BT_LOOKAHEAD, config.BT_STEP):
        hist = df.iloc[:t]
        zones = score_zones(detect_all(hist), hist)
        grid = build_grid(zones, hist)
        if not grid:
            continue
        results["steps"] += 1
        future = df.iloc[t + 1: t + 1 + config.BT_LOOKAHEAD]
        for z in grid:
            hit, bounce = _outcome(z, future)
            results["zones"] += 1
            results["hits"] += int(hit)
            results["bounces"].append(bounce)
            k = results["by_kind"].setdefault(z.kind, [0, 0])
            k[1] += 1
            k[0] += int(hit)
            s = results["by_side"][z.display_side or "ABOVE"]
            s[1] += 1
            s[0] += int(hit)
    z_total = results["zones"]
    results["hit_rate"] = round(results["hits"] / z_total, 3) if z_total else 0.0
    results["avg_bounce"] = round(sum(results.pop("bounces")) / z_total, 2) if z_total else 0.0
    results["by_kind"] = {k: {"hit_rate": round(v[0] / v[1], 3) if v[1] else 0.0,
                              "count": v[1]} for k, v in results["by_kind"].items()}
    results["by_side"] = {k: {"hit_rate": round(v[0] / v[1], 3) if v[1] else 0.0,
                              "count": v[1]} for k, v in results["by_side"].items()}
    return results


def main() -> None:
    ap = argparse.ArgumentParser(description="Smart Zones NG walk-forward backtest")
    ap.add_argument("csv")
    args = ap.parse_args()
    from .data import load_csv
    report = run_backtest(load_csv(args.csv))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
