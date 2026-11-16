"""Будує app_data/features.parquet з data/. Власник: R1 (Олександр).

Запуск з кореня репозиторію:
    python -m pipeline.extract_features            # усі 10 000
    python -m pipeline.extract_features --limit 300  # чорновий файл
Схема колонок — CONTRACT.md, розділ features.parquet.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")  # k-means у кожному процесі однопотоково

import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from PIL import Image
from skimage.color import rgb2lab
from tqdm import tqdm

from core import config
from core.palette import _to_rgb_array, extract_palette

K = config.PALETTE_K
PAL_COLS = [f"pal_{c}_{i}" for c in ("L", "a", "b", "w") for i in range(1, K + 1)]
OUT_COLS = [
    "painting_id", "title", "artist_id", "artist_name", "year", "century",
    "genre_main", "genre_ids", "fame_tier", "artist_sitelinks", "is_ukrainian",
    "image_url", "attribution", "license",
    *PAL_COLS, "brightness", "saturation", "warmth",
]


def _blank(s: pd.Series) -> pd.Series:
    """Порожні рядки / пробіли -> NA, щоб працював fillna."""
    return s.where(s.notna() & (s.astype(str).str.strip() != ""), None)


def image_features(rel_path: str) -> dict | None:
    """Палітра + яскравість/насиченість/теплота для однієї картинки; None, якщо не прочиталась."""
    try:
        with Image.open(config.DATA_DIR / rel_path) as img:
            img.load()
            pal = extract_palette(img, K)
            lab = rgb2lab(_to_rgb_array(img).reshape(-1, 1, 3)).reshape(-1, 3)
    except Exception:
        return None
    if not np.isfinite(pal).all():
        return None
    feats = {}
    for i in range(K):
        L, a, b, w = pal[i]
        feats[f"pal_L_{i + 1}"], feats[f"pal_a_{i + 1}"] = float(L), float(a)
        feats[f"pal_b_{i + 1}"], feats[f"pal_w_{i + 1}"] = float(b), float(w)
    feats["brightness"] = float(lab[:, 0].mean())
    feats["saturation"] = float(np.hypot(lab[:, 1], lab[:, 2]).mean())
    feats["warmth"] = float(lab[:, 2].mean())
    return feats


def build_metadata(limit: int | None) -> pd.DataFrame:
    p = pd.read_csv(config.PAINTINGS_CSV, dtype=str, keep_default_na=False)
    a = pd.read_csv(config.ARTISTS_CSV, dtype=str, keep_default_na=False)
    g = pd.read_csv(config.GENRES_CSV, dtype=str, keep_default_na=False)
    if limit:
        p = p.head(limit)

    genre_label = dict(zip(g["id"], _blank(g["label_uk"]).fillna(_blank(g["label_en"]))))
    a = a.assign(
        artist_name=_blank(a["name_uk"]).fillna(_blank(a["name_en"])).fillna("Невідомий художник"),
        artist_sitelinks=pd.to_numeric(a["sitelinks"], errors="coerce").fillna(0).astype(int),
        is_ukrainian=a["is_ukrainian"].str.lower().eq("true"),
    )[["artist_id", "artist_name", "artist_sitelinks", "is_ukrainian", "fame_tier"]]

    df = p.merge(a, on="artist_id", how="left")
    df["title"] = _blank(df["title_uk"]).fillna(_blank(df["title_en"])).fillna("Без назви")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df[df["year"].notna()].copy()
    df["year"] = df["year"].astype(int)
    df["century"] = (df["year"] - 1) // 100 + 1
    first_genre = df["genres"].str.split(";").str[0].str.strip()
    df["genre_main"] = first_genre.map(genre_label).fillna("інше")
    df["genre_ids"] = df["genres"]
    df["image_url"] = config.IMAGE_BASE_URL + df["image_file"]
    df["attribution"] = _blank(df["attribution"]).fillna(df["artist_name"]).fillna("")
    df["artist_name"] = df["artist_name"].fillna("Невідомий художник")
    df["fame_tier"] = df["fame_tier"].fillna("obscure")
    df["artist_sitelinks"] = df["artist_sitelinks"].fillna(0).astype(int)
    df["is_ukrainian"] = df["is_ukrainian"].fillna(False).astype(bool)
    return df


def main(limit: int | None = None, workers: int | None = None) -> None:
    for stream in (sys.stdout, sys.stderr):  # консоль Windows (cp1252) не вміє в кирилицю
        try:
            stream.reconfigure(errors="replace")
        except AttributeError:
            pass
    t0 = time.time()
    df = build_metadata(limit)
    workers = workers or max(1, (os.cpu_count() or 2) - 1)
    paths = df["image_file"].tolist()

    with ProcessPoolExecutor(max_workers=workers) as ex:
        feats = list(tqdm(ex.map(image_features, paths, chunksize=16),
                          total=len(paths), desc="палітри"))

    ok = [f is not None for f in feats]
    n_bad = len(ok) - sum(ok)
    df = df[ok].reset_index(drop=True)
    df = pd.concat([df, pd.DataFrame([f for f in feats if f is not None])], axis=1)
    df = df[OUT_COLS]

    config.APP_DATA.mkdir(parents=True, exist_ok=True)
    df.to_parquet(config.FEATURES_PATH, index=False, compression="zstd")
    size_mb = config.FEATURES_PATH.stat().st_size / 1e6
    print(f"Збережено {len(df)} рядків -> {config.FEATURES_PATH} ({size_mb:.2f} МБ), "
          f"викинуто {n_bad} картинок, що не прочитались; {time.time() - t0:.0f} с")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None, help="обробити лише перші N картин")
    p.add_argument("--workers", type=int, default=None, help="кількість процесів")
    args = p.parse_args()
    main(args.limit, args.workers)
