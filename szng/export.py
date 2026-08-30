"""Экспорт в zones_output.json. Контракт совместим с индикаторами SZP
(price/top/bottom/width/score/sources/label) + новые поля NG."""
from __future__ import annotations

import json
from pathlib import Path

from . import config
from .models import Zone


def export_json(zones: list[Zone], path: str | Path,
                current_price: float | None = None) -> dict:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone
    payload = {
        "version": config.SNAPSHOT_VERSION,
        "symbol": config.SYMBOL,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
        "current_price": current_price,
        "zone_count": len(zones),
        "zones": [z.to_dict() for z in zones],
    }
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)
    return payload
