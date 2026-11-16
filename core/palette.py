"""Палітри кольорів. Власник: R1 (Олександр). Формат палітри — див. CONTRACT.md."""
from __future__ import annotations

import numpy as np
import pandas as pd
from PIL import Image


def extract_palette(img: Image.Image, k: int = 5) -> np.ndarray:
    """k домінантних кольорів зображення в CIELAB + частки площі.

    Повертає np.ndarray форми (k, 4): [L, a, b, частка], частки в сумі = 1,
    рядки відсортовані за часткою спаданням. Працює і для картин, і для фото стіни.
    """
    raise NotImplementedError("R1: extract_palette")


def row_to_palette(row: pd.Series, k: int = 5) -> np.ndarray:
    """Збирає палітру (k, 4) з колонок pal_L_i, pal_a_i, pal_b_i, pal_w_i рядка features.parquet."""
    raise NotImplementedError("R1: row_to_palette")


def lab_to_hex(lab: np.ndarray) -> str:
    """[L, a, b] -> '#rrggbb' (для плашок кольорів в інтерфейсі)."""
    raise NotImplementedError("R1: lab_to_hex")
