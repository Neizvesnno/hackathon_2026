"""Графіки для захисту. Власник: R4 (Максим).

Запуск з кореня:
    python -m analysis.defense_plots

Зберігає PNG у analysis/ (середній колір по століттях + розподіл теплоти).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core import config
from core.palette import lab_to_hex

OUT_DIR = Path(__file__).resolve().parent


def _load() -> pd.DataFrame:
    df = pd.read_parquet(config.FEATURES_PATH)
    # відкидаємо явні викиди по року
    df = df[(df["year"] > 1000) & (df["year"] < 2025)].copy()
    return df


def plot_century_colors(df: pd.DataFrame) -> go.Figure:
    """Середній колір (за головним кольором палітри) по століттях."""
    # середні L,a,b по століттях (зважено часткою головного кольору)
    g = (
        df.groupby("century")
        .agg(
            L=("pal_L_1", "mean"),
            a=("pal_a_1", "mean"),
            b=("pal_b_1", "mean"),
            n=("painting_id", "count"),
        )
        .reset_index()
        .sort_values("century")
    )
    g = g[g["n"] >= 30]  # прибираємо століття з малою кількістю

    colors = [lab_to_hex(np.array([r.L, r.a, r.b])) for r in g.itertuples()]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=g["century"].astype(str) + " ст.",
            y=g["n"],
            marker_color=colors,
            text=g["n"],
            textposition="outside",
            hovertemplate="%{x}<br>картин: %{y}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Скільки картин по століттях (колір стовпчика = середній головний колір)",
        xaxis_title="Століття",
        yaxis_title="Кількість картин",
        height=420,
        margin=dict(l=40, r=20, t=50, b=40),
        showlegend=False,
    )
    return fig


def plot_warmth_by_century(df: pd.DataFrame) -> go.Figure:
    """Розподіл теплоти (середнє b*) по століттях — box plot."""
    df = df[df["century"].between(15, 21)].copy()
    df["century_label"] = df["century"].astype(str) + " ст."

    fig = px.box(
        df,
        x="century_label",
        y="warmth",
        points=False,
        color_discrete_sequence=["#5b8fa8"],
    )
    fig.update_layout(
        title="Теплота кольору (b*) по століттях",
        xaxis_title="Століття",
        yaxis_title="warmth (середнє b*)",
        height=420,
        margin=dict(l=40, r=20, t=50, b=40),
        showlegend=False,
    )
    fig.add_hline(y=0, line_dash="dot", line_color="gray", annotation_text="нейтрально")
    return fig


def plot_genre_share(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """Топ жанрів у датасеті."""
    vc = df["genre_main"].value_counts().head(top_n).reset_index()
    vc.columns = ["genre", "count"]

    fig = px.bar(
        vc,
        x="count",
        y="genre",
        orientation="h",
        color_discrete_sequence=["#c47c5c"],
    )
    fig.update_layout(
        title=f"Топ-{top_n} жанрів у датасеті",
        xaxis_title="Кількість картин",
        yaxis_title="",
        yaxis=dict(autorange="reversed"),
        height=420,
        margin=dict(l=20, r=20, t=50, b=40),
        showlegend=False,
    )
    return fig


def make_defense_figure(df: pd.DataFrame | None = None) -> go.Figure:
    """Зведена фігура з двох графіків для захисту (можна показати в один слайд)."""
    if df is None:
        df = _load()

    fig1 = plot_century_colors(df)
    fig2 = plot_warmth_by_century(df)

    # збираємо в один layout з двома підграфіками
    combined = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            "Картини по століттях (колір = середній головний)",
            "Теплота (b*) по століттях",
        ),
        horizontal_spacing=0.08,
    )

    for tr in fig1.data:
        combined.add_trace(tr, row=1, col=1)
    for tr in fig2.data:
        combined.add_trace(tr, row=1, col=2)

    combined.update_layout(
        height=440,
        margin=dict(l=40, r=20, t=60, b=40),
        showlegend=False,
        title_text="Огляд датасету для захисту",
    )
    combined.update_yaxes(title_text="кількість", row=1, col=1)
    combined.update_yaxes(title_text="warmth (b*)", row=1, col=2)
    return combined


if __name__ == "__main__":
    print("Читаю features.parquet…")
    df = _load()
    print(f"Картин після фільтра: {len(df)}")

    fig = make_defense_figure(df)
    out = OUT_DIR / "defense_overview.html"
    fig.write_html(str(out), include_plotlyjs="cdn")
    print(f"Збережено: {out}")

    # окремі графіки теж
    plot_century_colors(df).write_html(str(OUT_DIR / "century_colors.html"), include_plotlyjs="cdn")
    plot_warmth_by_century(df).write_html(str(OUT_DIR / "warmth_by_century.html"), include_plotlyjs="cdn")
    plot_genre_share(df).write_html(str(OUT_DIR / "genre_share.html"), include_plotlyjs="cdn")
    print("Окремі графіки теж збережені в analysis/")
