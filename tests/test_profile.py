import numpy as np
import pandas as pd

from szng import config
from szng.profile import build_profile, hvn_lvn, node_type, poc


def _profile_df():
    """Объём сосредоточен на 4400 (HVN), на 4450 почти пусто (LVN)."""
    rng = np.random.default_rng(1)
    rows = []
    for i in range(400):
        c = float(rng.normal(4400.0, 2.0))
        rows.append((f"2026-01-05 {i:02d}:00", c - 0.3, c + 0.4, c - 0.4, c, 100.0))
    for i in range(10):
        rows.append((f"2026-01-06 {i:02d}:00", 4449.7, 4450.3, 4449.7, 4450.0, 5.0))
    return pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "tick_volume"])


def test_hvn_lvn_classification():
    prof = build_profile(_profile_df())
    assert not prof.empty
    assert node_type(prof, 4400.0) == "HVN"
    assert node_type(prof, 4450.0) == "LVN"
    assert node_type(prof, 4415.0) in ("NORM", "LVN")


def test_poc_near_heavy_price():
    prof = build_profile(_profile_df())
    assert abs(poc(prof) - 4400.0) < 3.0


def test_empty_profile_safe():
    prof = build_profile(pd.DataFrame(columns=["time", "open", "high", "low", "close", "tick_volume"]))
    assert prof.empty
    assert node_type(prof, 100.0) == "NORM"
    assert poc(prof) is None
