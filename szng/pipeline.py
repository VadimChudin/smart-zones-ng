"""Сквозной пайплайн: CSV → детекторы → скоринг → сетка → lifecycle → JSON.

CLI:
    python -m szng.pipeline data/XAUUSD_H4.csv --out zones_output.json --snapshot state.json
"""
from __future__ import annotations

import argparse

from .data import load_csv
from .detectors import detect_all
from .export import export_json
from .grid import build_grid, current_price
from .lifecycle import (apply_lifecycle, load_snapshot, save_snapshot,
                        should_update)
from .models import Zone
from .scoring import score_zones


def run(df, snapshot_path: str | None = None) -> list[Zone]:
    """Инкрементальный прогон: если свеча не новая — возвращаем снапшот как есть."""
    snap = load_snapshot(snapshot_path) if snapshot_path else {"last_bar": "", "zones": []}
    if snapshot_path and not should_update(snap, df):
        return [Zone.from_dict(z) for z in snap.get("zones", [])]

    zones = detect_all(df, df_tf if (df_tf := "H4") else "H4")
    zones = score_zones(zones, df)

    # старые зоны из снапшота: прогоняем через новые бары (freshness, пробои)
    last_bar = snap.get("last_bar", "")
    new_bars = df
    if last_bar:
        new_bars = df[df["time"].astype(str) > last_bar]
    carried = [Zone.from_dict(z) for z in snap.get("zones", [])]
    alive_carried = apply_lifecycle(carried, new_bars)

    # свежие детекции + уцелевшие старые (старые не дублируем)
    merged = zones + [z for z in alive_carried
                      if not any(abs(z.price - n.price) <= (n.top - n.bottom) for n in zones)]
    grid = build_grid(merged, df)

    if snapshot_path:
        save_snapshot(grid, str(df["time"].iloc[-1]), snapshot_path)
    return grid


def main() -> None:
    ap = argparse.ArgumentParser(description="Smart Zones NG pipeline")
    ap.add_argument("csv", help="CSV с колонками time,open,high,low,close[,tick_volume]")
    ap.add_argument("--out", default="zones_output.json")
    ap.add_argument("--snapshot", default="state.json")
    args = ap.parse_args()
    df = load_csv(args.csv)
    grid = run(df, args.snapshot)
    payload = export_json(grid, args.out, current_price(df))
    print(f"zones: {payload['zone_count']} | price: {payload['current_price']:.2f}")
    for z in grid:
        print(f"  {z.display_side:5s} {z.label}  final={z.final_score():.2f} "
              f"fresh={z.freshness:.2f} conf={z.confirmation:.2f}")


if __name__ == "__main__":
    main()
