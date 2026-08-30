import pandas as pd

from szng.models import Zone
from szng.reaction import measure_reactions
from szng.scoring import score_zones


def _reaction_df():
    """Цена дважды касается 4400 и оба раза отскакивает вверх на ~8$."""
    rows = []
    for i in range(10):
        rows.append((f"2026-01-07 {i:02d}:00", 4410.0, 4411.0, 4408.0, 4410.0, 50.0))
    rows.append(("2026-01-07 10:00", 4410.0, 4411.0, 4399.5, 4409.0, 80.0))  # касание 1
    for i in range(11, 17):
        rows.append((f"2026-01-07 {i:02d}:00", 4409.0, 4418.0, 4408.0, 4417.0, 60.0))
    for i in range(17, 24):
        rows.append((f"2026-01-07 {i:02d}:00", 4412.0, 4413.0, 4410.0, 4411.0, 50.0))
    rows.append(("2026-01-07 24:00", 4411.0, 4412.0, 4399.6, 4410.0, 80.0))  # касание 2
    for i in range(25, 32):
        rows.append((f"2026-01-07 {i:02d}:00", 4410.0, 4419.0, 4409.0, 4418.0, 60.0))
    return pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "tick_volume"])


def test_reactions_measured():
    df = _reaction_df()
    z = Zone(price=4400.0, top=4401.0, bottom=4399.0, kind="OB",
             meta={"direction": "bullish"})
    reactions = measure_reactions(z, df)
    assert len(reactions) >= 2
    assert all(r["bounce"] > 3.0 for r in reactions)


def test_reactions_boost_confirmation():
    df = _reaction_df()
    z = Zone(price=4400.0, top=4401.0, bottom=4399.0, kind="OB",
             meta={"direction": "bullish"})
    [z2] = score_zones([z], df)
    assert z2.confirmation > 0.5
    assert z2.strength > 0.5
    assert len(z2.reactions) >= 2


def test_final_score_combines_dimensions():
    z = Zone(price=100.0, top=101.0, bottom=99.0, kind="OB",
             strength=10.0, freshness=0.5, confirmation=1.0)
    assert z.final_score() == 10.0 * 0.5 * 1.0


def test_json_roundtrip():
    z = Zone(price=4400.5, top=4401.5, bottom=4399.5, kind="OB", tf="H4",
             strength=8.25, freshness=0.8, confirmation=0.75,
             meta={"direction": "bullish"})
    z2 = Zone.from_dict(z.to_dict())
    assert z2.price == z.price and z2.kind == "OB"
    assert z2.strength == 8.25 and z2.freshness == 0.8
