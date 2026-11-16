"""Шляхи і константи проєкту. Власник: R0 (Павло). Беріть шляхи тільки звідси."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
APP_DATA = ROOT / "app_data"

PAINTINGS_CSV = DATA_DIR / "paintings.csv"
ARTISTS_CSV = DATA_DIR / "artists.csv"
GENRES_CSV = DATA_DIR / "genres.csv"
STYLES_CSV = DATA_DIR / "styles.csv"

FEATURES_PATH = APP_DATA / "features.parquet"
MAP_COORDS_PATH = APP_DATA / "map_coords.parquet"

# Картинки застосунок вантажить з GitHub за URL, а не з диска: IMAGE_BASE_URL + image_file
IMAGE_BASE_URL = "https://raw.githubusercontent.com/Neizvesnno/hackathon_2026/main/data/"

PALETTE_K = 5      # кількість домінантних кольорів у палітрі
TOP_K = 12         # скільки картин показує застосунок
