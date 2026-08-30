"""Скоринг: strength (как родилась) + confirmation (жива ли сейчас).

strength считается один раз при рождении зоны из фактов:
  сила импульса, ход после него, профиль объёма, confluence с FVG/sweep,
  число касаний, число доказанных реакций.
confirmation собирается из профиля и памяти реакций.
freshness меняет только lifecycle — здесь не трогаем.
"""
from __future__ import annotations

import pandas as pd

from . import config
from .models import Zone
from .profile import build_profile, node_type
from .reaction import (confirmation_from_profile, confirmation_from_reactions,
                       measure_reactions)


def score_zones(zones: list[Zone], df: pd.DataFrame) -> list[Zone]:
    if not zones:
        return []
    profile = build_profile(df)
    for z in zones:
        strength = 0.0
        if z.kind == "OB":
            strength += config.W_IMPULSE * float(z.meta.get("impulse_body_atr", 0.5))
            strength += config.W_MOVE * float(z.meta.get("move_after_atr", 0.0))
        elif z.kind == "WICK":
            strength += config.W_WICK_TOUCH * float(z.meta.get("touches", config.WICK_MIN_TOUCHES))
        elif z.kind == "SWEEP":
            strength += config.W_SWEEP
        elif z.kind == "FVG":
            strength += config.W_FVG * 0.5

        node = node_type(profile, z.price)
        if node == "HVN":
            strength += config.W_PROFILE
            z.confluences.append("hvn")
        elif node == "LVN":
            strength -= config.W_PROFILE
            z.confluences.append("lvn")

        reactions = measure_reactions(z, df)
        z.reactions = reactions
        strength += config.W_REACTION * len(reactions)

        tf_w = config.TIMEFRAME_WEIGHTS.get(z.tf, 1.0)
        z.strength = round(max(0.5, strength) * tf_w, 2)
        # Профиль — модификатор с половинным весом: LVN-штраф не должен
        # обнулять доказанные реакции, а HVN не должен заменять их.
        z.confirmation = round(min(1.0, max(0.0,
            0.5 + 0.5 * confirmation_from_profile(node)
                + (confirmation_from_reactions(reactions) - 0.5))), 3)
    return zones
