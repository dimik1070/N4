"""Sanity checks for jlpt_n4.db — run after build_db.py and merge_ru.py.

Checks: row counts, JSON columns parse, referential integrity, orphan links,
coverage of Russian translations, FTS search, and a few realistic site queries.
"""

import json
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "jlpt_n4.db")


def q(con, sql, params=()):
    return con.execute(sql, params).fetchall()


def main():
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = ON")
    problems = []
    stats = {}

    tables = [r[0] for r in q(con, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    views = [r[0] for r in q(con, "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")]
    stats["tables"] = tables
    stats["views"] = views

    for t in ["vocab", "vocab_examples", "vocab_pos", "vocab_kanji", "kanji", "kanji_readings",
              "kanji_words", "grammar", "grammar_tags", "grammar_tag_links", "grammar_examples",
              "grammar_related_vocab", "pos_codes", "sources", "meta"]:
        if t not in tables:
            problems.append("missing table: %s" % t)
            continue
        stats["rows_" + t] = q(con, "SELECT count(*) FROM " + t)[0][0]

    # foreign keys
    fk = q(con, "PRAGMA foreign_key_check")
    if fk:
        problems.append("foreign key violations: %d (%s)" % (len(fk), fk[:5]))

    # JSON columns must parse
    json_cols = [
        ("vocab", "meanings_en"), ("vocab", "other_forms"), ("vocab", "other_readings"),
        ("kanji", "onyomi"), ("kanji", "kunyomi"), ("kanji", "nanori"), ("kanji", "meanings_en"),
    ]
    for table, col in json_cols:
        bad = 0
        for (val,) in q(con, "SELECT %s FROM %s" % (col, table)):
            try:
                parsed = json.loads(val)
                if not isinstance(parsed, list):
                    bad += 1
            except (TypeError, json.JSONDecodeError):
                bad += 1
        if bad:
            problems.append("bad JSON in %s.%s: %d rows" % (table, col, bad))

    # coverage
    coverage = {
        "vocab_with_ru": q(con, "SELECT count(*) FROM vocab WHERE meaning_ru IS NOT NULL AND meaning_ru<>''")[0][0],
        "vocab_total": stats["rows_vocab"],
        "kanji_with_ru": q(con, "SELECT count(*) FROM kanji WHERE meaning_ru IS NOT NULL AND meaning_ru<>''")[0][0],
        "kanji_total": stats["rows_kanji"],
        "grammar_with_ru": q(con, "SELECT count(*) FROM grammar WHERE meaning_ru IS NOT NULL AND meaning_ru<>''")[0][0],
        "grammar_total": stats["rows_grammar"],
        "vocab_examples_with_ru": q(con, "SELECT count(*) FROM vocab_examples WHERE ru IS NOT NULL AND ru<>''")[0][0],
        "grammar_examples_with_ru": q(con, "SELECT count(*) FROM grammar_examples WHERE ru IS NOT NULL AND ru<>''")[0][0],
        "examples_total": stats["rows_vocab_examples"] + stats["rows_grammar_examples"],
    }
    stats["coverage"] = coverage

    # every vocab kanji character resolves to a kanji row (vocab_kanji guarantees this),
    # and every kanji inside a headword is present in kanji table
    missing_kanji = q(
        con,
        "SELECT v.word FROM vocab v WHERE v.has_kanji=1 AND NOT EXISTS "
        "(SELECT 1 FROM vocab_kanji vk WHERE vk.vocab_id = v.id)",
    )
    if missing_kanji:
        problems.append("headwords with kanji but no vocab_kanji link: %d" % len(missing_kanji))

    # furigana notation consistency: furigana text must contain braces
    bad_furi = q(con, "SELECT count(*) FROM vocab_examples WHERE furigana IS NOT NULL AND furigana NOT LIKE '%|%'")[0][0]
    if bad_furi:
        problems.append("suspect furigana rows in vocab_examples: %d" % bad_furi)

    # level sanity
    bad_level = q(con, "SELECT count(*) FROM vocab WHERE level NOT IN ('N5','N4')")[0][0]
    bad_level += q(con, "SELECT count(*) FROM grammar WHERE level NOT IN ('N5','N4')")[0][0]
    if bad_level:
        problems.append("unexpected JLPT level values: %d" % bad_level)

    # example counts must match the examples tables
    mismatch = q(
        con,
        "SELECT count(*) FROM vocab v WHERE v.example_count <> (SELECT count(*) FROM vocab_examples e WHERE e.vocab_id=v.id)",
    )[0][0]
    if mismatch:
        problems.append("vocab.example_count mismatch: %d rows" % mismatch)
    mismatch = q(
        con,
        "SELECT count(*) FROM grammar g WHERE g.example_count <> (SELECT count(*) FROM grammar_examples e WHERE e.grammar_id=g.id)",
    )[0][0]
    if mismatch:
        problems.append("grammar.example_count mismatch: %d rows" % mismatch)

    # FTS search
    try:
        hits = q(con, "SELECT v.word, v.reading, v.meaning_ru FROM vocab_fts f"
                      " JOIN vocab v ON v.rowid = f.rowid WHERE vocab_fts MATCH ?", ("стол",))
        stats["fts_ru_hits_for_stol"] = len(hits)
        stats["fts_sample"] = hits[:5]
        if len(hits) == 0:
            problems.append("FTS5 search for 'стол' returned nothing")
    except sqlite3.OperationalError as exc:
        problems.append("FTS5 unavailable: %s" % exc)

    # realistic site queries
    queries = {
        "word_card": (
            "SELECT v.word, v.reading, v.romaji, v.meaning_ru, "
            "(SELECT group_concat(pc.name_ru, ', ') FROM vocab_pos vp JOIN pos_codes pc ON pc.code=vp.code WHERE vp.vocab_id=v.id) AS pos "
            "FROM vocab v WHERE v.word = ?", ("勉強",),
        ),
        "search_by_romaji_prefix": (
            "SELECT word, reading, romaji FROM vocab WHERE romaji LIKE ? ORDER BY romaji LIMIT 5", ("ben%",),
        ),
        "n4_verbs": (
            "SELECT v.word, v.reading, v.meaning_ru FROM vocab v JOIN vocab_pos vp ON vp.vocab_id=v.id "
            "WHERE v.level='N4' AND vp.code LIKE 'v%' ORDER BY v.reading LIMIT 5",
        ),
        "kanji_card": (
            "SELECT character, onyomi, kunyomi, meaning_ru FROM kanji WHERE character = ?", ("会",),
        ),
        "grammar_by_tag": (
            "SELECT g.pattern, g.meaning_ru FROM grammar g JOIN grammar_tag_links l ON l.grammar_id=g.id "
            "WHERE l.tag = ? ORDER BY g.level DESC LIMIT 5", ("obligation",),
        ),
        "words_using_kanji": (
            "SELECT v.word, v.reading FROM kanji_words kw JOIN vocab v ON v.id = kw.vocab_id WHERE kw.character = ? LIMIT 8", ("会",),
        ),
    }
    stats["sample_queries"] = {}
    for name, (sql, *rest) in queries.items():
        params = rest[0] if rest else ()
        rows = q(con, sql, params)
        stats["sample_queries"][name] = rows
        if not rows:
            problems.append("sample query returned no rows: %s" % name)

    stats["integrity_check_rows"] = len(fk)
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    print("\nPROBLEMS:", len(problems))
    for p in problems:
        print(" -", p)
    con.close()
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
