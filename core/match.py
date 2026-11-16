"""Підбір картин під стіну. Власник: R2 (Іван). Сигнатури — див. CONTRACT.md."""
from __future__ import annotations

import numpy as np
import pandas as pd


def palette_distance(wall: np.ndarray, painting: np.ndarray) -> float:
    """Відстань між двома палітрами (k, 4) через CIEDE2000, зважена частками. Менше = схожіше."""
    raise NotImplementedError("R2: palette_distance")


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
    """Топ-k картин для палітри стіни.

    mode: "harmony" — схожі кольори, "accent" — комплементарні (відтінок стіни +180° у LCh).
    weights: {"color": 1.0, "genre": 0.0, "century": 0.0}.
    fame: -1 = маловідомі вище … +1 = відомі вище.
    Повертає рядки df + score, score_color, score_genre, score_century, score_fame (0…1),
    відсортовані за score спаданням. < 1 с на 10 000 картинах.
    """
    raise NotImplementedError("R2: recommend")
