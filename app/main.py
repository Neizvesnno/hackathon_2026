"""Streamlit-застосунок. Власник: R3 (Володимир). Запуск з кореня: streamlit run app/main.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # щоб працювало `from core ...`

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from ui_controls import render_controls  # noqa: E402  (app/ вже в sys.path — його додає streamlit)
from ui_extras import render_map, render_tryon  # noqa: E402
from ui_results import render_results  # noqa: E402
from ui_wall import render_wall  # noqa: E402
from core import config  # noqa: E402

st.set_page_config(page_title="Картина під стіну", page_icon="🖼️", layout="centered")
st.title("Картина під стіну")
st.caption("Сфотографуй стіну або вибери її кольори — підберемо картини з 10 000.")


@st.cache_data(show_spinner="Завантажуємо картини…")
def load_features(mtime: float) -> pd.DataFrame:
    """mtime у аргументах — щоб кеш оновився, коли R1 запушить новий файл."""
    return pd.read_parquet(config.FEATURES_PATH)


df = load_features(config.FEATURES_PATH.stat().st_mtime) if config.FEATURES_PATH.exists() else None

wall = render_wall()   # палітра стіни (k, 4) або None; також у st.session_state["wall_palette"]

st.divider()
if wall is None:
    st.info("Додай фото стіни або вибери кольори — і тут з'являться картини.")
else:
    params = render_controls(df)   # kwargs для recommend(wall, df, **params)

    st.divider()
    tab_art, tab_tryon, tab_map = st.tabs(["Картини", "Примірка", "Мапа"])
    with tab_art:
        results = render_results(wall, df, params)   # топ-12; також у st.session_state["results"]
    with tab_tryon:
        render_tryon(results)
    with tab_map:
        render_map(df, results)
