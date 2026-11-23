"""Build a SQLite database for a JLPT N4 Japanese-learning site.

Data source: OpenJLPT dataset (CC BY-SA 4.0) — vocabulary, kanji and grammar for
JLPT N5 + N4, built from JMdict / KANJIDIC2 / Jonathan Waller's lists / Tatoeba.

Run:  python build_db.py
Output: jlpt_n4.db  (+ exports/_pending_*.json batches awaiting Russian translation)
"""

import json
import os
import re
import sqlite3
import sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_sources", "openjlpt")
OUT_DIR = HERE
DB_PATH = os.path.join(OUT_DIR, "jlpt_n4.db")
EXPORT_DIR = os.path.join(OUT_DIR, "exports")

# Исходники могут лежать и плоско рядом со скриптом (так их собирает prepare_upload.py).
SRC_DIRS = [SRC, os.path.join(HERE, "_sources"), HERE]


def find_source(name):
    """Найти исходный файл в папке _sources/openjlpt, в _sources или рядом со скриптом."""
    for folder in SRC_DIRS:
        path = os.path.join(folder, name)
        if os.path.exists(path):
            return path
    return None

BUILD_VERSION = "1.0.0"

# ---------------------------------------------------------------- schema ----

SCHEMA = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS meta;
DROP TABLE IF EXISTS sources;
DROP TABLE IF EXISTS jlpt_levels;
DROP TABLE IF EXISTS pos_codes;
DROP TABLE IF EXISTS vocab;
DROP TABLE IF EXISTS vocab_pos;
DROP TABLE IF EXISTS vocab_examples;
DROP TABLE IF EXISTS vocab_kanji;
DROP TABLE IF EXISTS kanji;
DROP TABLE IF EXISTS kanji_readings;
DROP TABLE IF EXISTS kanji_words;
DROP TABLE IF EXISTS grammar;
DROP TABLE IF EXISTS grammar_tags;
DROP TABLE IF EXISTS grammar_examples;
DROP TABLE IF EXISTS grammar_related_vocab;

CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE sources (
    name    TEXT PRIMARY KEY,
    purpose TEXT NOT NULL,
    license TEXT NOT NULL,
    url     TEXT NOT NULL
);

CREATE TABLE jlpt_levels (
    level   TEXT PRIMARY KEY,           -- N5 .. N1
    label_ru TEXT NOT NULL,
    label_en TEXT NOT NULL,
    sort    INTEGER NOT NULL
);

CREATE TABLE pos_codes (
    code    TEXT PRIMARY KEY,           -- JMdict part-of-speech code
    name_en TEXT NOT NULL,
    name_ru TEXT NOT NULL
);

-- ---------------------------------------------------------- vocabulary ----
CREATE TABLE vocab (
    id             TEXT PRIMARY KEY,                 -- stable OpenJLPT id
    word           TEXT NOT NULL,                    -- headword (kanji/kana)
    reading        TEXT NOT NULL,                    -- kana reading
    romaji         TEXT NOT NULL,                    -- Hepburn romanisation
    level          TEXT NOT NULL REFERENCES jlpt_levels(level),
    jmdict_id      INTEGER,                          -- JMdict ent_seq
    meanings_en    TEXT NOT NULL,                    -- JSON array of English glosses
    meaning_ru     TEXT,                             -- Russian gloss (comma separated)
    other_forms    TEXT,                             -- JSON array of alternative spellings
    other_readings TEXT,                             -- JSON array of alternative readings
    has_kanji      INTEGER NOT NULL DEFAULT 0,
    is_kana_only   INTEGER NOT NULL DEFAULT 0,
    example_count  INTEGER NOT NULL DEFAULT 0,
    stroke_sum     INTEGER,                          -- total strokes of kanji in the word
    search_text    TEXT NOT NULL                     -- all searchable forms in one string
);

CREATE INDEX idx_vocab_word        ON vocab(word);
CREATE INDEX idx_vocab_reading     ON vocab(reading);
CREATE INDEX idx_vocab_romaji      ON vocab(romaji);
CREATE INDEX idx_vocab_level       ON vocab(level);
CREATE INDEX idx_vocab_jmdict      ON vocab(jmdict_id);

CREATE TABLE vocab_pos (
    vocab_id TEXT NOT NULL REFERENCES vocab(id) ON DELETE CASCADE,
    code     TEXT NOT NULL REFERENCES pos_codes(code),
    PRIMARY KEY (vocab_id, code)
);

CREATE TABLE vocab_examples (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    vocab_id   TEXT NOT NULL REFERENCES vocab(id) ON DELETE CASCADE,
    ja         TEXT NOT NULL,
    furigana   TEXT,                    -- {kanji|reading} notation, NULL if unavailable
    en         TEXT,
    ru         TEXT,
    tatoeba_id INTEGER,
    ord        INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX idx_vexamples_vocab ON vocab_examples(vocab_id);

CREATE TABLE vocab_kanji (
    vocab_id  TEXT NOT NULL REFERENCES vocab(id) ON DELETE CASCADE,
    character TEXT NOT NULL REFERENCES kanji(character) ON DELETE CASCADE,
    position  INTEGER NOT NULL,
    PRIMARY KEY (vocab_id, character, position)
);

-- -------------------------------------------------------------- kanji ----
CREATE TABLE kanji (
    character        TEXT PRIMARY KEY,
    level            TEXT NOT NULL REFERENCES jlpt_levels(level),  -- official list level
    in_core_list     INTEGER NOT NULL DEFAULT 0,   -- part of the N5+N4 kanji list
    used_in_vocab    INTEGER NOT NULL DEFAULT 0,   -- appears in an N5/N4 vocabulary word
    supplementary    INTEGER NOT NULL DEFAULT 0,   -- added on top of Waller's lists
    strokes          INTEGER,
    grade            INTEGER,                      -- school grade (1-6, 8 = other joyo)
    freq             INTEGER,                      -- newspaper frequency rank
    radical          TEXT,
    radical_number   INTEGER,
    onyomi           TEXT,                          -- JSON array (katakana)
    kunyomi          TEXT,                          -- JSON array (hiragana, . = okurigana)
    nanori           TEXT,                          -- JSON array (name readings)
    meanings_en      TEXT NOT NULL,                 -- JSON array
    meaning_ru       TEXT,
    source_note      TEXT,                          -- provenance when not from OpenJLPT lists
    stroke_order_svg TEXT                           -- reserved for KanjiVG asset path
);
CREATE INDEX idx_kanji_level    ON kanji(level);
CREATE INDEX idx_kanji_core     ON kanji(in_core_list, level);
CREATE INDEX idx_kanji_radical  ON kanji(radical_number);
CREATE INDEX idx_kanji_freq     ON kanji(freq);

CREATE TABLE kanji_readings (
    character   TEXT NOT NULL REFERENCES kanji(character) ON DELETE CASCADE,
    kind        TEXT NOT NULL CHECK (kind IN ('on', 'kun', 'nanori')),
    reading     TEXT NOT NULL,
    reading_kana TEXT NOT NULL,       -- kun reading with okurigana markers stripped
    PRIMARY KEY (character, kind, reading)
);
CREATE INDEX idx_kreadings_reading ON kanji_readings(reading);

CREATE TABLE kanji_words (
    character TEXT NOT NULL REFERENCES kanji(character) ON DELETE CASCADE,
    word      TEXT NOT NULL,
    vocab_id  TEXT REFERENCES vocab(id) ON DELETE SET NULL,
    PRIMARY KEY (character, word)
);

-- ------------------------------------------------------------ grammar ----
CREATE TABLE grammar (
    id          TEXT PRIMARY KEY,                   -- stable slug
    pattern     TEXT NOT NULL,                      -- e.g. 〜てもいい
    reading     TEXT,                               -- kana form when pattern has kanji
    romaji      TEXT NOT NULL,
    level       TEXT NOT NULL REFERENCES jlpt_levels(level),
    meaning_en  TEXT NOT NULL,
    meaning_ru  TEXT,
    formation   TEXT NOT NULL,                      -- how it attaches
    formation_ru TEXT,
    notes_en    TEXT,
    notes_ru    TEXT,
    tags_text   TEXT,                               -- comma separated tag slugs
    example_count INTEGER NOT NULL DEFAULT 0,
    search_text TEXT NOT NULL
);
CREATE INDEX idx_grammar_level  ON grammar(level);
CREATE INDEX idx_grammar_romaji ON grammar(romaji);

CREATE TABLE grammar_tags (
    tag      TEXT PRIMARY KEY,
    name_en  TEXT NOT NULL,
    name_ru  TEXT NOT NULL
);

CREATE TABLE grammar_tag_links (
    grammar_id TEXT NOT NULL REFERENCES grammar(id) ON DELETE CASCADE,
    tag        TEXT NOT NULL REFERENCES grammar_tags(tag),
    PRIMARY KEY (grammar_id, tag)
);

CREATE TABLE grammar_examples (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    grammar_id TEXT NOT NULL REFERENCES grammar(id) ON DELETE CASCADE,
    ja         TEXT NOT NULL,
    furigana   TEXT,
    en         TEXT,
    ru         TEXT,
    tatoeba_id INTEGER,
    ord        INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX idx_gexamples_grammar ON grammar_examples(grammar_id);

-- grammar point <-> vocabulary word used in its examples
CREATE TABLE grammar_related_vocab (
    grammar_id TEXT NOT NULL REFERENCES grammar(id) ON DELETE CASCADE,
    vocab_id   TEXT NOT NULL REFERENCES vocab(id) ON DELETE CASCADE,
    PRIMARY KEY (grammar_id, vocab_id)
);

-- ------------------------------------------------------------- views ----
CREATE VIEW v_vocab AS
SELECT v.id, v.word, v.reading, v.romaji, v.level, v.meanings_en, v.meaning_ru,
       (SELECT group_concat(pc.name_ru, ', ')
          FROM vocab_pos vp JOIN pos_codes pc ON pc.code = vp.code
         WHERE vp.vocab_id = v.id) AS pos_ru,
       (SELECT group_concat(vp.code, ' ')
          FROM vocab_pos vp WHERE vp.vocab_id = v.id) AS pos_codes,
       v.example_count, v.has_kanji, v.jmdict_id
  FROM vocab v;

CREATE VIEW v_kanji AS
SELECT k.character, k.level, k.in_core_list, k.used_in_vocab, k.supplementary, k.strokes,
       k.grade, k.freq, k.radical, k.radical_number, k.onyomi, k.kunyomi, k.meanings_en,
       k.meaning_ru,
       (SELECT group_concat(kr.reading, ' / ') FROM kanji_readings kr
         WHERE kr.character = k.character AND kr.kind IN ('on','kun')) AS readings
  FROM kanji k;

CREATE VIEW v_grammar AS
SELECT g.id, g.pattern, g.reading, g.romaji, g.level, g.meaning_en, g.meaning_ru,
       g.formation, g.formation_ru, g.notes_en, g.notes_ru, g.tags_text,
       g.example_count
  FROM grammar g;
"""

POS_CODES = {
    "n": ("noun", "существительное"),
    "n-suf": ("noun suffix", "существительное (суффикс)"),
    "n-pref": ("noun prefix", "существительное (приставка)"),
    "pref": ("prefix", "приставка"),
    "suf": ("suffix", "суффикс"),
    "nadj": ("noun adjectival", "именное прилагательное"),
    "adj-i": ("i-adjective", "прилагательное на -い"),
    "adj-ix": ("irregular i-adjective", "неправильное прилагательное на -い"),
    "adj-na": ("na-adjective", "прилагательное на -な"),
    "adj-no": ("no-adjective", "прилагательное на -の"),
    "adj-pn": ("pre-noun adjectival", "предыменное прилагательное"),
    "adj-f": ("noun or verb modifier", "определение от существительного/глагола"),
    "adj": ("adjective", "прилагательное"),
    "adv": ("adverb", "наречие"),
    "adv-to": ("adverb taking to", "наречие с を/に"),
    "adv-n": ("adverbal noun", "наречное существительное"),
    "adv-wo": ("adverbal noun taking wo", "наречное существительное с を"),
    "v1": ("ichidan verb", "глагол 1 группы (ичидан)"),
    "v1-s": ("ichidan verb (suru)", "глагол 1 группы (суру)"),
    "v2a-s": ("nidan verb -aru", "глагол 2 группы (-ару)"),
    "v4": ("yodan verb -u", "глагол 5 группы (-у)"),
    "v4b": ("yodan verb -buru", "глагол 5 группы (-буру)"),
    "v4g": ("yodan verb -guru", "глагол 5 группы (-гуру)"),
    "v4h": ("yodan verb -huru", "глагол 5 группы (-хуру)"),
    "v4m": ("yodan verb -mu", "глагол 5 группы (-му)"),
    "v4r": ("yodan verb -ru", "глагол 5 группы (-ру)"),
    "v4s": ("yodan verb -su", "глагол 5 группы (-су)"),
    "v4t": ("yodan verb -tsu", "глагол 5 группы (-цу)"),
    "v5": ("godan verb", "глагол 5 группы"),
    "v5aru": ("godan verb -aru", "глагол 5 группы (-ару)"),
    "v5b": ("godan verb -bu", "глагол 5 группы (-бу)"),
    "v5g": ("godan verb -gu", "глагол 5 группы (-гу)"),
    "v5k": ("godan verb -ku", "глагол 5 группы (-ку)"),
    "v5k-s": ("godan verb -kaku/-gaku", "глагол 5 группы (-каку/-гаку)"),
    "v5m": ("godan verb -mu", "глагол 5 группы (-му)"),
    "v5n": ("godan verb -nu", "глагол 5 группы (-ну)"),
    "v5r": ("godan verb -ru", "глагол 5 группы (-ру)"),
    "v5r-i": ("irregular godan verb -ru", "неправильный глагол 5 группы (-ру)"),
    "v5s": ("godan verb -su", "глагол 5 группы (-су)"),
    "v5t": ("godan verb -tsu", "глагол 5 группы (-цу)"),
    "v5u": ("godan verb -u", "глагол 5 группы (-у)"),
    "v5u-s": ("godan verb -asu/-wasu", "глагол 5 группы (-асу/-васу)"),
    "v5vu": ("godan verb -vu", "глагол 5 группы (-ву)"),
    "v6": ("nidan verb", "глагол 2 группы"),
    "vk": ("kuru verb", "глагол 来る"),
    "vs": ("suru verb", "глагол する"),
    "vs-i": ("suru verb (irregular)", "глагол する (неправильный)"),
    "vt": ("transitive verb", "переходный глагол"),
    "vi": ("intransitive verb", "непереходный глагол"),
    "vtn": ("transitive noun verb", "переходный глагол-существительное"),
    "vin": ("intransitive noun verb", "непереходный глагол-существительное"),
    "vst": ("suru verb transitive", "переходный глагол する"),
    "vst": ("suru verb transitive", "переходный глагол する"),
    "vsi": ("suru verb intransitive", "непереходный глагол する"),
    "aux-v": ("auxiliary verb", "вспомогательный глагол"),
    "aux-adj": ("auxiliary adjective", "вспомогательное прилагательное"),
    "aux": ("auxiliary", "вспомогательное слово"),
    "ctr": ("counter", "счётный суффикс"),
    "conj": ("conjunction", "союз"),
    "int": ("interjection", "междометие"),
    "exp": ("expression", "выражение"),
    "pn": ("pronoun", "местоимение"),
    "num": ("numeric", "числительное"),
    "cop": ("copula", "связка"),
    "unc": ("unclassified", "не классифицировано"),
    "prt": ("particle", "частица"),
    "par": ("particle", "частица"),
}

GRAMMAR_TAGS = {
    "particle": ("particle", "частица"),
    "copula": ("copula", "связка"),
    "conjugation": ("conjugation", "спряжение"),
    "tense": ("tense", "время"),
    "negation": ("negation", "отрицание"),
    "politeness": ("politeness", "вежливость"),
    "request": ("request", "просьба"),
    "permission": ("permission", "разрешение"),
    "prohibition": ("prohibition", "запрет"),
    "obligation": ("obligation", "обязанность"),
    "necessity": ("necessity", "необходимость"),
    "desire": ("desire", "желание"),
    "ability": ("ability", "способность"),
    "possibility": ("possibility", "возможность"),
    "conjecture": ("conjecture", "предположение"),
    "hearsay": ("hearsay", "косвенное сообщение"),
    "appearance": ("appearance", "впечатление, видимость"),
    "comparison": ("comparison", "сравнение"),
    "condition": ("condition", "условие"),
    "concession": ("concession", "уступка"),
    "contrast": ("contrast", "противопоставление"),
    "reason": ("reason", "причина"),
    "purpose": ("purpose", "цель"),
    "result": ("result", "результат"),
    "time": ("time", "время"),
    "sequence": ("sequence", "последовательность"),
    "simultaneity": ("simultaneity", "одновременность"),
    "change": ("change", "изменение"),
    "decision": ("decision", "решение"),
    "experience": ("experience", "опыт"),
    "giving-receiving": ("giving & receiving", "давание и получение"),
    "honorific": ("honorific", "вежливые (почтительные) формы"),
    "humble": ("humble", "скромные формы"),
    "casual": ("casual", "разговорная форма"),
    "formal": ("formal", "формальная форма"),
    "written": ("written", "письменная форма"),
    "emphasis": ("emphasis", "усиление"),
    "limitation": ("limitation", "ограничение"),
    "addition": ("addition", "добавление"),
    "example": ("example", "пример"),
    "quotation": ("quotation", "цитата"),
    "question": ("question", "вопрос"),
    "suggestion": ("suggestion", "предложение"),
    "advice": ("advice", "совет"),
    "intention": ("intention", "намерение"),
    "attempt": ("attempt", "попытка"),
    "tendency": ("tendency", "тенденция"),
    "degree": ("degree", "степень"),
    "manner": ("manner", "образ действия"),
    "state": ("state", "состояние"),
    "completion": ("completion", "завершённость"),
    "regret": ("regret", "сожаление"),
    "surprise": ("surprise", "удивление"),
    "criticism": ("criticism", "критика"),
    "emotion": ("emotion", "эмоция"),
    "standpoint": ("standpoint", "точка зрения"),
    "topic": ("topic", "тема"),
    "relation": ("relation", "отношение"),
    "means": ("means", "средство"),
    "range": ("range", "диапазон"),
    "exclusion": ("exclusion", "исключение"),
    "invitation": ("invitation", "приглашение"),
    "command": ("command", "приказ"),
    "voice": ("voice", "залог"),
    "nominalization": ("nominalization", "субстантивация"),
    "demonstrative": ("demonstrative", "указательное слово"),
    "quantity": ("quantity", "количество"),
    "exclamation": ("exclamation", "восклицание"),
    "recollection": ("recollection", "воспоминание"),
    "wish": ("wish", "пожелание"),
}

LEVELS = {
    "N5": ("N5 — базовый", "N5 (basic)", 5),
    "N4": ("N4 — начально-средний", "N4 (elementary)", 4),
    "N3": ("N3 — средний", "N3 (intermediate)", 3),
    "N2": ("N2 — средне-продвинутый", "N2 (upper-intermediate)", 2),
    "N1": ("N1 — продвинутый", "N1 (advanced)", 1),
}

KANJI_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
FURI_RE = re.compile(r"\{([^|{}]+)\|([ぁ-ゖー]+)\}")


def load_json(name):
    if not name.endswith(".json"):
        name += ".json"
    path = find_source(name)
    if path is None:
        sys.exit("Нет исходного файла %s (ожидается в _sources/openjlpt/)" % name)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def jdump(obj):
    return json.dumps(obj, ensure_ascii=False)


def strip_furigana(text):
    return FURI_RE.sub(lambda m: m.group(1), text or "")


def reading_core(kun):
    """KANJIDIC2 kun'yomi 'た.べる' -> 'べる' style core; keep as-is for prefixes."""
    return kun.replace(".", "").replace("-", "")


def build_kanji_strokes(kanji_by_char):
    return {ch: (e.get("strokes") or 0) for ch, e in kanji_by_char.items()}


def main():
    raw_meta = load_json("meta")
    vocab_raw = load_json("vocab_n5") + load_json("vocab_n4")
    core_kanji_raw = load_json("kanji_n5") + load_json("kanji_n4")
    other_kanji_raw = (
        load_json("kanji_n3") + load_json("kanji_n2") + load_json("kanji_n1")
    )
    grammar_raw = load_json("grammar_n5") + load_json("grammar_n4")

    # ---------------------------------------------------- kanji union ----
    kanji_by_char = OrderedDict()
    for e in core_kanji_raw:
        kanji_by_char[e["character"]] = dict(e, _core=True)
    core_chars = set(kanji_by_char)

    # kanji that appear inside N5/N4 vocabulary words but are not in the
    # N5+N4 kanji list: pull them from the higher-level lists so that every
    # character a learner meets at N4 has readings and meanings in the DB.
    vocab_chars = set()
    for v in vocab_raw:
        for ch in v["word"]:
            if KANJI_RE.match(ch):
                vocab_chars.add(ch)
    extra = [e for e in other_kanji_raw if e["character"] in vocab_chars and e["character"] not in core_kanji_raw]
    missing = sorted(vocab_chars - core_chars - {e["character"] for e in other_kanji_raw})
    for e in extra:
        kanji_by_char[e["character"]] = dict(e, _core=False)

    # Characters that appear in N4 vocabulary but are in no JLPT list at all
    # (味噌, 噛む, 賑やか, 飴). KANJIDIC2 data fetched from kanjiapi.dev.
    extra4_path = find_source("kanji_extra4.json")
    if extra4_path and os.path.exists(extra4_path):
        priority = {"N5": 0, "N4": 1}
        with open(extra4_path, encoding="utf-8") as fh:
            for e in json.load(fh):
                ch = e["character"]
                if ch not in vocab_chars:
                    continue
                used = [v["level"] for v in vocab_raw if ch in v["word"]]
                e = dict(e, _core=False, _note=e.get("source_note"))
                if used:
                    e["level"] = min(used, key=lambda lv: priority.get(lv, 9))
                kanji_by_char[ch] = e

    kanji_source_note = {
        ch: e.get("_note") for ch, e in kanji_by_char.items() if e.get("_note")
    }

    # ------------------------------------------------------ open DB -----
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)

    con.executemany(
        "INSERT INTO jlpt_levels VALUES (?,?,?,?)",
        [(lv, ru, en, s) for lv, (ru, en, s) in LEVELS.items()],
    )
    con.executemany(
        "INSERT INTO sources VALUES (?,?,?,?)",
        [
            ("OpenJLPT", "Словарь, кандзи и грамматика JLPT N5–N4 (сборка)",
             "CC BY-SA 4.0", "https://github.com/evanclan/OpenJLPT"),
            ("Jonathan Waller (tanos.co.uk)", "Отнесение слов и кандзи к уровням JLPT, английские переводы слов",
             "CC BY 4.0", "https://www.tanos.co.uk/jlpt/"),
            ("JMdict (EDRDG)", "Идентификаторы слов, части речи, чтения и перевода",
             "CC BY-SA 4.0", "https://www.edrdg.org/jmdict/j_jmdict.html"),
            ("KANJIDIC2 (EDRDG)", "Чтения кандзи, значения, черточки, классы, радикалы, частотность",
             "CC BY-SA 4.0", "https://www.edrdg.org/wiki/KANJIDIC_Project.html"),
            ("Tatoeba", "Примеры предложений", "CC BY 2.0 FR", "https://tatoeba.org"),
            ("kanjiapi.dev (KANJIDIC2)",
             "Чтения и значения 4 кандзи, которых нет ни в одном списке JLPT "
             "(噌 味噌, 噛 噛む, 賑 賑やか, 飴 飴)",
             "CC BY-SA (данные KANJIDIC2, EDRDG)", "https://kanjiapi.dev"),
        ],
    )
    used_pos = set()
    for v in vocab_raw:
        used_pos.update(v.get("pos", []))
    inserted_pos = set()
    for code in sorted(used_pos):
        en, ru = POS_CODES.get(code, (code, code))
        con.execute("INSERT OR IGNORE INTO pos_codes VALUES (?,?,?)", (code, en, ru))
        inserted_pos.add(code)
    # keep the reference table complete even if not used at N4
    for code, (en, ru) in POS_CODES.items():
        if code not in inserted_pos:
            con.execute("INSERT OR IGNORE INTO pos_codes VALUES (?,?,?)", (code, en, ru))

    strokes = build_kanji_strokes(kanji_by_char)

    # ------------------------------------------------------- kanji ------
    for ch, e in kanji_by_char.items():
        kunyomi = e.get("kunyomi") or []
        con.execute(
            "INSERT INTO kanji (character, level, in_core_list, used_in_vocab, supplementary,"
            " strokes, grade, freq, radical, radical_number, onyomi, kunyomi, nanori,"
            " meanings_en, source_note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                ch, e["level"], 1 if e["_core"] else 0,
                1 if ch in vocab_chars else 0,
                1 if e.get("supplementary") else 0,
                e.get("strokes"), e.get("grade"), e.get("freq"),
                e.get("radical"), e.get("radical_number"),
                jdump(e.get("onyomi") or []), jdump(kunyomi), jdump(e.get("nanori") or []),
                jdump(e.get("meanings") or []), e.get("_note"),
            ),
        )
        for kind, values in (("on", e.get("onyomi") or []), ("kun", kunyomi), ("nanori", e.get("nanori") or [])):
            for r in values:
                con.execute(
                    "INSERT OR IGNORE INTO kanji_readings VALUES (?,?,?,?)",
                    (ch, kind, r, reading_core(r)),
                )

    # ------------------------------------------------------ vocab -------
    word_to_id = {}
    for v in vocab_raw:
        word = v["word"]
        has_kanji = 1 if KANJI_RE.search(word) else 0
        stroke_sum = None
        if has_kanji:
            chars = [c for c in word if KANJI_RE.match(c)]
            if all(c in strokes for c in chars):
                stroke_sum = sum(strokes[c] for c in chars)
        search = " ".join(
            [word, v["reading"], v["romaji"]]
            + (v.get("other_forms") or [])
            + (v.get("other_readings") or [])
            + v["meanings"]
        )
        con.execute(
            "INSERT INTO vocab (id, word, reading, romaji, level, jmdict_id, meanings_en,"
            " other_forms, other_readings, has_kanji, is_kana_only, example_count,"
            " stroke_sum, search_text) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                v["id"], word, v["reading"], v["romaji"], v["level"], v.get("jmdict_id"),
                jdump(v["meanings"]), jdump(v.get("other_forms") or []),
                jdump(v.get("other_readings") or []), has_kanji, 1 - has_kanji,
                len(v.get("examples") or []), stroke_sum, search,
            ),
        )
        word_to_id.setdefault(word, v["id"])
        for code in v.get("pos", []):
            con.execute("INSERT OR IGNORE INTO vocab_pos VALUES (?,?)", (v["id"], code))
        for i, ex in enumerate(v.get("examples") or [], start=1):
            con.execute(
                "INSERT INTO vocab_examples (vocab_id, ja, furigana, en, tatoeba_id, ord)"
                " VALUES (?,?,?,?,?,?)",
                (v["id"], ex["ja"], ex.get("furigana"), ex.get("en"), ex.get("tatoeba_id"), i),
            )
        if has_kanji:
            for pos, ch in enumerate(word):
                if KANJI_RE.match(ch) and ch in kanji_by_char:
                    con.execute(
                        "INSERT OR IGNORE INTO vocab_kanji VALUES (?,?,?)",
                        (v["id"], ch, pos),
                    )

    # ----------------------------------------- kanji -> example words ----
    for ch, e in kanji_by_char.items():
        for w in e.get("words") or []:
            con.execute(
                "INSERT OR IGNORE INTO kanji_words (character, word, vocab_id) VALUES (?,?,?)",
                (ch, w, word_to_id.get(w)),
            )

    # ----------------------------------------------------- grammar ------
    tags_seen = {t for g in grammar_raw for t in (g.get("tags") or [])}
    for tag in sorted(set(GRAMMAR_TAGS) | tags_seen):
        en, ru = GRAMMAR_TAGS.get(tag, (tag, tag))
        con.execute("INSERT OR IGNORE INTO grammar_tags VALUES (?,?,?)", (tag, en, ru))
    for g in grammar_raw:
        tags = g.get("tags") or []
        tags_seen.update(tags)
        search = " ".join(
            [g["pattern"], g.get("reading") or "", g["romaji"], g["meaning"]]
            + [ex["ja"] for ex in g.get("examples") or []]
        )
        con.execute(
            "INSERT INTO grammar (id, pattern, reading, romaji, level, meaning_en, formation,"
            " notes_en, tags_text, example_count, search_text) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                g["id"], g["pattern"], g.get("reading"), g["romaji"], g["level"],
                g["meaning"], g["formation"], g.get("notes"), ", ".join(tags),
                len(g.get("examples") or []), search,
            ),
        )
        for tag in tags:
            con.execute("INSERT OR IGNORE INTO grammar_tag_links VALUES (?,?)", (g["id"], tag))
        for i, ex in enumerate(g.get("examples") or [], start=1):
            con.execute(
                "INSERT INTO grammar_examples (grammar_id, ja, furigana, en, tatoeba_id, ord)"
                " VALUES (?,?,?,?,?,?)",
                (g["id"], ex["ja"], ex.get("furigana"), ex.get("en"), ex.get("tatoeba_id"), i),
            )

    for tag in sorted(tags_seen | set(GRAMMAR_TAGS)):
        en, ru = GRAMMAR_TAGS.get(tag, (tag, tag))
        con.execute("INSERT OR IGNORE INTO grammar_tags VALUES (?,?,?)", (tag, en, ru))

    # grammar <-> vocabulary link when a grammar example uses an N4/N5 headword
    for g in grammar_raw:
        linked = set()
        for ex in g.get("examples") or []:
            text = ex["ja"]
            for word, vid in word_to_id.items():
                if len(word) >= 2 and word in text:
                    linked.add(vid)
        for vid in linked:
            con.execute("INSERT OR IGNORE INTO grammar_related_vocab VALUES (?,?)", (g["id"], vid))

    # -------------------------------------------------- full text -------
    try:
        con.execute(
            "CREATE VIRTUAL TABLE vocab_fts USING fts5(word, reading, romaji, meanings_en,"
            " meaning_ru, content='vocab', content_rowid='rowid')"
        )
        con.execute(
            "INSERT INTO vocab_fts (rowid, word, reading, romaji, meanings_en, meaning_ru)"
            " SELECT rowid, word, reading, romaji, meanings_en, meaning_ru FROM vocab"
        )
        con.execute(
            "CREATE VIRTUAL TABLE grammar_fts USING fts5(pattern, romaji, meaning_en,"
            " meaning_ru, tags_text, content='grammar', content_rowid='rowid')"
        )
        con.execute(
            "INSERT INTO grammar_fts (rowid, pattern, romaji, meaning_en, meaning_ru, tags_text)"
            " SELECT rowid, pattern, romaji, meaning_en, meaning_ru, tags_text FROM grammar"
        )
        fts = "fts5"
    except sqlite3.OperationalError as exc:  # pragma: no cover
        print("FTS5 unavailable, falling back to LIKE indexes:", exc, file=sys.stderr)
        fts = "none"

    # ----------------------------------------------------- metadata -----
    counts = {
        "vocab": con.execute("SELECT count(*) FROM vocab").fetchone()[0],
        "vocab_n5": con.execute("SELECT count(*) FROM vocab WHERE level='N5'").fetchone()[0],
        "vocab_n4": con.execute("SELECT count(*) FROM vocab WHERE level='N4'").fetchone()[0],
        "vocab_examples": con.execute("SELECT count(*) FROM vocab_examples").fetchone()[0],
        "kanji_core": con.execute("SELECT count(*) FROM kanji WHERE in_core_list=1").fetchone()[0],
        "kanji_extra": con.execute("SELECT count(*) FROM kanji WHERE in_core_list=0").fetchone()[0],
        "kanji_total": con.execute("SELECT count(*) FROM kanji").fetchone()[0],
        "kanji_readings": con.execute("SELECT count(*) FROM kanji_readings").fetchone()[0],
        "grammar": con.execute("SELECT count(*) FROM grammar").fetchone()[0],
        "grammar_n5": con.execute("SELECT count(*) FROM grammar WHERE level='N5'").fetchone()[0],
        "grammar_n4": con.execute("SELECT count(*) FROM grammar WHERE level='N4'").fetchone()[0],
        "grammar_examples": con.execute("SELECT count(*) FROM grammar_examples").fetchone()[0],
        "grammar_tags": con.execute("SELECT count(*) FROM grammar_tags").fetchone()[0],
        "pos_codes": con.execute("SELECT count(*) FROM pos_codes").fetchone()[0],
    }
    meta_rows = [
        ("db_name", "jlpt_n4 — база данных сайта для изучения японского языка (JLPT N4)"),
        ("build_version", BUILD_VERSION),
        ("coverage", "JLPT N4 (включая обязательную базу уровня N5)"),
        ("languages", "ja (кандзи + кана), romaji (Хепбёрн), en, ru"),
        ("license", "CC BY-SA 4.0 (производная работа от OpenJLPT)"),
        ("attribution", "Contains data from OpenJLPT (CC BY-SA 4.0), which uses JMdict and "
                        "KANJIDIC2 (EDRDG), Jonathan Waller's JLPT lists, and Tatoeba."),
        ("upstream", "OpenJLPT %s (%s)" % (raw_meta.get("version"), raw_meta.get("homepage"))),
        ("upstream_jmdict", raw_meta.get("sources", {}).get("jmdict", {}).get("created", "")),
        ("upstream_kanjidic2", raw_meta.get("sources", {}).get("kanjidic2", {}).get("database_version", "")),
        ("text_normalization", "furigana notation {канжи|чтение} preserved in *_examples.furigana"),
        ("fts_backend", fts),
        ("note_levels", "Уровни JLPT не публикуются официально; используются списки Дж. Уоллера."),
        ("note_ru", "Русские переводы добавлены при сборке этой базы (не являются официальными)."),
        ("counts_json", jdump(counts)),
    ]
    con.executemany("INSERT INTO meta VALUES (?,?)", meta_rows)
    con.commit()

    # -------------------------------------- batches awaiting RU text ----
    os.makedirs(EXPORT_DIR, exist_ok=True)
    def batches(rows, size=80):
        out = []
        for i in range(0, len(rows), size):
            out.append(rows[i:i + size])
        return out

    vocab_batch = [
        {"id": v["id"], "word": v["word"], "reading": v["reading"],
         "pos": v.get("pos") or [], "en": v["meanings"]}
        for v in vocab_raw
    ]
    kanji_batch = [
        {"character": ch, "meanings": e.get("meanings") or []}
        for ch, e in kanji_by_char.items()
    ]
    grammar_batch = [
        {"id": g["id"], "pattern": g["pattern"], "romaji": g["romaji"],
         "meaning": g["meaning"], "formation": g["formation"], "notes": g.get("notes") or ""}
        for g in grammar_raw
    ]
    example_batch = []
    for v in vocab_raw:
        for i, ex in enumerate(v.get("examples") or [], 1):
            example_batch.append({"kind": "vocab", "ref": v["id"], "ord": i, "ja": ex["ja"], "en": ex.get("en")})
    for g in grammar_raw:
        for i, ex in enumerate(g.get("examples") or [], 1):
            example_batch.append({"kind": "grammar", "ref": g["id"], "ord": i, "ja": ex["ja"], "en": ex.get("en")})

    pending = {
        "vocab": batches(vocab_batch, size=130),
        "kanji": batches(kanji_batch, size=120),
        "grammar": batches(grammar_batch, size=90),
        "examples": batches(example_batch, size=100),
    }
    summary = {"missing_kanji_no_source": missing, "extra_kanji_added": len(extra),
               "vocab": len(vocab_raw), "grammar": len(grammar_raw)}
    with open(os.path.join(EXPORT_DIR, "pending.json"), "w", encoding="utf-8") as fh:
        json.dump({"summary": summary, "batches": {k: len(v) for k, v in pending.items()}}, fh, ensure_ascii=False, indent=2)
    for name, groups in pending.items():
        for i, grp in enumerate(groups):
            with open(os.path.join(EXPORT_DIR, "pending_%s_%02d.json" % (name, i)), "w", encoding="utf-8") as fh:
                json.dump(grp, fh, ensure_ascii=False)

    # manifest of translation batches (input file -> expected output file)
    manifest = []
    ru_dir = os.path.join(EXPORT_DIR, "ru")
    os.makedirs(ru_dir, exist_ok=True)
    for name, groups in pending.items():
        for i, grp in enumerate(groups):
            src = os.path.join(EXPORT_DIR, "pending_%s_%02d.json" % (name, i))
            dst = os.path.join(ru_dir, "ru_%s_%02d.json" % (name, i))
            manifest.append(
                {
                    "kind": name,
                    "index": i,
                    "in": src.replace("\\", "/"),
                    "out": dst.replace("\\", "/"),
                    "count": len(grp),
                }
            )
    with open(os.path.join(EXPORT_DIR, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)

    con.close()
    print("DB written:", DB_PATH)
    print("counts:", jdump(counts))
    print("extra kanji added:", len(extra), "| kanji with no dictionary source:", len(missing))
    print("pending batches:", jdump({k: len(v) for k, v in pending.items()}))


if __name__ == "__main__":
    main()
