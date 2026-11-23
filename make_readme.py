"""Generate README.md for jlpt_n4.db from the database contents."""

import json
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "jlpt_n4.db")
OUT = os.path.join(HERE, "README.md")


def main():
    con = sqlite3.connect(DB)
    meta = dict(con.execute("SELECT key, value FROM meta").fetchall())
    sources = con.execute("SELECT name, purpose, license, url FROM sources ORDER BY name").fetchall()
    counts = json.loads(meta.get("counts_json", "{}"))
    coverage = json.loads(meta.get("ru_coverage", "{}"))
    integrity = json.loads(meta.get("integrity_json", "{}"))
    n_tags = con.execute("SELECT count(*) FROM grammar_tags").fetchone()[0]
    n_pos = con.execute("SELECT count(*) FROM pos_codes").fetchone()[0]
    rowcount = {}
    for (name,) in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        " AND name NOT LIKE '%_fts' ORDER BY name"
    ):
        rowcount[name] = con.execute("SELECT count(*) FROM %s" % name).fetchone()[0]
    tables = list(rowcount)
    views = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")]
    con.close()

    src_rows = "\n".join("| %s | %s | %s | [%s](%s) |" % (n, p, l, n, u) for n, p, l, u in sources)

    text = f"""# База данных «Японский язык — JLPT N4» (SQLite)

Готовая база для сайта: **{counts.get('vocab',0)} слов**, **{counts.get('kanji_total',0)} кандзи**
({counts.get('kanji_core',0)} из списка N5+N4 и {counts.get('kanji_extra',0)} тех, что встречаются в лексике N4)
и **{counts.get('grammar',0)} грамматических структур** уровня **N4** вместе с обязательной базой **N5**.
Всё с чтениями (кана + ромадзи), значениями на английском и русском, примерами предложений и связями
«слово ↔ кандзи», «грамматика ↔ слово».

Файл: `jlpt_n4.db` (SQLite 3, ~2 МБ). Пересборка: `python build_db.py && python merge_ru.py && python verify_db.py`.
Сайт для этой базы — в папке `docs/`, его обновление: `python export_site.py` (подробнее ниже).

## Что внутри

| Таблица | Что хранится | Строк |
|---|---|---|
| `vocab` | Слова: кандзи, кана-чтение, ромадзи, уровень, часть речи, значения en/ru, кол-во примеров, сумма черт | {rowcount['vocab']} |
| `vocab_examples` | Примеры предложений к словам (ja, furigana, en, ru, id Tatoeba) | {rowcount['vocab_examples']} |
| `vocab_pos` | Связь слова с кодами частей речи | {rowcount['vocab_pos']} |
| `vocab_kanji` | Какие кандзи входят в слово и на какой позиции | {rowcount['vocab_kanji']} |
| `kanji` | Кандзи: уровень, черточки, школьный класс, частотность, радикал, онъёмы/кунъёмы/нанори, значения en/ru | {rowcount['kanji']} |
| `kanji_readings` | Все чтения кандзи отдельными строками (поиск по чтению) | {rowcount['kanji_readings']} |
| `kanji_words` | Слова, в которых встречается кандзи (ссылка на `vocab`, если слово есть в базе) | {rowcount['kanji_words']} |
| `grammar` | Грамматические структуры: паттерн, чтение, ромадзи, уровень, значение, образование, заметки, теги | {rowcount['grammar']} |
| `grammar_examples` | Примеры к правилам (ja, furigana, en, ru) | {rowcount['grammar_examples']} |
| `grammar_tags` / `grammar_tag_links` | Теги правил ({n_tags}) и их связь с правилами | {n_tags} / {rowcount['grammar_tag_links']} |
| `grammar_related_vocab` | Слова из примеров правила — для перелинковки страниц | {rowcount['grammar_related_vocab']} |
| `pos_codes` | Справочник частей речи JMdict с русскими названиями | {n_pos} |
| `jlpt_levels` | Справочник уровней N5…N1 | {rowcount['jlpt_levels']} |
| `sources`, `meta` | Атрибуция данных и служебная информация | {rowcount['sources']} / {rowcount['meta']} |

Виртуальные таблицы полнотекстового поиска: **`vocab_fts`** и **`grammar_fts`** (FTS5) — ищут по кандзи,
кане, ромадзи и значениям (в том числе по-русски).
Готовые представления: `v_vocab`, `v_kanji`, `v_grammar`.

Индексы: `vocab(word, reading, romaji, level, jmdict_id)`, `kanji(level, in_core_list, radical_number, freq)`,
`kanji_readings(reading)`, `grammar(level, romaji)`, индексы по внешним ключам примеров.

## Примеры запросов

```sql
-- Страница слова: карточка со всеми данными
SELECT v.word, v.reading, v.romaji, v.meaning_ru, v.meanings_en,
       (SELECT group_concat(pc.name_ru, ', ')
          FROM vocab_pos vp JOIN pos_codes pc ON pc.code = vp.code
         WHERE vp.vocab_id = v.id) AS part_of_speech
  FROM vocab v WHERE v.word = '会う';

-- Примеры предложения для слова
SELECT ja, furigana, ru FROM vocab_examples WHERE vocab_id = 'ada066edfd' ORDER BY ord;

-- Кандзи слова
SELECT k.character, k.strokes, k.onyomi, k.kunyomi, k.meaning_ru
  FROM vocab_kanji vk JOIN kanji k ON k.character = vk.character
 WHERE vk.vocab_id = 'ada066edfd' ORDER BY vk.position;

-- Поиск по любому написанию (кана, ромадзи, русский)
SELECT word, reading, romaji, meaning_ru FROM vocab
 WHERE reading LIKE '%あ%' OR romaji LIKE 'a%' OR meaning_ru LIKE '%встреч%' LIMIT 20;

-- Полный текстовый поиск (FTS5)
SELECT v.word, v.reading, v.meaning_ru
  FROM vocab_fts f JOIN vocab v ON v.rowid = f.rowid
 WHERE vocab_fts MATCH 'стол';

-- Список слов уровня N4, только глаголы
SELECT v.word, v.reading, v.meaning_ru FROM vocab v
  JOIN vocab_pos vp ON vp.vocab_id = v.id
 WHERE v.level = 'N4' AND vp.code LIKE 'v%' ORDER BY v.reading;

-- Кандзи уровня N4, отсортированные по черточкам
SELECT character, strokes, onyomi, kunyomi, meaning_ru FROM kanji
 WHERE level = 'N4' ORDER BY strokes, character;

-- Поиск кандзи по чтению (например, «カイ»)
SELECT DISTINCT k.character, k.meaning_ru
  FROM kanji_readings kr JOIN kanji k ON k.character = kr.character
 WHERE kr.reading LIKE '%カイ%';

-- Грамматика N4 по теме «обязательство»
SELECT g.pattern, g.formation, g.meaning_ru, g.notes_ru
  FROM grammar g JOIN grammar_tag_links l ON l.grammar_id = g.id
 WHERE g.level = 'N4' AND l.tag = 'obligation';

-- Случайное слово для карточки «слово дня»
SELECT word, reading, romaji, meaning_ru FROM vocab
 ORDER BY RANDOM() LIMIT 1;

-- Прогресс изучения (создайте свою таблицу поверх базы)
CREATE TABLE IF NOT EXISTS user_progress (
    user_id  INTEGER NOT NULL,
    item_id  TEXT NOT NULL,          -- vocab.id или grammar.id
    kind     TEXT NOT NULL,          -- 'vocab' | 'kanji' | 'grammar'
    correct  INTEGER DEFAULT 0,
    wrong    INTEGER DEFAULT 0,
    updated  TEXT,
    PRIMARY KEY (user_id, item_id, kind)
);
```

Подключение из Python:

```python
import sqlite3
con = sqlite3.connect("jlpt_n4.db")
con.row_factory = sqlite3.Row
rows = con.execute("SELECT word, reading FROM vocab WHERE level='N4' LIMIT 10").fetchall()
```

## Происхождение данных и лицензия

| Источник | Для чего | Лицензия | Ссылка |
|---|---|---|---|
{src_rows}

База является производной работой и распространяется под **CC BY-SA 4.0**. Обязательная атрибуция:

> Contains data from [OpenJLPT](https://github.com/evanclan/OpenJLPT) (CC BY-SA 4.0), which uses
> JMdict and KANJIDIC2 (EDRDG), Jonathan Waller's JLPT lists, and Tatoeba.

Если вы публикуете базу или её часть на сайте, укажите эту строку (например, в подвале или на странице
«О данных») и сохраните возможность скачать исходные данные.

## Русские переводы

Русские значения и переводы примеров добавлены при сборке этой базы автоматически
(литературный перевод с японского и английского оригинала) и **не являются частью словарных
источников**: их стоит вычитать редактором. Покрытость на момент сборки: слова {coverage.get('vocab', 0)}/{counts.get('vocab',0)},
кандзи {coverage.get('kanji', 0)}/{counts.get('kanji_total',0)}, грамматика {coverage.get('grammar', 0)}/{counts.get('grammar',0)}.
Поля `meaning_ru`, `notes_ru`, `formation_ru`, `ru` в примерах — русские; поля `meanings_en`,
`meaning_en`, `notes_en`, `en` — из исходных словарей.

## Что важно знать про уровни JLPT

Организаторы JLPT (Japan Foundation) **не публикуют** официальных списков слов, кандзи и грамматики.
Уровни в базе взяты из общепринятых списков Джонатана Уоллера (tanos.co.uk) и из консенсуса
учебных материалов — это надёжная, но всё же приблизительная оценка. Кандзи, которых нет ни в одном
списке, но которые встречаются в лексике N4 (например 味噌, 噛む, 賑やか, 飴), помечены
`in_core_list = 0` и `used_in_vocab = 1`.

## Сайт для этой базы (`docs/`)

Готовый статичный сайт: современный дизайн в японском аниме-стиле (сакура + индиго, падающие лепестки,
руби-текст над кандзи) и **12 режимов тренировки запоминания** — для слов, кандзи и грамматики.

Никакого сервера и никаких библиотек: чистые HTML/CSS/JS, всё содержимое базы выгружено в JSON-чанки,
которые подгружаются по мере надобности. Папка называется `docs/` — это стандартное место для GitHub Pages,
но сайт работает и на любом другом статичном хостинге (Netlify, Cloudflare Pages, обычный shared-хостинг)
и даже при открытии `docs/index.html` с диска.

```
docs/
├── index.html        страница-обёртка, навигация, подвал с атрибуцией
├── css/style.css     тема, карточки, анимации, адаптивность (телефон/планшет/ПК)
├── js/data.js        загрузчик чанков, хранилище прогресса, интервальные повторения
├── js/train.js       12 режимов тренировки и движок сессии
├── js/app.js         страницы: Главная, Слова, Кандзи, Грамматика, Тренажёр, Прогресс
└── data/*.js         слова N5, слова N4, кандзи, грамматика, служебная сводка (~1,5 МБ)
```

### Страницы

| Адрес | Что там есть |
|---|---|
| `#/` | главная со счётчиками базы и кнопкой «случайная карточка» |
| `#/words` | 1304 слова: уровень, часть речи, чтения, ромадзи, переводы, примеры с переводом; поиск по кане/кириллице/ромадзи, фильтр по уровню и части речи; кнопка «Тренировать этот набор» |
| `#/kanji` | 725 кандзи: поиск, фильтр по уровню и школьному классу, счётчик черточек |
| `#/kanji/白` | страница иероглифа: онъёмы и кунъёмы с руби, значения, черточки, класс, частотность, слова с этим кандзи |
| `#/grammar` | 179 конструкций: паттерн, чтение, ромадзи, русское значение, способ образования, заметки, теги, примеры с переводом |
| `#/train` | тренажёр: выбор материала, уровня, количества вопросов (10/20/40) и фокуса (смесь / новые / к повторению / слабые) |
| `#/progress` | профиль: выученные материалы, точность, серии, последние тренировки, уровни памяти |

### Режимы тренировки

* Слова: карточки · слово → перевод · перевод → слово · «прочитай слово» (ввод каной или ромадзи).
* Кандзи: карточки · выбрать чтение · выбрать значение · сколько черточек.
* Грамматика: карточки · конструкция → смысл · смысл → конструкция · «что за конструкция в примере».

Ответы с руби, примеры с переводом, звуковые сигналы (отключаются кнопкой в шапке). Горячие клавиши:
`1…4` — вариант ответа, `Пробел` — перевернуть карточку, `Enter` — «Далее».

### Прогресс и повторения

Прогресс хранится в `localStorage` браузера (ключ `jlpt4.progress.v1`) — один профиль, без аккаунтов и
без сервера. Повторения по методу Лейтнера: 6 коробок, интервалы 30 мин → 6 ч → 1 день → 3 дня → 1 неделя
→ 3 недели; новое и ошибочное поднимается в начало очереди, «слабые» можно тренировать отдельно.
Кнопка «Сбросить прогресс» на странице «Прогресс».

### Публикация на GitHub Pages

На машине не нужен Git — файлы можно загрузить прямо в браузере.

**Вариант А (проще всего, папки не нужны):**

```bash
python prepare_upload.py
```

Скрипт собирает папку `github-upload/` — **всё содержимое репозитория одним списком из 40 файлов,
без папок**: сайт (`index.html`, `style.css`, `data.js`, `train.js`, `app.js`, `meta.js`, `kanji.js`,
`grammar.js`, `vocabN5.js`, `vocabN4.js`), готовая база `jlpt_n4.db`, скрипты сборки, исходные данные
OpenJLPT (`vocab_n5.json`, `kanji_n4.json`, …, `LICENSE`, `NOTICE.md`) и отчёт `ru_report.json`.
`build_db.py` читает исходники и в плоском виде, так что база пересобирается прямо из этой папки.
Однако `merge_ru.py` (русские переводы) требует пакетов `exports/ru/` — они остаются локально, поэтому
полную пересборку с переводами делайте у себя, а на GitHub перезагружайте готовые файлы.

1. github.com → **New repository** → имя, например `jlpt-n4` → **Public** → Create repository.
2. **Add file → Upload files** → перетащить **все файлы из `github-upload/`** (40 файлов, без папок)
   → **Commit changes**.
3. **Settings → Pages** → Source: **Deploy from a branch**, branch `main`, папка **`/`** → **Save**.
4. Через 1–2 минуты сайт открывается по адресу `https://<ваш-логин>.github.io/jlpt-n4/`.


**Вариант Б (если хочется сохранить папку `docs`):** загрузите папку `docs` целиком так, чтобы в
репозитории остались `docs/index.html`, `docs/css/`, `docs/js/`, `docs/data/`, и в Pages выберите
папку **`/docs`**. Если браузер раскладывал файлы по корню репозитория без папок, такой вариант не
подойдёт — берите вариант А.

В `github-upload/` уже лежат скрипты сборки и исходные данные, догружать ничего не нужно. Не входят
только `exports/` — промежуточные пакеты перевода и отчёты: готовые русские переводы уже в `jlpt_n4.db`,
а сами пакеты остаются локально (они перечислены в `.gitignore`).

Дальнейшее обновление: правите базу, запускаете `python export_site.py` и затем
`python prepare_upload.py`, после чего перезагружаете изменённые файлы в репозиторий
(Add file → Upload files → Commit changes) — Pages обновится сам.

### Выкладка на другой хостинг

1. Скопируйте папку `docs/` целиком (важно, чтобы `data/` лежала рядом с `index.html`).
2. Открывайте `index.html` — сервер не нужен; PHP, Node и база на хостинге не требуются.
3. Атрибуция уже в подвале сайта — сохраните её (CC BY-SA 4.0).

### Как обновить сайт после правок в базе

```bash
python build_db.py && python merge_ru.py && python verify_db.py && python export_site.py
```

`export_site.py` перечитывает `jlpt_n4.db` и заново пишет `docs/data/*.js` — код сайта при этом менять не нужно.

## Структура файлов

```
jlpt_n4.db          готовая база SQLite
docs/               готовый сайт: HTML + CSS + JS + данные (выкладывается как есть, Pages: /docs)
prepare_upload.py   сборка папки github-upload/ — тот же сайт плоско, для загрузки без папок (Pages: /)
github-upload/      готовый набор файлов для репозитория (создаётся prepare_upload.py)
build_db.py         сборка базы из исходных JSON
merge_ru.py         добавление русских переводов и проверка целостности
verify_db.py        проверка базы (количества, связи, поиск)
export_site.py      выгрузка базы в статичный сайт (docs/data/*.js)
make_readme.py      генерация этого README из базы
qa_ru.py            проверка русских переводов
_sources/openjlpt/  исходные данные OpenJLPT (JSON) + лицензии
exports/            пакеты перевода и отчёты (exports/ru_report.json)
README.md           этот файл
```

## Идеи доработки

* Порядок черт кандзи: подключите KanjiVG (CC BY-SA 3.0) — поле `kanji.stroke_order_svg` уже предусмотрено.
* Аудио произношения: по `vocab.jmdict_id` можно связаться с аудиоресурсами.
* Таблицы прогресса и повторений (SRS) создавайте отдельно, ссылка на `vocab.id` / `grammar.id` стабильна.
* Если нужен сервер MySQL/PostgreSQL — схема переносится почти один в один (JSON-поля оставьте TEXT или
  переведите в JSONB).
"""

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("README written:", OUT, len(text), "chars")
    print("integrity:", json.dumps(integrity, ensure_ascii=False))


if __name__ == "__main__":
    main()
