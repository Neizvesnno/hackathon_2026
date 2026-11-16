"""Палітри кольорів. Власник: R1 (Олександр). Формат палітри — див. CONTRACT.md."""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from PIL import Image
from skimage.color import lab2rgb, rgb2lab
from sklearn.cluster import KMeans

_SIDE = 64  # до якого розміру зменшуємо довшу сторону перед k-means


def _to_rgb_array(img: Image.Image, side: int = _SIDE) -> np.ndarray:
    """PIL -> масив пікселів (N, 3) у RGB 0…1, зменшений до ~side px."""
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, img)
    img = img.convert("RGB")
    img = img.copy()
    img.thumbnail((side, side), Image.Resampling.BILINEAR)
    return np.asarray(img, dtype=np.float64).reshape(-1, 3) / 255.0


def extract_palette(img: Image.Image, k: int = 5) -> np.ndarray:
    """k домінантних кольорів зображення в CIELAB + частки площі.

    Повертає np.ndarray форми (k, 4): [L, a, b, частка], частки в сумі = 1,
    рядки відсортовані за часткою спаданням. Працює і для картин, і для фото стіни.
    """
    rgb = _to_rgb_array(img)
    lab = rgb2lab(rgb.reshape(-1, 1, 3)).reshape(-1, 3)

    n_unique = len(np.unique(np.round(lab, 3), axis=0))
    n_clusters = max(1, min(k, n_unique))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # ConvergenceWarning на однотонних зображеннях
        km = KMeans(n_clusters=n_clusters, n_init=3, random_state=0).fit(lab)

    counts = np.bincount(km.labels_, minlength=n_clusters).astype(np.float64)
    pal = np.column_stack([km.cluster_centers_, counts / counts.sum()])
    pal = pal[np.argsort(-pal[:, 3], kind="stable")]

    if n_clusters < k:  # мало різних кольорів — доповнюємо головним кольором з часткою 0
        pad = np.tile(pal[:1], (k - n_clusters, 1))
        pad[:, 3] = 0.0
        pal = np.vstack([pal, pad])
    return pal


def row_to_palette(row: pd.Series, k: int = 5) -> np.ndarray:
    """Збирає палітру (k, 4) з колонок pal_L_i, pal_a_i, pal_b_i, pal_w_i рядка features.parquet."""
    return np.array(
        [[row[f"pal_{c}_{i}"] for c in ("L", "a", "b", "w")] for i in range(1, k + 1)],
        dtype=np.float64,
    )


def lab_to_hex(lab: np.ndarray) -> str:
    """[L, a, b] -> '#rrggbb' (для плашок кольорів в інтерфейсі)."""
    lab = np.asarray(lab, dtype=np.float64)[:3].reshape(1, 1, 3)
    rgb = np.clip(lab2rgb(lab).reshape(3), 0.0, 1.0)
    r, g, b = (int(round(v * 255)) for v in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"
