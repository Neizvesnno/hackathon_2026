"""Результати: сітка з 12 карток. Власник: R3 (Володимир).

Картки малюємо одним HTML-блоком із CSS-сіткою: st.columns на вузькому екрані телефона
складається в одну колонку, а нам треба дві. Картинки — тільки за image_url, не з диска.
"""
from __future__ import annotations

import html
from urllib.parse import quote

import numpy as np
import pandas as pd
import streamlit as st

from core import config
from core.match import recommend

RESULTS_KEY = "results"     # останній показаний топ (DataFrame) — для «Мапи» і «Примірки»
SCORE_PARTS = ("score", "score_color", "score_genre", "score_century", "score_fame")


# ---------- дані ----------

@st.cache_data(show_spinner=False)
def demo_frame() -> pd.DataFrame:
    """Тимчасово, поки немає features.parquet: метадані прямо з data/*.csv (без палітр).

    Колонки названі як у CONTRACT.md, тож картки не помітять різниці.
    """
    p = pd.read_csv(config.PAINTINGS_CSV)
    a = pd.read_csv(config.ARTISTS_CSV)
    g = pd.read_csv(config.GENRES_CSV)
    genre_label = dict(zip(g["id"], g["label_uk"].fillna(g["label_en"])))
    df = p.merge(a[["artist_id", "name_uk", "name_en", "fame_tier", "is_ukrainian"]], on="artist_id", how="left")
    first_genre = df["genres"].fillna("").str.split(";").str[0]
    return pd.DataFrame({
        "painting_id": df["painting_id"],
        "title": df["title_uk"].fillna(df["title_en"]).fillna("Без назви"),
        "artist_id": df["artist_id"],
        "artist_name": df["name_uk"].fillna(df["name_en"]).fillna(""),
        "year": df["year"],
        "century": (df["year"] - 1) // 100 + 1,
        "genre_main": first_genre.map(genre_label).fillna("інше"),
        "fame_tier": df["fame_tier"],
        "is_ukrainian": df["is_ukrainian"],
        "image_url": config.IMAGE_BASE_URL + df["image_file"].map(lambda s: quote(str(s))),
        "attribution": df["attribution"].fillna(""),
        "license": df["license"].fillna(""),
    })


def _stub(df: pd.DataFrame, top_k: int) -> pd.DataFrame:
    """Заглушка з контракту: випадкові картини зі score = 0. Вибірка не стрибає між rerun-ами."""
    seed = st.session_state.setdefault("stub_seed", int(np.random.default_rng().integers(1_000_000)))
    out = df.sample(min(top_k, len(df)), random_state=seed).copy()
    for col in SCORE_PARTS:
        out[col] = 0.0
    return out


def get_results(wall: np.ndarray, df: pd.DataFrame | None, params: dict) -> tuple[pd.DataFrame, str]:
    """Топ картин. Повертає (DataFrame, джерело): 'recommend' | 'stub' | 'demo'."""
    if df is None:
        return _stub(demo_frame(), config.TOP_K), "demo"
    try:
        return recommend(wall, df, top_k=config.TOP_K, **params), "recommend"
    except NotImplementedError:
        return _stub(df, config.TOP_K), "stub"


# ---------- картки ----------

_CSS = """
<style>
.art-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.art-card{border:1px solid rgba(128,128,128,.3);border-radius:12px;overflow:hidden;display:flex;flex-direction:column}
.art-img{aspect-ratio:1/1;background:rgba(128,128,128,.12);display:flex;align-items:center;justify-content:center}
.art-img img{width:100%;height:100%;object-fit:contain;display:block}
.art-body{padding:8px 10px 10px;display:flex;flex-direction:column;gap:2px;min-width:0}
.art-title{font-weight:600;font-size:.9rem;line-height:1.25;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.art-meta{font-size:.8rem;opacity:.85;line-height:1.3;overflow-wrap:anywhere}
.art-score{font-size:.75rem;font-weight:600;margin-top:2px}
.art-parts{display:flex;flex-direction:column;gap:3px;margin-top:4px}
.art-part{display:flex;align-items:center;gap:6px;font-size:.65rem;opacity:.85}
.art-part span:first-child{flex:0 0 4.6em}
.art-part span:last-child{flex:0 0 2.2em;text-align:right}
.art-bar{flex:1 1 auto;height:4px;border-radius:2px;background:rgba(128,128,128,.25);overflow:hidden}
.art-bar i{display:block;height:100%;background:#e0575b;border-radius:2px}
.art-attr{font-size:.65rem;opacity:.6;line-height:1.25;margin-top:4px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;overflow-wrap:anywhere}
</style>
"""


def _txt(value, default: str = "") -> str:
    return default if value is None or pd.isna(value) else html.escape(str(value))


def active_parts(params: dict | None) -> list[tuple[str, str]]:
    """Які складові score показувати: лише ті, що зараз справді впливають на рейтинг."""
    p = params or {}
    w = p.get("weights") or {}
    parts = [("score_color", "колір")]
    if p.get("genres") and w.get("genre", 0) > 0:
        parts.append(("score_genre", "жанр"))
    if p.get("centuries") and w.get("century", 0) > 0:
        parts.append(("score_century", "століття"))
    if p.get("fame"):
        parts.append(("score_fame", "відомість"))
    if w.get("ukrainian", 0) > 0:
        parts.append(("score_ukrainian", "укр. автор"))
    return parts


def parts_html(row, parts) -> str:
    rows = []
    for col, label in parts:
        v = row.get(col)
        if v is None or pd.isna(v):
            continue
        pct = round(min(max(float(v), 0.0), 1.0) * 100)
        rows.append(f'<div class="art-part"><span>{label}</span>'
                    f'<div class="art-bar"><i style="width:{pct}%"></i></div><span>{pct}%</span></div>')
    return f'<div class="art-parts">{"".join(rows)}</div>' if rows else ""


def card_html(row, show_score: bool, parts=()) -> str:
    year = "" if pd.isna(row.get("year")) else str(int(row["year"]))
    meta = " · ".join(x for x in (_txt(row.get("artist_name")), year) if x)
    genre = " · ".join(x for x in (_txt(row.get("genre_main")), _txt(row.get("mood_1"))) if x)
    attr = " · ".join(x for x in (_txt(row.get("attribution")), _txt(row.get("license"))) if x)
    title = _txt(row.get("title"), "Без назви")
    score = ""
    if show_score and not pd.isna(row.get("score")):
        score = f'<div class="art-score">Збіг {round(float(row["score"]) * 100)}%</div>' + parts_html(row, parts)
    return (
        '<div class="art-card">'
        f'<div class="art-img"><img src="{html.escape(str(row["image_url"]), quote=True)}" alt="{title}" loading="lazy"></div>'
        '<div class="art-body">'
        f'<div class="art-title">{title}</div>'
        f'<div class="art-meta">{meta}</div>'
        + (f'<div class="art-meta">{genre}</div>' if genre else "")
        + score
        + (f'<div class="art-attr">{attr}</div>' if attr else "")
        + "</div></div>"
    )


def grid_html(results: pd.DataFrame, show_score: bool, parts=()) -> str:
    cards = "".join(card_html(row, show_score, parts) for _, row in results.iterrows())
    css = "".join(line.strip() for line in _CSS.splitlines())   # одним рядком, щоб markdown не чіпав
    return f'{css}<div class="art-grid">{cards}</div>'


# ---------- екран ----------

def render_results(wall: np.ndarray, df: pd.DataFrame | None, params: dict) -> pd.DataFrame:
    st.subheader("3. Картини для твоєї стіни")
    results, source = get_results(wall, df, params)
    st.session_state[RESULTS_KEY] = results

    if source == "demo":
        st.caption("Поки що випадкові картини: чекаємо features.parquet від R1 і recommend() від R2.")
    elif source == "stub":
        st.caption("Поки що випадкові картини: чекаємо recommend() від R2.")
    if source != "recommend" and st.button("Показати інші", key="stub_reshuffle"):
        st.session_state.pop("stub_seed", None)
        st.rerun()

    if results.empty:
        st.info("За такими фільтрами нічого не знайшлося — прибери частину фільтрів.")
    else:
        st.markdown(
            grid_html(results, show_score=source == "recommend", parts=active_parts(params)),
            unsafe_allow_html=True,
        )
    return results
