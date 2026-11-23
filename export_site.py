"""Export jlpt_n4.db into static-site data files (docs/data/*.js).

The data is emitted as JS chunks that assign a global (window.JLPTDATA.*), so the
site works both from a plain static host (GitHub Pages) and when docs/index.html is
opened directly from disk. Loaded lazily by docs/js/data.js.

Run:  python export_site.py
"""

import datetime
import json
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "jlpt_n4.db")
OUT = os.path.join(HERE, "docs", "data")


def jrow(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def write_chunk(name, payload):
    path = os.path.join(OUT, name + ".js")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("window.JLPTDATA=window.JLPTDATA||{};window.JLPTDATA[%s]=%s;"
                 % (jrow(name), jrow(payload)))
    return path, os.path.getsize(path)


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    os.makedirs(OUT, exist_ok=True)

    # ------------------------------------------------------------ vocab ----
    pos_of = {}
    for r in con.execute("SELECT vp.vocab_id AS id, pc.name_ru AS name FROM vocab_pos vp"
                         " JOIN pos_codes pc ON pc.code = vp.code"):
        pos_of.setdefault(r["id"], []).append(r["name"])

    ex_of = {}
    for r in con.execute("SELECT vocab_id AS id, ja, furigana, ru FROM vocab_examples"
                         " ORDER BY vocab_id, ord"):
        ex_of.setdefault(r["id"], []).append(
            {"ja": r["ja"], "fu": r["furigana"] or r["ja"], "ru": r["ru"]}
        )

    kanji_of = {}
    for r in con.execute("SELECT vocab_id AS id, character, position FROM vocab_kanji"
                         " ORDER BY vocab_id, position"):
        kanji_of.setdefault(r["id"], []).append(r["character"])

    # чтения для озвучки: онъёме сначала, потом кунъёме (ровно те строки, что
    # озвучивает gen_audio.py, поэтому запись находится с первого раза)
    say_of = {}
    for r in con.execute("SELECT character, kind, reading_kana FROM kanji_readings"
                         " WHERE kind IN ('on','kun') AND reading_kana IS NOT NULL"
                         " ORDER BY CASE kind WHEN 'on' THEN 0 ELSE 1 END, reading_kana"):
        bucket = say_of.setdefault(r["character"], [])
        if len(bucket) >= 4:
            continue
        if any(item["t"] == r["reading_kana"] for item in bucket):
            continue
        bucket.append({"r": r["kind"], "t": r["reading_kana"]})

    def vocab_rows(level):
        rows = []
        for v in con.execute("SELECT * FROM vocab WHERE level = ? ORDER BY reading, word", (level,)):
            rows.append({
                "id": v["id"],
                "word": v["word"],
                "reading": v["reading"],
                "romaji": v["romaji"],
                "level": v["level"],
                "ru": v["meaning_ru"],
                "en": json.loads(v["meanings_en"]),
                "pos": pos_of.get(v["id"], []),
                "kanji": kanji_of.get(v["id"], []),
                "ex": ex_of.get(v["id"], []),
                "kanaOnly": bool(v["is_kana_only"]),
            })
        return rows

    # ------------------------------------------------------------ kanji ----
    words_of = {}
    for r in con.execute("SELECT kw.character AS ch, kw.word AS word, v.reading AS reading,"
                         " v.level AS level, v.meaning_ru AS ru FROM kanji_words kw"
                         " LEFT JOIN vocab v ON v.id = kw.word ORDER BY kw.character"):
        entry = {"word": r["word"], "reading": r["reading"], "level": r["level"], "ru": r["ru"]}
        words_of.setdefault(r["ch"], []).append(entry)

    kanji_rows = []
    for k in con.execute("SELECT * FROM kanji ORDER BY CASE level WHEN 'N5' THEN 0 ELSE 1 END,"
                         " strokes, character"):
        kanji_rows.append({
            "char": k["character"],
            "level": k["level"],
            "core": bool(k["in_core_list"]),
            "used": bool(k["used_in_vocab"]),
            "strokes": k["strokes"],
            "grade": k["grade"],
            "freq": k["freq"],
            "radical": k["radical"],
            "radicalN": k["radical_number"],
            "on": json.loads(k["onyomi"]),
            "kun": json.loads(k["kunyomi"]),
            "meaningsEn": json.loads(k["meanings_en"]),
            "ru": k["meaning_ru"],
            "sourceNote": k["source_note"],
            "say": say_of.get(k["character"], []),
            "words": (words_of.get(k["character"]) or [])[:14],
        })

    # ---------------------------------------------------------- grammar ----
    tags_of, tag_ru = {}, {}
    for r in con.execute("SELECT grammar_id AS id, tag FROM grammar_tag_links"):
        tags_of.setdefault(r["id"], []).append(r["tag"])
    for r in con.execute("SELECT tag, name_ru FROM grammar_tags"):
        tag_ru[r["tag"]] = r["name_ru"]

    gex_of = {}
    for r in con.execute("SELECT grammar_id AS id, ja, furigana, ru FROM grammar_examples"
                         " ORDER BY grammar_id, ord"):
        gex_of.setdefault(r["id"], []).append(
            {"ja": r["ja"], "fu": r["furigana"] or r["ja"], "ru": r["ru"]}
        )

    grammar_rows = []
    for g in con.execute("SELECT * FROM grammar ORDER BY CASE level WHEN 'N5' THEN 0 ELSE 1 END, pattern"):
        grammar_rows.append({
            "id": g["id"],
            "pattern": g["pattern"],
            "romaji": g["romaji"],
            "level": g["level"],
            "ru": g["meaning_ru"],
            "en": g["meaning_en"],
            "formation": g["formation"],
            "formationRu": g["formation_ru"],
            "notes": g["notes_ru"],
            "tags": tags_of.get(g["id"], []),
            "ex": gex_of.get(g["id"], []),
        })

    meta = dict(con.execute("SELECT key, value FROM meta").fetchall())
    counts = json.loads(meta.get("counts_json", "{}"))
    meta_payload = {
        "generated": datetime.datetime.now().strftime("%Y-%m-%d"),
        "counts": {
            "vocab": len(vocab_rows("N5")) + len(vocab_rows("N4")),
            "kanji": len(kanji_rows),
            "grammar": len(grammar_rows),
            "examples": sum(len(v) for v in ex_of.values()) + sum(len(v) for v in gex_of.values()),
        },
        "tags": [{"tag": t, "ru": n} for t, n in sorted(tag_ru.items())],
        "attribution": meta.get("attribution", ""),
        "license": meta.get("license", "CC BY-SA 4.0"),
        "noteRu": "Русские переводы — переводческая работа, не часть словарных источников.",
    }

    written = []
    written.append(write_chunk("meta", meta_payload))
    written.append(write_chunk("vocabN5", vocab_rows("N5")))
    written.append(write_chunk("vocabN4", vocab_rows("N4")))
    written.append(write_chunk("kanji", kanji_rows))
    written.append(write_chunk("grammar", grammar_rows))

    for path, size in written:
        print("%-40s %7.1f KB" % (os.path.relpath(path, HERE), size / 1024.0))
    print("total %.2f MB" % (sum(s for _, s in written) / 1048576.0))
    con.close()


if __name__ == "__main__":
    main()
