"""«Мапа мистецтва»: картини як точки в кольоровому просторі. Власник: R4 (Максим).

Запуск з кореня: python -m analysis.art_map  (будує app_data/map_coords.parquet)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.manifold import TSNE

from core import config
from core.palette import lab_to_hex, row_to_palette


def _palette_vectors(df: pd.DataFrame) -> np.ndarray:
    """Вектор палітри: 5 кольорів × (L, a, b) + частки → (N, 20)."""
    cols = []
    for i in range(1, 6):
        for c in ("L", "a", "b", "w"):
            cols.append(f"pal_{c}_{i}")
    return df[cols].to_numpy(dtype=np.float64)


def build_map(df: pd.DataFrame) -> pd.DataFrame:
    """t-SNE по векторах палітр -> DataFrame painting_id, x, y; зберігає config.MAP_COORDS_PATH."""
    if len(df) == 0:
        coords = pd.DataFrame(columns=["painting_id", "x", "y"])
        coords.to_parquet(config.MAP_COORDS_PATH, index=False)
        return coords

    X = _palette_vectors(df)
    # для швидкості на 10k точок
    perplexity = min(30, max(5, len(df) // 100))
    tsne = TSNE(
        n_components=2,
        perplexity=perplexity,
        learning_rate="auto",
        init="pca",
        random_state=42,
        n_iter=750,
    )
    emb = tsne.fit_transform(X)

    coords = pd.DataFrame(
        {
            "painting_id": df["painting_id"].astype(str).values,
            "x": emb[:, 0].astype(np.float32),
            "y": emb[:, 1].astype(np.float32),
        }
    )
    config.MAP_COORDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    coords.to_parquet(config.MAP_COORDS_PATH, index=False)
    return coords


def art_map_figure(
    df: pd.DataFrame,
    coords: pd.DataFrame,
    highlight_ids: list[str] | None = None,
):
    """plotly Figure: точка = картина в її головному кольорі, highlight_ids — підсвічені."""
    merged = coords.merge(
        df[["painting_id", "title", "artist_name", "pal_L_1", "pal_a_1", "pal_b_1"]],
        on="painting_id",
        how="left",
    )

    # колір точки = головний колір палітри
    colors = [
        lab_to_hex(np.array([r.pal_L_1, r.pal_a_1, r.pal_b_1]))
        for r in merged.itertuples()
    ]

    highlight = set(highlight_ids or [])
    is_hl = merged["painting_id"].isin(highlight)

    # звичайні точки
    normal = merged[~is_hl]
    fig = go.Figure()

    if len(normal):
        fig.add_trace(
            go.Scattergl(
                x=normal["x"],
                y=normal["y"],
                mode="markers",
                marker=dict(
                    size=5,
                    color=[colors[i] for i in normal.index],
                    opacity=0.65,
                    line=dict(width=0),
                ),
                text=normal["title"] + " — " + normal["artist_name"],
                hoverinfo="text",
                name="картини",
                showlegend=False,
            )
        )

    # підсвічені (більші + обводка)
    hl = merged[is_hl]
    if len(hl):
        fig.add_trace(
            go.Scattergl(
                x=hl["x"],
                y=hl["y"],
                mode="markers",
                marker=dict(
                    size=14,
                    color=[colors[i] for i in hl.index],
                    opacity=1.0,
                    line=dict(width=2, color="#111"),
                ),
                text=hl["title"] + " — " + hl["artist_name"],
                hoverinfo="text",
                name="підібрані",
                showlegend=False,
            )
        )

    fig.update_layout(
        margin=dict(l=10, r=10, t=30, b=10),
        height=420,
        xaxis=dict(visible=False, fixedrange=True),
        yaxis=dict(visible=False, fixedrange=True, scaleanchor="x", scaleratio=1),
        plot_bgcolor="#fafafa",
        paper_bgcolor="#fafafa",
        title=dict(text="Мапа мистецтва", font=dict(size=14)),
    )
    return fig


if __name__ == "__main__":
    print("Читаю features.parquet…")
    df = pd.read_parquet(config.FEATURES_PATH)
    print(f"Картин: {len(df)}")
    coords = build_map(df)
    print(f"Готово: {config.MAP_COORDS_PATH} ({len(coords)} точок)")
