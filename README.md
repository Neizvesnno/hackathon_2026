# Картина під стіну — хакатон Open Data

Застосунок підбирає картину під стіну: фото або кольори стіни → картини з датасету
за кольором, жанром, століттям і відомістю художника.

Дані: 10 000 картин з Wikidata (метадані, CC0) і Wikimedia Commons (мініатюри; ліцензія та
автор кожного файлу — у `data/paintings.csv`). Опис датасету — `data/DATASET.md`.

## Запуск

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pipeline.extract_features   # будує app_data/features.parquet
streamlit run app/main.py
```

Домовленості команди — `CONTRACT.md`.
