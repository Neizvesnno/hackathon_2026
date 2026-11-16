
from __future__ import annotations

import argparse
import sys
import time

import numpy as np
import pandas as pd
from PIL import Image
from tqdm import tqdm

from core import config

MODEL_NAME = "openai/clip-vit-base-patch32"  # ~600 МБ, найшвидша CLIP на CPU
MOOD_TAGS_PATH = config.APP_DATA / "mood_tags.parquet"

# ключ -> (українська назва, англійські підказки для CLIP; усереднюємо їхні ембединги)
MOODS: dict[str, tuple[str, list[str]]] = {
    "calm":        ("спокійний",      ["a calm, peaceful painting", "a serene and tranquil painting"]),
    "joyful":      ("радісний",       ["a joyful, cheerful painting", "a happy and bright painting"]),
    "melancholic": ("меланхолійний",  ["a melancholic, sad painting", "a gloomy and sorrowful painting"]),
    "dramatic":    ("драматичний",    ["a dramatic, intense painting", "a painting full of tension and conflict"]),
    "romantic":    ("романтичний",    ["a romantic, tender painting", "a painting about love and tenderness"]),
    "mysterious":  ("таємничий",      ["a mysterious, enigmatic painting", "a dark and mystical painting"]),
    "majestic":    ("урочистий",      ["a majestic, solemn painting", "a grand and ceremonial painting"]),
    "cozy":        ("затишний",       ["a cozy, warm domestic painting", "an intimate homely painting"]),
    "energetic":   ("енергійний",     ["an energetic, dynamic painting", "a lively painting full of movement"]),
    "anxious":     ("тривожний",      ["an anxious, disturbing painting", "an unsettling and eerie painting"]),
}
KEYS = list(MOODS)


def _load(path: str) -> Image.Image | None:
    try:
        with Image.open(config.DATA_DIR / path) as img:
            return img.convert("RGB")
    except Exception:
        return None


def main(limit: int | None = None, batch: int = 64) -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except AttributeError:
            pass
    import torch
    from transformers import CLIPModel, CLIPProcessor

    t0 = time.time()
    torch.set_grad_enabled(False)
    model = CLIPModel.from_pretrained(MODEL_NAME).eval()
    proc = CLIPProcessor.from_pretrained(MODEL_NAME)

    # усі підказки однією партією; model(...) повертає нормовані text_embeds / image_embeds
    prompts = [t for k in KEYS for t in MOODS[k][1]]
    owner = torch.tensor([m for m, k in enumerate(KEYS) for _ in MOODS[k][1]])
    tok = proc(text=prompts, return_tensors="pt", padding=True)
    scale = model.logit_scale.exp()

    def embed(images: list[Image.Image]) -> tuple[torch.Tensor, torch.Tensor]:
        px = proc(images=images, return_tensors="pt")
        out = model(input_ids=tok["input_ids"], attention_mask=tok["attention_mask"],
                    pixel_values=px["pixel_values"])
        return out.text_embeds, out.image_embeds

    # текстові ембединги настроїв: середнє по підказках кожного настрою, L2-нормовані
    t_all, _ = embed([Image.new("RGB", (224, 224))])
    text_emb = torch.stack([t_all[owner == m].mean(0) for m in range(len(KEYS))])
    text_emb = text_emb / text_emb.norm(dim=-1, keepdim=True)   # (M, D)

    p = pd.read_csv(config.PAINTINGS_CSV, dtype=str, keep_default_na=False)
    if limit:
        p = p.head(limit)
    ids, files = p["painting_id"].tolist(), p["image_file"].tolist()

    out_ids, probs, n_bad = [], [], 0
    for i in tqdm(range(0, len(ids), batch), desc="CLIP"):
        imgs, bid = [], []
        for pid, f in zip(ids[i:i + batch], files[i:i + batch]):
            img = _load(f)
            if img is None:
                n_bad += 1
                continue
            imgs.append(img)
            bid.append(pid)
        if not imgs:
            continue
        _, e = embed(imgs)
        e = e / e.norm(dim=-1, keepdim=True)
        probs.append((scale * e @ text_emb.T).numpy())   # логіти (B, M)
        out_ids.extend(bid)

    # калібрування: CLIP має «улюблені» підказки (напр. majestic), тож віднімаємо середній
    # логіт кожного настрою по датасету — тег = настрій, виражений сильніше, ніж зазвичай
    logits = np.vstack(probs)
    logits = logits - logits.mean(axis=0, keepdims=True)
    P = np.exp(logits - logits.max(axis=1, keepdims=True))
    P = P / P.sum(axis=1, keepdims=True)                  # (N, M), softmax
    order = np.argsort(-P, axis=1)[:, :3]
    labels = np.array([MOODS[k][0] for k in KEYS])
    df = pd.DataFrame({"painting_id": out_ids})
    for j in range(3):
        df[f"mood_{j + 1}"] = labels[order[:, j]]
        df[f"mood_score_{j + 1}"] = P[np.arange(len(P)), order[:, j]].astype(np.float32)
    for m, key in enumerate(KEYS):
        df[f"m_{key}"] = P[:, m].astype(np.float32)

    config.APP_DATA.mkdir(parents=True, exist_ok=True)
    df.to_parquet(MOOD_TAGS_PATH, index=False, compression="zstd")
    size_mb = MOOD_TAGS_PATH.stat().st_size / 1e6
    print(f"Збережено {len(df)} рядків -> {MOOD_TAGS_PATH} ({size_mb:.2f} МБ), "
          f"не прочиталось {n_bad}; {time.time() - t0:.0f} с")
    print(df["mood_1"].value_counts().to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="обробити лише перші N картин")
    ap.add_argument("--batch", type=int, default=64)
    args = ap.parse_args()
    main(args.limit, args.batch)
