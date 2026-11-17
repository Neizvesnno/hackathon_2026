 🇺🇦 [Українська версія](README.md)

# Paint Your Wall

An app that finds a painting for a specific wall. Take a photo of the wall or pick its colours, and get 12 paintings from a dataset of 10,000 works that match it by colour, genre, era and the artist's fame.

**Try it:** https://arts4us.streamlit.app (works on a phone too)

Built at the KSE Python Hackathon on Open Data (Kyiv School of Economics, 16 November 2026). The project received the maximum jury score.

![Demo: wall photo → matched paintings → try-on](https://github.com/user-attachments/assets/f4bcf3c6-4401-4236-bb0c-717a25ea4bc1)

## Features

- **Wall palette from a photo.** 5 dominant colours in CIELAB space (k-means), with the share of the area each one covers.
- **Colour matching.** Distance between palettes is CIEDE2000, weighted by colour share: a large patch counts more than a small accent.
- **Two modes.** "Harmony" looks for paintings in the wall's colours, "Accent" in complementary ones.
- **Transparent ranking.** The score combines colour, genre, century and fame. Weights are adjustable with sliders, and each card shows how much every component contributed.
- **Discovery ↔ famous.** A slider that lifts lesser-known or famous artists.
- **Ukrainian artists first.** A checkbox that moves paintings by Ukrainian artists to the top.
- **Mood.** Filter by the painting's mood (calm, dramatic, cosy…), tagged with CLIP.
- **Hide nudity.** A toggle based on Wikidata genres and words in the title (approximate).
- **Try-on.** The chosen painting is placed on a photo of the room, with a frame and a shadow.
- **Art map.** All 10,000 paintings as points in colour space (t-SNE), with the matches highlighted.

![Try-on: a painting on a wall at KSE](https://github.com/user-attachments/assets/f0ef3626-738c-44b4-9b02-8e695f2fc46d)
*Try-on: «A bag of groceries» by Karl Witkowski (public domain)*

## Data

10,000 paintings from the 12th to the 21st century by 5,783 artists. Metadata comes from [Wikidata](https://www.wikidata.org) (CC0), thumbnails from [Wikimedia Commons](https://commons.wikimedia.org). The licence and author of every file are listed in `data/paintings.csv` and shown under each painting in the app.

The sample is stratified: no more than 15 paintings per artist, 63% of works by lesser-known artists, an even spread across centuries and genres, and 948 paintings by Ukrainian artists. Details in `data/DATASET.md`.

## How it works

```
data/         dataset: CSV with metadata and 10,000 thumbnails
pipeline/     extract_features.py — palettes and features; mood_tags.py — moods (CLIP)
app_data/     generated files: features.parquet, mood_tags.parquet, map_coords.parquet
core/         palette.py (palettes), match.py (ranking), tryon.py (try-on), config.py
analysis/     art_map.py (map), defense_plots.py (charts)
app/          Streamlit interface
CONTRACT.md   agreements between modules: file schemas and function signatures
```

The app does not load the 323 MB of images. It reads `features.parquet` (≈2.5 MB) and shows only the 12 thumbnails it needs, by link. Matching across 10,000 paintings takes about 0.05 s.

## Run locally

```bash
git clone https://github.com/Neizvesnno/hackathon_2026.git
cd hackathon_2026
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/main.py
```

The files in `app_data/` are already in the repository. To rebuild them:

```bash
python -m pipeline.extract_features    # palettes and features, a few minutes
python -m analysis.art_map             # map coordinates
python -m pipeline.mood_tags           # moods; needs torch and the CLIP model, not in requirements
```

## Team

| Role | Who |
|---|---|
| Idea, team lead, integration | Pavlo |
| Painting data and features | Oleksandr |
| Matching algorithm | Ivan |
| Mobile interface | Volodymyr |
| Map, try-on, analytics | Maksym |

The code was written during the hackathon with the help of AI assistants.

## Limitations

- Genre, style and size are missing for some paintings: the data is only as complete as Wikidata.
- An artist's fame is approximated by the number of language versions of their Wikipedia article.
- Mood tags and the nudity filter are automatic and make mistakes.
- There are few contemporary works: they are protected by copyright and rarely available on Commons.
