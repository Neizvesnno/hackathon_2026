"""core/match.py — R2 · алгоритм підбору.

Порівнює палітру стіни з палітрами картин (CIEDE2000, зважено частками кольорів)
і повертає топ-N картин з розкладом оцінки на складові.

Сигнатури та назви колонок — за CONTRACT.md, не змінювати.

Формула рейтингу (усі складові в 0…1, ваги видимі):

    score = (w_color * score_color + w_genre * score_genre
             + w_century * score_century + w_fame * score_fame)
            / (w_color + w_genre + w_century + w_fame)

    w_color, w_genre, w_century  — з параметра `weights` (за замовчуванням 1 / 0 / 0)
    w_fame = |fame| * weights["fame"]   (необов'язковий ключ, за замовчуванням 0.5)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Константи
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS = {"color": 1.0, "genre": 0.0, "century": 0.0, "fame": 0.5}

# Масштаб переходу «відстань ΔE00 -> оцінка 0…1»: score_color = exp(-d / COLOR_SCALE).
# d = 0 -> 1.0; d = 20 -> 0.37; d = 40 -> 0.14.
COLOR_SCALE = 20.0

# Внесок рівня відомості художника з fame_tier (решта — з artist_sitelinks).
_TIER_VALUE = {"famous": 1.0, "known": 2 / 3, "lesser": 1 / 3, "obscure": 0.0}
_TIER_SHARE = 0.5

_MODES = ("harmony", "accent")


# ---------------------------------------------------------------------------
# CIEDE2000 (векторизована, numpy)
# ---------------------------------------------------------------------------

def _ciede2000(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    """CIEDE2000 між масивами Lab формою (..., 3); працює з broadcasting."""
    L1, a1, b1 = lab1[..., 0], lab1[..., 1], lab1[..., 2]
    L2, a2, b2 = lab2[..., 0], lab2[..., 1], lab2[..., 2]

    C1 = np.hypot(a1, b1)
    C2 = np.hypot(a2, b2)
    C_bar7 = ((C1 + C2) / 2.0) ** 7
    G = 0.5 * (1.0 - np.sqrt(C_bar7 / (C_bar7 + 25.0 ** 7)))

    a1p = (1.0 + G) * a1
    a2p = (1.0 + G) * a2
    C1p = np.hypot(a1p, b1)
    C2p = np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360.0
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360.0

    dLp = L2 - L1
    dCp = C2p - C1p

    CC = C1p * C2p
    zero = CC == 0.0
    dh = h2p - h1p
    dh = np.where(dh > 180.0, dh - 360.0, dh)
    dh = np.where(dh < -180.0, dh + 360.0, dh)
    dh = np.where(zero, 0.0, dh)
    dHp = 2.0 * np.sqrt(CC) * np.sin(np.radians(dh) / 2.0)

    L_bar = (L1 + L2) / 2.0
    C_barp = (C1p + C2p) / 2.0
    h_sum = h1p + h2p
    h_bar = np.where(
        np.abs(h1p - h2p) <= 180.0,
        h_sum / 2.0,
        np.where(h_sum < 360.0, (h_sum + 360.0) / 2.0, (h_sum - 360.0) / 2.0),
    )
    h_bar = np.where(zero, h_sum, h_bar)

    T = (
        1.0
        - 0.17 * np.cos(np.radians(h_bar - 30.0))
        + 0.24 * np.cos(np.radians(2.0 * h_bar))
        + 0.32 * np.cos(np.radians(3.0 * h_bar + 6.0))
        - 0.20 * np.cos(np.radians(4.0 * h_bar - 63.0))
    )
    d_theta = 30.0 * np.exp(-(((h_bar - 275.0) / 25.0) ** 2))
    C_barp7 = C_barp ** 7
    Rc = 2.0 * np.sqrt(C_barp7 / (C_barp7 + 25.0 ** 7))
    Sl = 1.0 + 0.015 * (L_bar - 50.0) ** 2 / np.sqrt(20.0 + (L_bar - 50.0) ** 2)
    Sc = 1.0 + 0.045 * C_barp
    Sh = 1.0 + 0.015 * C_barp * T
    Rt = -np.sin(np.radians(2.0 * d_theta)) * Rc

    dL = dLp / Sl
    dC = dCp / Sc
    dH = dHp / Sh
    return np.sqrt(np.maximum(dL ** 2 + dC ** 2 + dH ** 2 + Rt * dC * dH, 0.0))


# ---------------------------------------------------------------------------
# Відстань між палітрами
# ---------------------------------------------------------------------------

def _normalize_shares(w: np.ndarray) -> np.ndarray:
    """Частки -> сума 1 (по останній осі). Нульова сума -> рівні частки."""
    w = np.clip(w, 0.0, None)
    s = w.sum(axis=-1, keepdims=True)
    k = w.shape[-1]
    return np.where(s > 0, w / np.where(s > 0, s, 1.0), 1.0 / k)


def _palette_distances(wall: np.ndarray, pals: np.ndarray) -> np.ndarray:
    """Відстані між однією палітрою стіни (kw, 4) і N палітрами (N, kp, 4) -> (N,).

    Для кожного кольору береться ΔE00 до найближчого кольору іншої палітри,
    результат усереднюється за частками — в обидва боки (симетрично):

        d = 0.5 * ( Σ_i w_wall_i * min_j ΔE(i, j)  +  Σ_j w_paint_j * min_i ΔE(i, j) )
    """
    wall_lab = wall[:, :3]
    wall_w = _normalize_shares(wall[:, 3])                # (kw,)
    pal_lab = pals[:, :, :3]
    pal_w = _normalize_shares(pals[:, :, 3])              # (N, kp)

    # (N, kw, kp)
    de = _ciede2000(wall_lab[None, :, None, :], pal_lab[:, None, :, :])

    wall_to_paint = (de.min(axis=2) * wall_w[None, :]).sum(axis=1)   # (N,)
    paint_to_wall = (de.min(axis=1) * pal_w).sum(axis=1)             # (N,)
    return 0.5 * (wall_to_paint + paint_to_wall)


def palette_distance(wall: np.ndarray, painting: np.ndarray) -> float:
    """CIEDE2000 між палітрами (k, 4) = [L, a, b, частка], зважено частками.

    Менше = схожіше. 0 для однакових палітр.
    """
    wall = np.asarray(wall, dtype=float)
    painting = np.asarray(painting, dtype=float)
    return float(_palette_distances(wall, painting[None, :, :])[0])


# ---------------------------------------------------------------------------
# Допоміжне для recommend
# ---------------------------------------------------------------------------

def _palettes_from_df(df: pd.DataFrame) -> np.ndarray:
    """Колонки pal_L_i / pal_a_i / pal_b_i / pal_w_i -> масив (N, k, 4)."""
    k = 0
    while f"pal_L_{k + 1}" in df.columns:
        k += 1
    if k == 0:
        raise KeyError("У df немає колонок pal_L_1 … (очікується features.parquet)")
    cols = []
    for i in range(1, k + 1):
        cols.append(
            np.stack(
                [df[f"pal_L_{i}"].to_numpy(float), df[f"pal_a_{i}"].to_numpy(float),
                 df[f"pal_b_{i}"].to_numpy(float), df[f"pal_w_{i}"].to_numpy(float)],
                axis=1,
            )
        )
    return np.stack(cols, axis=1)  # (N, k, 4)


def _accent_target(wall: np.ndarray) -> np.ndarray:
    """Комплементарна палітра: a, b -> -a, -b (поворот відтінку на 180°), L і частки ті самі."""
    target = wall.copy()
    target[:, 1] = -wall[:, 1]
    target[:, 2] = -wall[:, 2]
    return target


def _fame_level(df: pd.DataFrame) -> np.ndarray:
    """Рівень відомості художника 0…1: суміш fame_tier і log(artist_sitelinks)."""
    tier = df["fame_tier"].map(_TIER_VALUE).fillna(_TIER_VALUE["lesser"]).to_numpy(float)
    sl = np.log1p(df["artist_sitelinks"].fillna(0).to_numpy(float))
    smax = sl.max() if len(sl) else 0.0
    sl = sl / smax if smax > 0 else np.zeros_like(sl)
    return _TIER_SHARE * tier + (1.0 - _TIER_SHARE) * sl


def _century_score(centuries_col: np.ndarray, wanted: list[int] | None) -> np.ndarray:
    """1 для бажаного століття, далі 1/(1+відстань у століттях до найближчого бажаного)."""
    if not wanted:
        return np.ones(len(centuries_col))
    wanted_arr = np.asarray(list(wanted), dtype=float)
    dist = np.abs(centuries_col[:, None] - wanted_arr[None, :]).min(axis=1)
    return 1.0 / (1.0 + dist)


def _genre_score(genre_col: pd.Series, wanted: list[str] | None) -> np.ndarray:
    """1, якщо genre_main серед бажаних, інакше 0. Без вибору — 1 для всіх."""
    if not wanted:
        return np.ones(len(genre_col))
    return genre_col.isin(list(wanted)).to_numpy(float)


# ---------------------------------------------------------------------------
# Головна функція
# ---------------------------------------------------------------------------

def recommend(
    wall: np.ndarray,
    df: pd.DataFrame,
    mode: str = "harmony",
    weights: dict | None = None,
    fame: float = 0.0,
    genres: list[str] | None = None,
    centuries: list[int] | None = None,
    top_k: int = 12,
) -> pd.DataFrame:
    """Топ-`top_k` картин для палітри стіни.

    mode     "harmony" — схожі кольори; "accent" — комплементарні (a, b -> -a, -b).
    weights  {"color", "genre", "century"[, "fame"]}; відсутні ключі беруться за замовчуванням,
             від'ємні ваги вважаються нулем.
    fame     -1 = відкриття (маловідомі) … +1 = відомі; 0 — відомість не впливає.
    genres   бажані genre_main; None/[] = будь-які. Впливає лише з weights["genre"] > 0.
    centuries бажані століття; None/[] = будь-які; сусідні століття дають часткову оцінку.
             Впливає лише з weights["century"] > 0.

    Повертає top_k рядків df (усі колонки) + score, score_color, score_genre,
    score_century, score_fame (кожна 0…1), відсортовано за score спаданням.
    """
    if mode not in _MODES:
        raise ValueError(f"mode має бути одним із {_MODES}, отримано {mode!r}")

    wall = np.asarray(wall, dtype=float)
    if wall.ndim != 2 or wall.shape[1] != 4:
        raise ValueError("wall має мати форму (k, 4): [L, a, b, частка]")

    w = dict(DEFAULT_WEIGHTS)
    if weights:
        w.update({k: float(v) for k, v in weights.items() if v is not None})
    w = {k: max(v, 0.0) for k, v in w.items()}
    fame = float(np.clip(fame, -1.0, 1.0))

    if len(df) == 0:
        out = df.copy()
        for c in ("score", "score_color", "score_genre", "score_century", "score_fame"):
            out[c] = pd.Series(dtype=float)
        return out

    # --- колір ---
    target = _accent_target(wall) if mode == "accent" else wall
    dist = _palette_distances(target, _palettes_from_df(df))
    score_color = np.exp(-dist / COLOR_SCALE)

    # --- жанр, століття ---
    score_genre = _genre_score(df["genre_main"], genres)
    score_century = _century_score(df["century"].to_numpy(float), centuries)

    # --- відомість: 0.5 + fame * (рівень - 0.5); при fame=0 однакова для всіх ---
    score_fame = 0.5 + fame * (_fame_level(df) - 0.5)

    # --- підсумок ---
    w_color, w_genre, w_century = w["color"], w["genre"], w["century"]
    w_fame = abs(fame) * w["fame"]
    total_w = w_color + w_genre + w_century + w_fame
    if total_w <= 0:                       # усі ваги нульові -> лише колір
        w_color, total_w = 1.0, 1.0
    score = (
        w_color * score_color + w_genre * score_genre
        + w_century * score_century + w_fame * score_fame
    ) / total_w

    # --- топ-k (стабільно: при рівності — за кольором, потім за порядком у df) ---
    order = np.lexsort((np.arange(len(df)), -score_color, -score))[: max(int(top_k), 0)]
    out = df.iloc[order].copy()
    out["score"] = score[order]
    out["score_color"] = score_color[order]
    out["score_genre"] = score_genre[order]
    out["score_century"] = score_century[order]
    out["score_fame"] = score_fame[order]
    return out.reset_index(drop=True)