"""Все параметры движка. Каждый переопределяется через переменные окружения."""
import os


def _env_str(name: str, default: str) -> str:
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# ── Инструмент ──────────────────────────────────────────────────────────────
SYMBOL = _env_str("SZNG_SYMBOL", "XAUUSD")
PIP_SIZE = _env_float("PIP_SIZE", 0.1)          # $ в одном пипсе клиентского терминала

# Веса таймфреймов: зона, подтверждённая на D1, структурно сильнее H1
TIMEFRAME_WEIGHTS = {"H1": 1.0, "H4": 2.0, "D1": 3.0}
PRIMARY_TF = "H4"
ATR_PERIOD = _env_int("ATR_PERIOD", 14)

# ── Импульсные свечи (displacement) ─────────────────────────────────────────
# Импульс — тело свечи заметно больше ATR и закрытие в крайней части диапазона.
IMPULSE_BODY_ATR = _env_float("IMPULSE_BODY_ATR", 1.2)
IMPULSE_CLOSE_POS = _env_float("IMPULSE_CLOSE_POS", 0.65)
# Order block: ищем противоположную свечу-источник в этой глубине перед импульсом
OB_SEARCH_BACK = _env_int("OB_SEARCH_BACK", 3)
# Сколько баров меряем ход после импульса (сила смещения)
OB_MOVE_BARS = _env_int("OB_MOVE_BARS", 12)

# ── Wick-кластеры (наследие SZP, как запасной детектор) ─────────────────────
WICK_CLUSTER_TOL_ATR = _env_float("WICK_CLUSTER_TOL_ATR", 0.35)
WICK_MIN_TOUCHES = _env_int("WICK_MIN_TOUCHES", 2)

# ── Sweep ликвидности ────────────────────────────────────────────────────────
# Равные экстремумы считаются равными в пределах этой доли ATR
SWEEP_EQUAL_TOL_ATR = _env_float("SWEEP_EQUAL_TOL_ATR", 0.15)
SWEEP_LOOKBACK = _env_int("SWEEP_LOOKBACK", 20)

# ── Volume-at-price профиль ─────────────────────────────────────────────────
PROFILE_BINS = _env_int("PROFILE_BINS", 120)
HVN_RATIO = _env_float("HVN_RATIO", 1.5)        # объём выше среднего ×1.5 — узел
LVN_RATIO = _env_float("LVN_RATIO", 0.5)        # ниже ×0.5 — пустота

# ── Память реакций ───────────────────────────────────────────────────────────
REACTION_LOOKAHEAD = _env_int("REACTION_LOOKAHEAD", 6)   # баров на отскок после касания
MIN_REACTION_ATR = _env_float("MIN_REACTION_ATR", 0.5)   # отскок меньше — не реакция

# ── Веса strength ────────────────────────────────────────────────────────────
W_IMPULSE = _env_float("W_IMPULSE", 3.0)        # за каждый ATR тела импульса
W_MOVE = _env_float("W_MOVE", 2.0)              # за каждый ATR хода после импульса
W_PROFILE = _env_float("W_PROFILE", 2.0)        # бонус HVN / штраф LVN
W_FVG = _env_float("W_FVG", 1.5)
W_SWEEP = _env_float("W_SWEEP", 1.5)
W_WICK_TOUCH = _env_float("W_WICK_TOUCH", 1.0)  # за касание в кластере
W_REACTION = _env_float("W_REACTION", 0.5)      # за каждую доказанную реакцию

# ── Адаптивная сетка ─────────────────────────────────────────────────────────
ZONES_PER_SIDE = _env_int("ZONES_PER_SIDE", 3)
GRID_SLOT_MIN_ATR = _env_float("GRID_SLOT_MIN_ATR", 1.5)
GRID_SLOT_MAX_ATR = _env_float("GRID_SLOT_MAX_ATR", 3.0)
GRID_MIN_DIST = _env_float("GRID_MIN_DIST", 15.0)    # $ — ближе зона липнет к цене
GRID_MAX_DIST = _env_float("GRID_MAX_DIST", 45.0)    # $ — дальше уровень за горизонтом
GRID_TOLERANCE = _env_float("GRID_TOLERANCE", 0.30)  # допуск окна слота

# ── Жизненный цикл ───────────────────────────────────────────────────────────
FRESHNESS_TEST_DECAY = _env_float("FRESHNESS_TEST_DECAY", 0.8)
FRESHNESS_MIN = _env_float("FRESHNESS_MIN", 0.15)
SNAPSHOT_VERSION = "1.0"

# ── Бэктест ──────────────────────────────────────────────────────────────────
BT_WARMUP = _env_int("BT_WARMUP", 120)
BT_STEP = _env_int("BT_STEP", 4)
BT_LOOKAHEAD = _env_int("BT_LOOKAHEAD", 24)
BT_MIN_REACTION = _env_float("BT_MIN_REACTION", 5.0)   # $ отскок, чтобы засчитать реакцию
