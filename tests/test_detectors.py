import pandas as pd

from szng.detectors import (detect_fvgs, detect_order_blocks, detect_sweeps,
                            detect_wick_clusters, find_impulses)


def _impulse_df():
    """Медвежья свеча-источник → мощный бычий импульс → цена уходит вверх."""
    rows = []
    base = 4400.0
    for i in range(20):
        rows.append((f"2026-01-01 {i:02d}:00", base, base + 1, base - 1, base + 0.5, 100.0))
    # свеча-источник (медвежья)
    rows.append(("2026-01-01 20:00", base + 0.5, base + 1.5, base - 2.5, base - 2.0, 100.0))
    # импульс: тело 12$ >> ATR, закрытие на хаях
    rows.append(("2026-01-01 21:00", base - 2.0, base + 10.5, base - 2.2, base + 10.0, 300.0))
    for i in range(22, 40):
        p = base + 10 + (i - 22) * 1.5
        rows.append((f"2026-01-01 {i:02d}:00", p - 1.0, p + 1.0, p - 1.5, p, 120.0))
    return pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "tick_volume"])


def test_impulse_found():
    df = _impulse_df()
    impulses = find_impulses(df)
    assert 21 in impulses


def test_order_block_is_source_candle():
    df = _impulse_df()
    zones = detect_order_blocks(df)
    ob = [z for z in zones if z.kind == "OB" and z.meta.get("direction") == "bullish"]
    assert ob, "order block не найден"
    z = ob[0]
    # OB — медвежья свеча-источник с high 4401.5 / low 4397.5
    assert abs(z.price - 4399.5) < 0.6
    assert z.meta["impulse_body_atr"] > 1.0
    assert z.meta["move_after_atr"] > 0


def test_wick_clusters_need_two_touches():
    rows = []
    for i in range(10):
        rows.append((f"2026-01-02 {i:02d}:00", 100.0, 105.0, 95.0, 100.0, 50.0))
    rows.append(("2026-01-02 10:00", 100.0, 101.0, 90.0, 100.0, 50.0))
    rows.append(("2026-01-02 11:00", 100.0, 101.0, 90.4, 100.0, 50.0))
    df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "tick_volume"])
    zones = detect_wick_clusters(df)
    lows = [z for z in zones if z.meta.get("wick_side") == "low"]
    assert lows and abs(lows[0].price - 90.2) < 0.5
    assert lows[0].meta["touches"] >= 2


def test_sweep_detected():
    rows = []
    for i in range(25):
        rows.append((f"2026-01-03 {i:02d}:00", 100.0, 110.0, 95.0, 100.0, 50.0))
    # тень пробила 110, закрытие вернулось ниже — sweep хая
    rows.append(("2026-01-03 25:00", 100.0, 112.0, 98.0, 105.0, 80.0))
    df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "tick_volume"])
    zones = detect_sweeps(df)
    assert any(z.kind == "SWEEP" and abs(z.price - 110.0) < 0.1 for z in zones)


def test_fvg_detected():
    rows = [
        ("2026-01-04 00:00", 100.0, 101.0, 99.0, 100.0, 50.0),
        ("2026-01-04 01:00", 100.0, 104.0, 100.0, 103.5, 50.0),
        ("2026-01-04 02:00", 103.5, 106.0, 103.0, 105.0, 50.0),  # low 103 > high[0] 101 → бычий FVG
    ]
    df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "tick_volume"])
    zones = detect_fvgs(df)
    assert any(z.kind == "FVG" and z.bottom == 101.0 and z.top == 103.0 for z in zones)
