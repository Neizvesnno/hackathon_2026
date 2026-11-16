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

MOOD_PATH = config.APP_DATA / "mood_tags.parquet"


@st.cache_data(show_spinner=False)
def load_moods(mtime: float) -> pd.DataFrame:
    """Теги настрою від R1 (CLIP, пораховані заздалегідь): painting_id, mood_1, mood_2."""
    return pd.read_parquet(MOOD_PATH, columns=["painting_id", "mood_1", "mood_2"])


if df is not None and MOOD_PATH.exists():
    try:
        df = df.merge(load_moods(MOOD_PATH.stat().st_mtime), on="painting_id", how="left")
    except Exception:   # без настроїв застосунок працює як раніше
        pass

wall = render_wall()   # палітра стіни (k, 4) або None; також у st.session_state["wall_palette"]

st.divider()
if wall is None:
    st.info("Додай фото стіни або вибери кольори — і тут з'являться картини.")
else:
    params = render_controls(df)   # kwargs для recommend(wall, df, **params)

    df_rec = df   # картини, серед яких шукаємо; мапа далі показує всі
    if df is not None and "mood_1" in df.columns:
        moods = st.multiselect(
            "Настрій", sorted(df["mood_1"].dropna().unique()), key="ctl_moods", placeholder="Будь-який",
            help="Настрій картини визначено моделлю CLIP.",
        )
        if moods:
            picked = df[df["mood_1"].isin(moods) | df["mood_2"].isin(moods)]
            if len(picked):
                df_rec = picked

    st.divider()
    tab_art, tab_tryon, tab_map = st.tabs(["Картини", "Примірка", "Мапа"])
    with tab_art:
        results = render_results(wall, df_rec, params)   # топ-12; також у st.session_state["results"]
    with tab_tryon:
        render_tryon(results)
    with tab_map:
        render_map(df, results)
