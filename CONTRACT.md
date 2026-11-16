# CONTRACT.md — домовленості між модулями

Цей файл — єдине джерело правди для всієї команди і для кожної ШІ.
**На початку кожної сесії з ШІ вставляй їй цей файл + свій рядок з таблиці ролей.**
Сигнатури функцій і назви колонок нижче **не змінюємо** без згоди Павла (R0).

## Що робимо

Застосунок на Streamlit (відкривається в браузері телефона): користувач фотографує стіну
або вибирає її кольори, а застосунок підбирає картини з датасету (10 000 картин) за кольором,
жанром, століттям і відомістю художника. Режими «гармонія» (схожі кольори) і «акцент»
(комплементарні). Плюс «мапа мистецтва» і примірка картини на фото кімнати.

## Ролі і власність файлів

Кожен редагує **лише свої файли**. Потрібна зміна в чужому — пишеш власнику в чат.

| Роль | Хто | Файли |
| --- | --- | --- |
| R0 · тімлід, інтеграція | Павло | `CONTRACT.md`, `README.md`, `requirements.txt`, `.gitignore`, `core/config.py` |
| R1 · дані та ознаки | Олександр | `core/palette.py`, `pipeline/extract_features.py`, `app_data/features.parquet` |
| R2 · алгоритм підбору | Іван | `core/match.py` |
| R3 · мобільний інтерфейс | Володимир | `app/main.py`, `app/ui_*.py` |
| R4 · мапа, примірка, аналітика | Максим | `analysis/art_map.py`, `core/tryon.py`, `app_data/map_coords.parquet` |

## Структура репозиторію

```
data/                     # датасет — НЕ ЧІПАТИ, нічого туди не комітити
  paintings.csv artists.csv genres.csv styles.csv DATASET.md
  images/<художник>__<artist_id>/<painting_id>.jpg   # 10 000 мініатюр, ширина ≤ 330 px
app_data/                 # згенеровані файли, які читає застосунок (комітимо)
  features.parquet        # R1
  map_coords.parquet      # R4
core/
  config.py               # шляхи і константи (R0)
  palette.py              # R1
  match.py                # R2
  tryon.py                # R4
pipeline/extract_features.py   # R1, запуск: python -m pipeline.extract_features
analysis/art_map.py            # R4, запуск: python -m analysis.art_map
app/main.py                    # R3, запуск: streamlit run app/main.py
```

Усі команди запускаємо **з кореня репозиторію**. Шляхи беремо лише з `core/config.py`,
не пишемо `"../data/..."` руками.

## Вхідні дані (data/, тільки читаємо)

`paintings.csv` — одна картина = один рядок:
`painting_id` (QID Wikidata, ключ), `title_uk`, `title_en`, `artist_id`, `year`, `year_precision`,
`genres` (QID через `;`), `styles` (QID через `;`, майже завжди порожньо), `material`, `collection`,
`width_cm`, `height_cm`, `image_file` (шлях відносно `data/`), `commons_file`, `commons_url`,
`license`, `attribution`, `sitelinks` (мовні версії статті про **картину**).

`artists.csv`: `artist_id`, `name_uk`, `name_en`, `birth_year`, `death_year`, `citizenship`,
`birth_place`, `birth_country`, `is_ukrainian` (`true`/`false`), `styles`, `sitelinks`
(мовні версії статті про **художника**), `fame_tier` (`famous` / `known` / `lesser` / `obscure`),
`n_paintings_in_sample`.

`genres.csv`, `styles.csv`: `id`, `label_uk`, `label_en`, `n_paintings`.

Нюанси: `title_uk` порожній у ~97% (беремо `title_en`, а якщо й він порожній — «Без назви»);
`genres` порожній у ~12%.

## app_data/features.parquet (R1 → усі)

Один рядок на картину, 10 000 рядків, ~2–4 МБ. Застосунок читає **тільки цей файл**,
а картинки показує за `image_url` — тож телефон не вантажить 323 МБ.

| Колонка | Тип | Опис |
| --- | --- | --- |
| `painting_id` | str | QID картини, ключ |
| `title` | str | `title_uk`, інакше `title_en`, інакше «Без назви» |
| `artist_id` | str | QID художника |
| `artist_name` | str | `name_uk`, інакше `name_en` |
| `year` | int | рік створення |
| `century` | int | `(year - 1) // 100 + 1`, напр. 1896 → 19 |
| `genre_main` | str | `label_uk` першого жанру з `genres` (інакше `label_en`); без жанру — `"інше"` |
| `genre_ids` | str | `genres` як є (QID через `;`) |
| `fame_tier` | str | з `artists.csv` |
| `artist_sitelinks` | int | `sitelinks` з `artists.csv` |
| `is_ukrainian` | bool | з `artists.csv` |
| `image_url` | str | `config.IMAGE_BASE_URL + image_file` |
| `attribution` | str | з `paintings.csv` — показувати під картиною |
| `license` | str | з `paintings.csv` |
| `pal_L_1` … `pal_L_5` | float | L* п'яти домінантних кольорів (0…100) |
| `pal_a_1` … `pal_a_5` | float | a* |
| `pal_b_1` … `pal_b_5` | float | b* |
| `pal_w_1` … `pal_w_5` | float | частки площі, сума = 1, від найбільшої (1) до найменшої (5) |
| `brightness` | float | середнє L* по картині, 0…100 |
| `saturation` | float | середня хрома √(a²+b²) |
| `warmth` | float | середнє b* (більше = тепліше, жовто-червоне; менше = холодніше) |

Порядок рядків — довільний. Пропусків у колонках `pal_*` бути не повинно: картину, яку не вдалося
прочитати, R1 просто викидає (і пише в консоль скільки).

## app_data/mood_tags.parquet (R1 → R3)

Теги настрою, пораховані заздалегідь моделлю CLIP (`python -m pipeline.mood_tags`, потрібен torch —
лише локально, у `requirements.txt` його немає). Застосунок файл тільки читає; шлях —
`config.MOOD_TAGS_PATH`. Один рядок на картину, з'єднується з `features.parquet` за `painting_id`.

| Колонка | Тип | Опис |
| --- | --- | --- |
| `painting_id` | str | QID картини, ключ |
| `mood_1`, `mood_2`, `mood_3` | str | три найсильніші настрої, українською, від найсильнішого |
| `mood_score_1` … `mood_score_3` | float | їхні оцінки, 0…1 |
| `m_calm`, `m_joyful`, `m_melancholic`, `m_dramatic`, `m_romantic`, `m_mysterious`, `m_majestic`, `m_cozy`, `m_energetic`, `m_anxious` | float | оцінка кожного з 10 настроїв, сума по рядку = 1 |

Настрої: спокійний, радісний, меланхолійний, драматичний, романтичний, таємничий, урочистий,
затишний, енергійний, тривожний. Оцінка відносна: настрій виражений сильніше, ніж у середньому
по датасету. Це автоматична розмітка, а не експертна.

## Палітра — спільний формат

Палітра всюди = `np.ndarray` форми `(k, 4)`, `float`, рядок = `[L, a, b, частка]`,
кольори в просторі **CIELAB (D65)** як у `skimage.color.rgb2lab`, частки в сумі = 1,
рядки відсортовані за часткою від більшої до меншої. Зазвичай `k = 5`.

Перетворення з `features.parquet` у палітру: `core.palette.row_to_palette(row)`.

## Сигнатури функцій

```python
# core/palette.py — R1
def extract_palette(img: PIL.Image.Image, k: int = 5) -> np.ndarray: ...   # (k, 4)
def row_to_palette(row: pd.Series, k: int = 5) -> np.ndarray: ...          # (k, 4) з колонок pal_*
def lab_to_hex(lab: np.ndarray) -> str: ...                                 # [L, a, b] -> "#rrggbb"

# core/match.py — R2
def palette_distance(wall: np.ndarray, painting: np.ndarray) -> float: ...  # CIEDE2000, зважено частками; менше = схожіше
def recommend(
    wall: np.ndarray,                       # (k, 4) палітра стіни
    df: pd.DataFrame,                       # features.parquet
    mode: str = "harmony",                  # "harmony" | "accent"
    weights: dict | None = None,            # {"color": 1.0, "genre": 0.0, "century": 0.0}
    fame: float = 0.0,                      # -1 = відкриття (маловідомі) … +1 = відомі
    genres: list[str] | None = None,        # бажані genre_main; None = будь-які
    centuries: list[int] | None = None,     # бажані століття; None = будь-які
    top_k: int = 12,
) -> pd.DataFrame: ...
# Повертає top_k рядків df (усі колонки) + колонки score, score_color, score_genre,
# score_century, score_fame; кожна складова в 0…1, відсортовано за score спаданням.
# Має відпрацьовувати < 1 с на 10 000 картинах (векторизовано numpy).

# core/tryon.py — R4
def overlay(room: PIL.Image.Image, painting: PIL.Image.Image,
            cx: float = 0.5, cy: float = 0.4, width: float = 0.35) -> PIL.Image.Image: ...
# cx, cy — центр картини, width — її ширина; усе частками 0…1 від розміру фото кімнати.

# analysis/art_map.py — R4
def build_map(df: pd.DataFrame) -> pd.DataFrame: ...       # painting_id, x, y; і зберігає app_data/map_coords.parquet
def art_map_figure(df: pd.DataFrame, coords: pd.DataFrame,
                   highlight_ids: list[str] | None = None) -> "plotly.graph_objects.Figure": ...
```

## Застосунок (R3)

- Запуск: `streamlit run app/main.py` (з кореня). На початку `app/main.py` корінь репозиторію
  додається в `sys.path`, тож працюють імпорти `from core.match import recommend`.
- Дані: `@st.cache_data` на `pd.read_parquet(config.FEATURES_PATH)`.
- Картинки: тільки `st.image(row.image_url)`, ніколи не читати `data/images` із застосунку.
- Під кожною картиною — `attribution` дрібним шрифтом (вимога ліцензій CC BY / BY-SA).
- Поки R2 не готовий — заглушка: `df.sample(12)` з `score = 0`.

## Git — правила

1. Одна гілка `main`. Перед кожним комітом і перед пушем: `git pull --rebase`.
2. `git add` — **тільки свої файли** (не `git add .`).
3. Коміти маленькі, кожні 20–30 хв, повідомлення з кодом ролі: `R2: accent mode`.
4. Заборонено: `git push --force`, будь-які зміни в `data/`, коміт `.venv`, ключів, великих файлів.
5. Конфлікт — нічого не «вирішуємо» самі, кличемо Павла.
6. Нові бібліотеки додає в `requirements.txt` лише Павло — пишіть йому.

## Контрольні точки

16:50 каркас · 17:15 чорновий `features.parquet` (300 картин) · 17:45 повний (10 000) ·
18:00 інтеграція · 19:20 фріз фіч · 20:00 фінальний пуш · далі захист (демо 1–2 хв).
