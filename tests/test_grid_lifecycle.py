import pandas as pd

from szng import config
from szng.grid import build_grid, current_price, slot_step
from szng.lifecycle import apply_lifecycle, load_snapshot, save_snapshot, should_update
from szng.models import Zone


def _df(price=4400.0, n=30):
    rows = [(f"2026-01-08 {i:02d}:00", price, price + 2.0, price - 2.0, price, 100.0)
            for i in range(n)]
    return pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "tick_volume"])


def _z(offset, kind="OB", strength=10.0):
    return Zone(price=4400.0 + offset, top=4400.0 + offset + 1.0,
                bottom=4400.0 + offset - 1.0, kind=kind, strength=strength)


def test_grid_three_and_three():
    df = _df()
    step = slot_step(df)
    zones = []
    for sign in (1, -1):
        for k in range(1, 5):
            zones.append(_z(sign * (step * k + 5.0)))
    grid = build_grid(zones, df)
    above = [z for z in grid if z.display_side == "ABOVE"]
    below = [z for z in grid if z.display_side == "BELOW"]
    assert len(above) == config.ZONES_PER_SIDE
    assert len(below) == config.ZONES_PER_SIDE
    assert len(grid) == 6


def test_grid_slot_distances_reasonable():
    df = _df()
    step = slot_step(df)
    zones = [_z(s * (step * k + 5.0)) for s in (1, -1) for k in range(1, 5)]
    grid = build_grid(zones, df)
    for side in ("ABOVE", "BELOW"):
        dists = sorted(abs(z.price - 4400.0) for z in grid if z.display_side == side)
        assert dists[0] >= step * 0.5                    # первая зона не липнет к цене
        gaps = [b - a for a, b in zip(dists, dists[1:])]
        assert all(g >= step * 0.5 for g in gaps)        # зоны не слипаются


def test_stronger_zone_wins_inside_slot():
    df = _df()
    step = slot_step(df)
    weak = _z(step + 5.0, strength=5.0)
    strong = _z(step + 8.0, strength=20.0)
    grid = build_grid([weak, strong] + [_z(s * (step * k + 20.0)) for s in (1, -1) for k in range(2, 5)], df)
    above = [z for z in grid if z.display_side == "ABOVE"]
    assert strong in above
    assert weak not in above


def test_empty_side_does_not_steal_slots():
    df = _df()
    step = slot_step(df)
    zones = [_z(step * k + 5.0) for k in range(1, 5)]  # только сверху
    grid = build_grid(zones, df)
    assert all(z.display_side == "ABOVE" for z in grid)
    assert len(grid) <= 3                                # низ не выдумывается и не ворует


def test_lifecycle_test_decays_freshness():
    z = _z(-20.0)
    bars = pd.DataFrame(
        [("2026-01-09 00:00", 4400.0, 4401.0, 4379.5, 4390.0, 100.0)],  # тень коснулась зоны
        columns=["time", "open", "high", "low", "close", "tick_volume"])
    [z2] = apply_lifecycle([z], bars)
    assert z2.state == "TESTED"
    assert z2.test_count == 1
    assert z2.freshness == config.FRESHNESS_TEST_DECAY


def test_lifecycle_body_break_invalidates():
    z = _z(-20.0)  # зона 4379..4381
    bars = pd.DataFrame(
        [("2026-01-09 00:00", 4400.0, 4401.0, 4375.0, 4376.0, 100.0)],  # тело прошло насквозь вниз
        columns=["time", "open", "high", "low", "close", "tick_volume"])
    alive = apply_lifecycle([z], bars)
    assert alive == []


def test_wick_pierce_is_not_invalidation():
    z = _z(-20.0)
    bars = pd.DataFrame(
        [("2026-01-09 00:00", 4400.0, 4401.0, 4370.0, 4395.0, 100.0)],  # прокол тенью, закрытие выше зоны
        columns=["time", "open", "high", "low", "close", "tick_volume"])
    [z2] = apply_lifecycle([z], bars)
    assert z2.state != "INVALIDATED"


def test_snapshot_roundtrip_and_update_gate(tmp_path):
    df = _df()
    snap_path = tmp_path / "state.json"
    zones = [_z(20.0)]
    save_snapshot(zones, "2026-01-08 29:00", snap_path)
    snap = load_snapshot(snap_path)
    assert snap["zone_count"] == 1
    assert should_update(snap, df) is False                    # та же свеча — не пересчитываем
    df2 = _df()
    df2.loc[len(df2)] = ["2026-01-08 30:00", 4400, 4402, 4398, 4401, 100.0]
    assert should_update(snap, df2) is True                    # новая свеча — пересчёт
