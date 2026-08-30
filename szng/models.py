"""Модель зоны. Зона — живой объект, а не строка в списке.

Три независимых измерения (намеренно не сведены в одно число):
  strength     — как зона РОДИЛАСЬ (структурная значимость, не убывает от времени)
  freshness    — сколько жизни осталось (каждое касание съедает лимитные ордера)
  confirmation — жива ли зона СЕЙЧАС (профиль объёма, свежие реакции)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Zone:
    price: float                       # центр зоны
    top: float
    bottom: float
    kind: str                          # OB | WICK | SWEEP | FVG
    tf: str = "H4"
    born_at: str = ""
    strength: float = 0.0
    freshness: float = 1.0
    confirmation: float = 0.5
    state: str = "FRESH"               # FRESH | TESTED | INVALIDATED
    test_count: int = 0
    reactions: list = field(default_factory=list)   # [{time, bounce}]
    confluences: list = field(default_factory=list) # человекочитаемые причины
    display_side: str = ""             # ABOVE | BELOW (ставит grid)
    meta: dict = field(default_factory=dict)        # direction и прочее

    @property
    def width(self) -> float:
        return (self.top - self.bottom) / 2.0

    def final_score(self) -> float:
        """Единая метрика для сравнения внутри слота сетки."""
        return self.strength * self.freshness * (0.5 + 0.5 * self.confirmation)

    @property
    def label(self) -> str:
        return f"{self.price:.2f} | {self.kind} {self.tf} | S:{self.strength:.1f}"

    def to_dict(self) -> dict:
        return {
            "price": round(self.price, 2),
            "top": round(self.top, 2),
            "bottom": round(self.bottom, 2),
            "width": round(self.width, 2),
            "score": round(self.final_score(), 2),
            "kind": self.kind,
            "tf": self.tf,
            "sources": [self.tf],
            "label": self.label,
            "born_at": self.born_at,
            "strength": round(self.strength, 2),
            "freshness": round(self.freshness, 3),
            "confirmation": round(self.confirmation, 3),
            "state": self.state,
            "test_count": self.test_count,
            "reactions": self.reactions,
            "confluences": self.confluences,
            "display_side": self.display_side,
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Zone":
        return cls(
            price=float(d["price"]), top=float(d["top"]), bottom=float(d["bottom"]),
            kind=d.get("kind", "WICK"), tf=d.get("tf", "H4"),
            born_at=d.get("born_at", ""),
            strength=float(d.get("strength", d.get("score", 0.0))),
            freshness=float(d.get("freshness", 1.0)),
            confirmation=float(d.get("confirmation", 0.5)),
            state=d.get("state", "FRESH"),
            test_count=int(d.get("test_count", 0)),
            reactions=list(d.get("reactions", [])),
            confluences=list(d.get("confluences", [])),
            display_side=d.get("display_side", ""),
            meta=dict(d.get("meta", {})),
        )
