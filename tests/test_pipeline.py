import json

from szng.backtest import run_backtest
from szng.data import synthetic
from szng.export import export_json
from szng.pipeline import run


def test_pipeline_end_to_end(tmp_path):
    df = synthetic(n=500, seed=3)
    snap = tmp_path / "state.json"
    out = tmp_path / "zones.json"
    grid = run(df, str(snap))
    assert grid, "сетка пустая на синтетике"
    assert all(z.state != "INVALIDATED" for z in grid)
    assert all(z.final_score() > 0 for z in grid)
    payload = export_json(grid, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["zone_count"] == payload["zone_count"] == len(grid)
    assert data["zones"][0]["price"]
    # SZP-совместимые поля
    for key in ("price", "top", "bottom", "width", "score", "label"):
        assert key in data["zones"][0]
    # NG-поля
    for key in ("kind", "strength", "freshness", "confirmation"):
        assert key in data["zones"][0]


def test_pipeline_idempotent_on_same_bar(tmp_path):
    df = synthetic(n=300, seed=5)
    snap = tmp_path / "state.json"
    first = run(df, str(snap))
    second = run(df, str(snap))
    assert [z.price for z in first] == [z.price for z in second]


def test_backtest_produces_report():
    df = synthetic(n=400, seed=11)
    report = run_backtest(df)
    assert report["zones"] > 0
    assert 0.0 <= report["hit_rate"] <= 1.0
    assert "by_kind" in report and "by_side" in report


def test_synthetic_levels_get_found():
    """Синтетика зашивает уровни через mean-reversion — детекторы обязаны их находить."""
    from szng.detectors import detect_all
    from szng.scoring import score_zones
    df = synthetic(n=500, seed=3)
    zones = score_zones(detect_all(df), df)
    known = [4315.0, 4345.0, 4375.0, 4425.0, 4455.0, 4485.0]
    hits = sum(1 for lv in known if any(abs(z.price - lv) < 6.0 for z in zones))
    assert hits >= 2, f"движок нашёл только {hits}/6 зашитых уровней"
