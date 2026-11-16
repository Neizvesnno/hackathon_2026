"""«Мапа мистецтва»: картини як точки в кольоровому просторі. Власник: R4 (Максим).

Запуск з кореня: python -m analysis.art_map  (будує app_data/map_coords.parquet)
"""
from __future__ import annotations

import pandas as pd

from core import config


def build_map(df: pd.DataFrame) -> pd.DataFrame:
    """t-SNE (або UMAP) по векторах палітр -> DataFrame painting_id, x, y; зберігає config.MAP_COORDS_PATH."""
    raise NotImplementedError("R4: build_map")


def art_map_figure(df: pd.DataFrame, coords: pd.DataFrame,
                   highlight_ids: list[str] | None = None):
    """plotly Figure: точка = картина в її головному кольорі, highlight_ids — підсвічені."""
    raise NotImplementedError("R4: art_map_figure")


if __name__ == "__main__":
    build_map(pd.read_parquet(config.FEATURES_PATH))
