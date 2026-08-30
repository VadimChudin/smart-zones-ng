# Smart Zones NG

Следующее поколение движка уровней для XAU/USD. Наследник Smart Zones Pro, но с другим ядром: зоны рождаются не из «теней подряд», а из **поведения цены** — импульсов, order blocks, sweep-ликвидности, незакрытых FVG и профиля объёма.

## Чем отличается от SZP

| | SZP (старый) | SZ-NG (этот движок) |
|---|---|---|
| Источник зон | кластеры фитилей | order blocks от импульсных свечей + wick-кластеры + sweep + FVG |
| Score | статичный, считается один раз | `strength × freshness × confirmation` — живой, обновляется |
| Тесты зоны | бинарно: пробили — убить | каждое касание «съедает» зону (freshness decay), пробой телом H4 — инвалидация |
| Геометрия | фиксированная лестница 200–300 пипсов | ATR-адаптивная симметричная сетка (3+3), в боковике сжимается, в тренде расширяется |
| Объём | бонус к score | полноценный volume-at-price профиль: HVN усиливает зону, LVN — красный флаг |
| Память реакций | нет | для каждой зоны измеряется реальный отскок на каждом касании |
| Качество | на глаз | walk-forward бэктест с hit-rate по каждому типу зон |

## Архитектура

```
OHLCV (MT4/MT5/CSV)
   │
   ├── detectors.py      импульсы → order blocks, wick-кластеры, sweep, FVG
   ├── profile.py        volume-at-price профиль → HVN / LVN / POC
   ├── reaction.py       память реакций: реальный отскок на каждом касании
   ├── scoring.py        strength × freshness × confirmation → final_score
   ├── grid.py           ATR-адаптивная сетка: 3 слота выше + 3 ниже цены
   ├── lifecycle.py      снапшот меняется только на закрытии H4; касания и пробои
   ├── backtest.py       walk-forward: hit-rate, avg bounce, per-kind статистика
   └── export.py         zones_output.json (контракт совместим с SZP-индикаторами)
```

## Быстрый старт

```bash
pip install -r requirements.txt
pytest -q

# построить зоны из CSV (time,open,high,low,close,tick_volume)
python -m szng.pipeline data/XAUUSD_H4.csv --out zones_output.json --snapshot state.json

# walk-forward бэктест
python -m szng.backtest data/XAUUSD_H4.csv
```

## Модель зоны

Каждая зона — не число, а живой объект:

- **strength** — как рождена: сила импульса, размер хода после него, HVN, confluence с FVG/sweep, число касаний
- **freshness** — сколько жизни осталось: каждое касание умножает на 0.8 (лимитные ордера исполняются, зона «съедается»)
- **confirmation** — жива ли сейчас: профиль объёма на уровне + свежие реакции
- **final_score = strength × freshness × (0.5 + 0.5 × confirmation)**

Состояния: `FRESH → TESTED → INVALIDATED`. Инвалидация — только пробой телом H4, не прокол тенью.

## Сетка

Симметричная, 3 слота на сторону. Шаг слота — `1.5–3.0 × ATR(H4)` (зажато в $15–45): зона ищется там, где она есть, а не там, где хочет арифметика. Внутри слота побеждает `final_score`. Если слот пуст — окно следующего слота сдвигается номинально, сторона не залипает.

## JSON-контракт

`zones_output.json` совместим с индикаторами SZP (поля `price/top/bottom/width/score/sources/label`), плюс новые поля: `kind`, `strength`, `freshness`, `confirmation`, `state`, `test_count`, `reactions`, `confluences`.
