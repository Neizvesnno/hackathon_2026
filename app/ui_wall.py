"""Екран «Стіна»: фото або вибір кольорів -> палітра стіни (k, 4) + плашки. Власник: R3 (Володимир).

Палітра — у форматі з CONTRACT.md: np.ndarray (k, 4), рядок = [L, a, b, частка], CIELAB (D65),
частки в сумі = 1, від більшої до меншої. Результат лежить у st.session_state["wall_palette"].
"""
from __future__ import annotations

import io

import numpy as np
import streamlit as st
from PIL import Image, ImageOps

from core import config
from core import palette as core_palette

WALL_KEY = "wall_palette"   # ключ у st.session_state — його читають інші екрани
ANALYSIS_PX = 400           # фото стіни зменшуємо перед аналізом
PICKER_DEFAULTS = ("#E8E2D6", "#8A9A8B", "#3B3F45")
PICKER_LABELS = ("Основний", "Другий", "Третій")
PICKER_SHARES = (0.6, 0.25, 0.15)   # основний колір стіни важить найбільше


# ---------- кольори ----------

def _lab_to_hex(lab) -> str:
    """[L, a, b] -> '#rrggbb'. Беремо функцію R1, а поки вона заглушка — рахуємо самі."""
    try:
        return core_palette.lab_to_hex(np.asarray(lab, dtype=float)[:3])
    except NotImplementedError:
        from skimage.color import lab2rgb

        rgb = lab2rgb(np.asarray(lab, dtype=float)[:3].reshape(1, 1, 3)).reshape(3)
        r, g, b = (int(round(float(c) * 255)) for c in np.clip(rgb, 0, 1))
        return f"#{r:02x}{g:02x}{b:02x}"


def _hex_to_lab(hex_color: str) -> np.ndarray:
    from skimage.color import rgb2lab

    h = hex_color.lstrip("#")
    rgb = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=float) / 255.0
    return rgb2lab(rgb.reshape(1, 1, 3)).reshape(3)


def palette_from_hex(colors, shares=None) -> np.ndarray:
    """Список '#rrggbb' (+ частки) -> палітра (k, 4), відсортована за часткою спаданням."""
    k = len(colors)
    w = np.full(k, 1.0 / k) if shares is None else np.asarray(shares, dtype=float)
    w = w / w.sum()
    pal = np.column_stack([np.array([_hex_to_lab(c) for c in colors]), w])
    return pal[np.argsort(-pal[:, 3], kind="stable")]


# ---------- палітра з фото ----------

def _fallback_extract(img: Image.Image, k: int) -> np.ndarray:
    """Тимчасова заміна extract_palette() від R1 — той самий рецепт: ~64 px -> Lab -> KMeans."""
    import warnings

    from skimage.color import rgb2lab
    from sklearn.cluster import KMeans

    small = img.convert("RGB")
    small.thumbnail((64, 64))
    lab = rgb2lab(np.asarray(small, dtype=float) / 255.0).reshape(-1, 3)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")   # однотонна стіна -> менше k різних кольорів, це ок
        km = KMeans(n_clusters=k, n_init=4, random_state=0).fit(lab)
    shares = np.bincount(km.labels_, minlength=k) / len(lab)
    order = np.argsort(-shares, kind="stable")
    return np.column_stack([km.cluster_centers_[order], shares[order]])


def palette_from_image(img: Image.Image, k: int = config.PALETTE_K) -> tuple[np.ndarray, bool]:
    """Палітра фото стіни. Повертає (палітра, чи_рахував_R1)."""
    img = ImageOps.exif_transpose(img).convert("RGB")   # фото з телефона часто «лежить на боці»
    img.thumbnail((ANALYSIS_PX, ANALYSIS_PX))
    try:
        return np.asarray(core_palette.extract_palette(img, k), dtype=float), True
    except NotImplementedError:
        return _fallback_extract(img, k), False


@st.cache_data(show_spinner=False)
def _palette_from_bytes(data: bytes, k: int) -> tuple[np.ndarray, bool]:
    return palette_from_image(Image.open(io.BytesIO(data)), k)


# ---------- плашки ----------

def swatches_html(pal: np.ndarray) -> str:
    """Смуга кольорів: ширина плашки = частка кольору, під нею — hex і відсоток."""
    bar, legend = [], []
    for L, a, b, w in np.asarray(pal, dtype=float):
        hx = _lab_to_hex([L, a, b])
        pct = round(w * 100)
        text = "#1c1c1c" if L > 60 else "#ffffff"
        label = f"{pct}%" if w >= 0.12 else ""
        bar.append(
            f'<div title="{hx} · {pct}%" style="flex:{max(w, 0.04):.4f} 1 0;min-width:14px;background:{hx};'
            f'color:{text};display:flex;align-items:center;justify-content:center;'
            f'font-size:0.8rem;font-weight:600">{label}</div>'
        )
        legend.append(
            f'<span style="display:inline-flex;align-items:center;gap:4px;margin:0 10px 4px 0;'
            f'font-size:0.75rem;opacity:0.8;white-space:nowrap">'
            f'<span style="width:10px;height:10px;border-radius:50%;background:{hx};'
            f'border:1px solid rgba(128,128,128,0.5)"></span>{hx} · {pct}%</span>'
        )
    return (
        '<div style="display:flex;height:56px;border-radius:12px;overflow:hidden;'
        'border:1px solid rgba(128,128,128,0.35);margin:4px 0 8px">' + "".join(bar) + "</div>"
        '<div style="display:flex;flex-wrap:wrap">' + "".join(legend) + "</div>"
    )


def show_palette(pal: np.ndarray, title: str = "Палітра стіни") -> None:
    st.markdown(f"**{title}**")
    st.markdown(swatches_html(pal), unsafe_allow_html=True)


# ---------- екран ----------

def render_wall() -> np.ndarray | None:
    """Малює екран «Стіна». Повертає палітру (k, 4) або None, якщо фото ще немає."""
    st.subheader("1. Стіна")
    source = st.radio(
        "Як задати стіну", ["Фото", "Кольори"], horizontal=True,
        label_visibility="collapsed", key="wall_source",
    )

    pal: np.ndarray | None = None
    if source == "Фото":
        file = st.file_uploader(
            "Фото стіни або кімнати", type=["jpg", "jpeg", "png", "webp"], key="wall_file",
            help="На телефоні тут можна і вибрати фото з галереї, і зробити нове.",
        )
        # Камеру вмикаємо лише на прохання: інакше браузер одразу питає дозвіл і тримає камеру.
        if file is None and st.toggle("Зняти камерою просто тут", key="wall_use_camera"):
            file = st.camera_input("Сфотографуй стіну", label_visibility="collapsed", key="wall_camera")

        if file is None:
            st.caption("Немає фото під рукою? Перемкнись на «Кольори».")
        else:
            data = file.getvalue()
            try:
                pal, by_r1 = _palette_from_bytes(data, config.PALETTE_K)
            except Exception:
                st.error("Не вдалося прочитати це фото. Спробуй інше (JPG або PNG).")
            else:
                st.session_state["wall_photo_bytes"] = data   # знадобиться для «Примірки»
                if not by_r1:
                    st.caption("Палітра рахується тимчасовою функцією — чекаємо extract_palette() від R1.")
    else:
        cols = st.columns(len(PICKER_DEFAULTS))
        picked = [
            col.color_picker(label, default, key=f"wall_color_{i}")
            for i, (col, label, default) in enumerate(zip(cols, PICKER_LABELS, PICKER_DEFAULTS))
        ]
        pal = palette_from_hex(picked, PICKER_SHARES)

    if pal is None:
        st.session_state.pop(WALL_KEY, None)
        return None

    st.session_state[WALL_KEY] = pal
    show_palette(pal)
    return pal
