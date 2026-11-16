"""Налаштування підбору: режим, ваги, «відомі ↔ відкриття», фільтри. Власник: R3 (Володимир).

render_controls(df) повертає dict, який напряму йде в recommend():
    recommend(wall, df, **params)
Ключі — як у CONTRACT.md: mode, weights, fame, genres, centuries.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import config

PARAMS_KEY = "rec_params"   # ключ у st.session_state
MODES = {"Гармонія": "harmony", "Акцент": "accent"}
MODE_HELP = "Гармонія — картини в кольорах стіни. Акцент — у протилежних (комплементарних) кольорах."
DEFAULT_WEIGHTS = {"color": 1.0, "genre": 0.5, "century": 0.5}
FALLBACK_CENTURIES = list(range(13, 22))
MAX_GENRES = 30


def _roman(n: int) -> str:
    out = ""
    for val, sym in ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= val:
            out, n = out + sym, n - val
    return out


@st.cache_data(show_spinner=False)
def _fallback_genres() -> list[str]:
    """Поки немає features.parquet — найчастіші жанри з довідника data/genres.csv."""
    try:
        g = pd.read_csv(config.GENRES_CSV).sort_values("n_paintings", ascending=False)
        labels = g["label_uk"].fillna(g["label_en"]).dropna()
        return list(dict.fromkeys(labels))[:MAX_GENRES]
    except Exception:
        return []


def genre_options(df: pd.DataFrame | None) -> list[str]:
    """Жанри для фільтра, від найчастішого. «інше» — в кінці."""
    if df is not None and "genre_main" in df.columns:
        opts = [g for g in df["genre_main"].value_counts().index if g != "інше"][:MAX_GENRES]
    else:
        opts = _fallback_genres()
    return opts + ["інше"]


def century_options(df: pd.DataFrame | None) -> list[int]:
    if df is not None and "century" in df.columns:
        return sorted(int(c) for c in df["century"].dropna().unique())
    return FALLBACK_CENTURIES


def render_controls(df: pd.DataFrame | None = None) -> dict:
    """Малює налаштування, повертає kwargs для recommend()."""
    st.subheader("2. Що шукаємо")
    mode_label = st.radio(
        "Режим", list(MODES), horizontal=True, key="ctl_mode",
        label_visibility="collapsed", help=MODE_HELP,
    )

    with st.expander("Налаштування і фільтри"):
        fame = st.slider(
            "Відкриття ↔ відомі", -1.0, 1.0, 0.0, 0.1, key="ctl_fame",
            help="Ліворуч — маловідомі художники вище, праворуч — знамениті. Посередині — байдуже.",
        )
        genres = st.multiselect(
            "Жанр", genre_options(df), key="ctl_genres", placeholder="Будь-який",
        )
        centuries = st.multiselect(
            "Століття", century_options(df), format_func=_roman, key="ctl_centuries",
            placeholder="Будь-яке",
        )
        st.caption("Що важливіше")
        weights = {
            "color": st.slider("Колір", 0.0, 1.0, DEFAULT_WEIGHTS["color"], 0.05, key="ctl_w_color"),
            "genre": st.slider("Жанр", 0.0, 1.0, DEFAULT_WEIGHTS["genre"], 0.05, key="ctl_w_genre"),
            "century": st.slider("Століття", 0.0, 1.0, DEFAULT_WEIGHTS["century"], 0.05, key="ctl_w_century"),
        }
        if sum(weights.values()) == 0:
            st.caption("Усі ваги на нулі — рахуємо лише за кольором.")
            weights["color"] = 1.0

    params = {
        "mode": MODES[mode_label],
        "weights": weights,
        "fame": float(fame),
        "genres": list(genres) or None,
        "centuries": [int(c) for c in centuries] or None,
    }
    st.session_state[PARAMS_KEY] = params
    return params
