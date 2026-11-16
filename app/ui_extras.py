"""Вкладки «Мапа» і «Примірка». Власник: R3 (Володимир).

Логіка — у файлах Максима (analysis/art_map.py, core/tryon.py); тут лише виклики.
Кожна вкладка загорнута в try/except: якщо щось зламається, решта застосунку працює далі.
"""
from __future__ import annotations

import io
import urllib.request

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps

from core import config

ROOM_MAX_PX = 1000   # фото кімнати зменшуємо, щоб примірка рахувалась миттєво


# ---------- мапа ----------

@st.cache_data(show_spinner=False)
def _load_coords(mtime: float) -> pd.DataFrame:
    return pd.read_parquet(config.MAP_COORDS_PATH)


@st.cache_data(show_spinner="Малюємо мапу…")
def _map_figure(highlight_ids: tuple, coords_mtime: float, _df: pd.DataFrame, _coords: pd.DataFrame):
    """Фігура на 10 000 точок будується кілька секунд — кешуємо за набором підсвічених картин."""
    from analysis.art_map import art_map_figure

    return art_map_figure(_df, _coords, list(highlight_ids))


def render_map(df: pd.DataFrame | None, results: pd.DataFrame | None) -> None:
    if df is None or "pal_L_1" not in df.columns or not config.MAP_COORDS_PATH.exists():
        st.info("Мапа з'явиться, коли будуть готові дані (features.parquet і map_coords.parquet).")
        return
    try:
        mtime = config.MAP_COORDS_PATH.stat().st_mtime
        coords = _load_coords(mtime)
        ids = tuple(results["painting_id"].astype(str)) if results is not None and len(results) else ()
        fig = _map_figure(ids, mtime, df, coords)
        st.caption("Кожна точка — картина у своєму головному кольорі. Великі точки з обводкою — підібрані для твоєї стіни.")
        st.plotly_chart(fig, key="art_map")
    except Exception as e:   # не валимо весь застосунок через мапу
        st.warning(f"Мапу зараз не вдалося показати ({type(e).__name__}).")


# ---------- примірка ----------

@st.cache_data(show_spinner=False, max_entries=64)
def _fetch_image(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "art-wall-hackathon"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()


def _open_room(data: bytes) -> Image.Image:
    room = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    room.thumbnail((ROOM_MAX_PX, ROOM_MAX_PX))
    return room


def painting_label(row) -> str:
    artist = row.get("artist_name")
    title = row.get("title") or "Без назви"
    return f"{title} — {artist}" if isinstance(artist, str) and artist else str(title)


def render_tryon(results: pd.DataFrame | None) -> None:
    if results is None or len(results) == 0:
        st.info("Спершу підбери картини — тоді їх можна буде приміряти.")
        return
    try:
        room_bytes = st.session_state.get("wall_photo_bytes")
        if st.session_state.get("wall_source") != "Фото":
            room_bytes = None   # стіну задано кольорами — старе фото не підставляємо
        if room_bytes is None:
            up = st.file_uploader("Фото кімнати для примірки", type=["jpg", "jpeg", "png", "webp"], key="tryon_room")
            if up is None:
                st.caption("Додай фото кімнати — і побачиш картину на своїй стіні.")
                return
            room_bytes = up.getvalue()

        rows = results.reset_index(drop=True)
        idx = st.selectbox(
            "Картина", range(len(rows)), format_func=lambda i: painting_label(rows.iloc[i]), key="tryon_pick",
        )
        c1, c2 = st.columns(2)
        cx = c1.slider("Ліворуч ↔ праворуч", 0.0, 1.0, 0.5, 0.01, key="tryon_cx")
        cy = c2.slider("Вище ↔ нижче", 0.0, 1.0, 0.4, 0.01, key="tryon_cy")
        width = st.slider("Розмір картини", 0.1, 0.8, 0.35, 0.01, key="tryon_w")

        from core.tryon import overlay

        painting = Image.open(io.BytesIO(_fetch_image(str(rows.iloc[idx]["image_url"]))))
        st.image(overlay(_open_room(room_bytes), painting, cx=cx, cy=cy, width=width))
        attr = rows.iloc[idx].get("attribution")
        if isinstance(attr, str) and attr:
            st.caption(f"{painting_label(rows.iloc[idx])} · {attr} · {rows.iloc[idx].get('license') or ''}")
    except Exception as e:   # не валимо весь застосунок через примірку
        st.warning(f"Примірку зараз не вдалося показати ({type(e).__name__}).")
