"""Streamlit-застосунок. Власник: R3 (Володимир). Запуск з кореня: streamlit run app/main.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # щоб працювало `from core ...`

import streamlit as st  # noqa: E402

from core import config  # noqa: E402

st.set_page_config(page_title="Картина під стіну", page_icon="🖼️", layout="centered")
st.title("Картина під стіну")
st.caption("Каркас працює. Тут буде інтерфейс R3.")
st.write("features.parquet:", "є" if config.FEATURES_PATH.exists() else "ще немає (чекаємо R1)")
