# Датасет картин (Wikidata + Wikimedia Commons)

Вибірка картин з відкритих даних для хакатону Open Data. Метадані — з Wikidata (CC0), зображення — мініатюри з Wikimedia Commons; ліцензія й автор кожного файлу вказані в `paintings.csv` (колонки `license`, `attribution`, `commons_url`). Під час використання зображень дотримуйтесь цих ліцензій.

Зібрано: 2026-11-12 · Python 3.13.15 · картин: 10000 · художників: 5783 · розмір `data/`: 323 МБ

## Структура

- `paintings.csv` — картини (ключ `painting_id` = QID Wikidata): назви, `artist_id`, `year`, `year_precision`, `genres`, `styles` (QID через `;`), `material`, `collection`, розміри в см, `image_file`, ліцензія.
- `artists.csv` — художники: імена, роки життя, громадянство, `is_ukrainian`, `sitelinks`, `fame_tier`, `n_paintings_in_sample`.
- `genres.csv`, `styles.csv` — довідники QID → назви.
- `images/<художник>__<artist_id>/<painting_id>.jpg` — мініатюри (ширина до 330 px, JPEG).

Зв'язки: `paintings.artist_id → artists.artist_id`; `paintings.genres → genres.id`; `paintings.styles → styles.id`; `paintings.image_file` — шлях відносно `data/`.

## Як формувалась вибірка

Кандидати: елементи Wikidata `instance of painting` із зображенням, одним автором-людиною та датою створення (точність не грубіша за десятиліття). Дублі зображень прибрано; картини з кількома різними авторами пропущено. Далі — стратифікована вибірка з фіксованим seed (42):

- не менше 40.0% картин українських авторів (`is_ukrainian`: громадянство України/УРСР або місце народження в країні Україна за Wikidata);
- не менше 50.0% картин художників із нижніх двох рівнів відомості (рівні за кількістю мовних версій статті у Вікіпедії: famous ≥ 30, known ≥ 10, lesser ≥ 3, obscure — решта);
- не більше 15 картин на художника (рівномірно за роками);
- рівномірний добір за комірками «століття × група жанру» (група — один із 25 найчастіших жанрів, `other` або `none`); без жанру — не більше 25.0%, одне століття — не більше 35.0%.

## Склад вибірки

- Українські автори: 948 картин (9.5%), 198 художників.
- Маловідомі (lesser + obscure): 63.4% картин. Рівні відомості (картин): famous: 842, known: 2820, lesser: 4506, obscure: 1832.
- Максимум картин в одного художника: 15.
- Картин без жанру: 12.3%; найбільша частка одного століття: 23.6%.

Століття (картин): 12: 6, 13: 146, 14: 266, 15: 434, 16: 932, 17: 1896, 18: 1841, 19: 2359, 20: 1923, 21: 197

Топ жанрів: religious art (930), portrait (715), landscape painting (604), mythological painting (561), genre art (546), allegory (517), history painting (516), self-portrait (502), still life (482), marine art (480), cityscape (441), nude (309), animal art (305), floral painting (236), group portrait (174)

Топ стилів (течій): Early Netherlandish painting (31), academic art (20), Art Nouveau (19), Early Renaissance (17), Neoclassicism (16), Orientalism (13), Baroque (13), High Renaissance (12), French Realism (12), Mannerism (11), Symbolism (10), Dutch Golden Age painting (10), Venetian school (10), Proto-Renaissance (8), neo-pop (8)

Ліцензії: Public domain (8703), CC BY-SA 4.0 (454), CC0 (405), CC BY-SA 3.0 (143), CC BY 3.0 (106), CC BY 4.0 (101), PDM-owner (30), CC BY 2.0 (13), No restrictions (11), CC BY-SA 2.0 fr (6)

Частка порожніх значень у `paintings.csv`: title_uk: 96.8%, title_en: 19.9%, genres: 12.3%, styles: 96.5%, material: 17.6%, collection: 13.5%, width_cm: 19.6%, height_cm: 19.6%

## Обмеження

- Дані такі повні, як їх внесли у Wikidata: частина картин не має жанру, стилю, розмірів чи колекції.
- «Відомість» художника — наближення за кількістю мовних версій статті, а не експертна оцінка.
- Правило `is_ukrainian` формальне й залежить від полів Wikidata.

## Попередження збирача

- Ukrainian quota missed: 948 of 4000 (pool exhausted)
- Ukrainian share 9.5% < 40%
- dropped: download failed: image too small: 330x62 - 5
- dropped: download failed: image too small: 330x85 - 4
- dropped: download failed: image too small: 330x91 - 4
- dropped: download failed: image too small: 330x75 - 4
- dropped: missing on Commons - 3
- dropped: download failed: image too small: 330x89 - 3
- dropped: download failed: image too small: 330x83 - 3
- dropped: download failed: image too small: 330x86 - 3
- dropped: download failed: image too small: 330x97 - 3
- dropped: download failed: image too small: 330x12 - 3
- dropped: download failed: image too small: 330x17 - 3
- dropped: download failed: image too small: 330x19 - 3
- dropped: download failed: image too small: 330x93 - 3
- dropped: download failed: image too small: 330x73 - 3
- dropped: not a raster image (image/gif) - 2
- dropped: download failed: image too small: 330x78 - 2
- dropped: download failed: image too small: 330x90 - 2
- dropped: download failed: image too small: 330x82 - 2
- dropped: download failed: image too small: 330x54 - 2
- dropped: download failed: image too small: 330x94 - 2
- dropped: download failed: image too small: 330x43 - 2
- dropped: download failed: image too small: 330x67 - 2
- dropped: download failed: image too small: 330x15 - 2
- dropped: download failed: image too small: 330x16 - 2
- dropped: download failed: image too small: 330x7 - 2
- dropped: download failed: image too small: 330x20 - 2
- dropped: download failed: image too small: 330x95 - 2
- dropped: download failed: image too small: 330x58 - 2
- dropped: download failed: image too small: 330x11 - 2
- dropped: download failed: image too small: 330x24 - 2
- dropped: download failed: image too small: 330x57 - 2
- dropped: download failed: image too small: 330x27 - 2
- dropped: download failed: image too small: 330x13 - 2
- dropped: download failed: image too small: 330x50 - 1
- dropped: download failed: image too small: 330x60 - 1
- dropped: download failed: image too small: 330x55 - 1
- dropped: download failed: image too small: 80x108 - 1
- dropped: download failed: image too small: 330x29 - 1
- dropped: download failed: image too small: 330x76 - 1
- dropped: download failed: image too small: 330x30 - 1
- dropped: download failed: image too small: 330x22 - 1
- dropped: download failed: image too small: 330x68 - 1
- dropped: download failed: image too small: 235x95 - 1
- dropped: download failed: image too small: 330x41 - 1
- dropped: download failed: image too small: 330x96 - 1
- dropped: download failed: image too small: 330x25 - 1
- dropped: download failed: image too small: 330x18 - 1
- dropped: download failed: image too small: 330x66 - 1
- dropped: download failed: image too small: 330x21 - 1
- dropped: download failed: image too small: 330x26 - 1
- dropped: download failed: image too small: 330x9 - 1
- dropped: download failed: image too small: 330x8 - 1
- dropped: download failed: image too small: 330x88 - 1
- dropped: download failed: image too small: 330x28 - 1
- dropped: download failed: image too small: 330x6 - 1
- dropped: download failed: image too small: 330x71 - 1
- dropped: download failed: image too small: 330x87 - 1
- dropped: download failed: image too small: 330x44 - 1
- dropped: download failed: image too small: 330x72 - 1
- dropped: download failed: image too small: 330x65 - 1
- dropped: download failed: image too small: 330x23 - 1
- dropped: download failed: image too small: 330x81 - 1
- dropped: download failed: image too small: 330x69 - 1
- dropped: download failed: image too small: 330x32 - 1
