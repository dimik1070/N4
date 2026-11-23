"""Merge the Russian translation batches (exports/ru/*.json) into jlpt_n4.db.

Run after the translation workflow finished:  python merge_ru.py
Prints a coverage report and writes exports/ru_report.json.
"""

import datetime
import json
import os
import re
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT_DIR = os.path.join(HERE, "exports")
RU_DIR = os.path.join(EXPORT_DIR, "ru")
DB_PATH = os.path.join(HERE, "jlpt_n4.db")

BUILD_VERSION = "1.0.0"


def read_json(path):
    """Read a JSON array; tolerate agents that wrapped or fenced the output."""
    if not os.path.exists(path):
        return None, "missing file"
    with open(path, encoding="utf-8-sig") as fh:
        text = fh.read().strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\[.*\]", text, re.S)
        if not m:
            return None, "no JSON array found"
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError as exc:
            return None, "invalid JSON: %s" % exc
    if isinstance(data, dict):
        for key in ("items", "data", "results", "rows"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        return None, "expected a JSON array"
    return data, None


def load_pending(kind):
    """Return {key: expected_element} for every pending item of this kind."""
    expected = {}
    idx = 0
    while True:
        path = os.path.join(EXPORT_DIR, "pending_%s_%02d.json" % (kind, idx))
        if not os.path.exists(path):
            break
        with open(path, encoding="utf-8") as fh:
            for item in json.load(fh):
                key = key_of(kind, item)
                expected[key] = item
        idx += 1
    return expected, idx


def key_of(kind, item):
    if kind == "vocab":
        return item["id"]
    if kind == "kanji":
        return item["character"]
    if kind == "grammar":
        return item["id"]
    return "%s|%s|%s" % (item["kind"], item["ref"], item["ord"])


def jdump(obj):
    return json.dumps(obj, ensure_ascii=False)


def main():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    report = {}

    # ---------------------------------------------------- vocabulary ----
    expected, n_files = load_pending("vocab")
    got, stats = collect("vocab", n_files)
    applied = 0
    for key, ru in got.items():
        if key in expected and ru:
            cur = con.execute("UPDATE vocab SET meaning_ru = ? WHERE id = ?", (ru, key))
            applied += cur.rowcount
    report["vocab"] = dict(stats, expected=len(expected), applied=applied)

    # -------------------------------------------------------- kanji ----
    expected, n_files = load_pending("kanji")
    got, stats = collect("kanji", n_files)
    extra_data, extra_err = read_json(os.path.join(RU_DIR, "ru_kanji_extra.json"))
    if extra_data:
        for item in extra_data:
            if isinstance(item, dict) and item.get("character"):
                got[item["character"]] = (item.get("ru") or "").strip()
    elif extra_err != "missing file":
        stats["problems"].append("ru_kanji_extra: " + extra_err)
    applied = 0
    for key, ru in got.items():
        if key in expected and ru:
            cur = con.execute("UPDATE kanji SET meaning_ru = ? WHERE character = ?", (ru, key))
            applied += cur.rowcount
    # kanji that no batch covered (characters added after the batches were cut).
    # Applied last so they win over a batch value with the same key.
    manual = {
        "噌": "мисо (соевая паста)",
        "噛": "жевать; кусать; грызть",
        "賑": "оживлённый; многолюдный; оживляться",
        "飴": "конфета; леденец; карамель",
    }
    for ch, ru in manual.items():
        con.execute("UPDATE kanji SET meaning_ru = ? WHERE character = ?", (ru, ch))
    report["kanji"] = dict(stats, expected=len(expected), applied=applied,
                           total_rows=con.execute("SELECT count(*) FROM kanji WHERE meaning_ru IS NOT NULL").fetchone()[0])

    # ------------------------------------------------------ grammar ----
    expected, n_files = load_pending("grammar")
    got, stats = collect("grammar", n_files)
    applied = 0
    for key, item in got.items():
        if key not in expected:
            continue
        cur = con.execute(
            "UPDATE grammar SET meaning_ru = ?, formation_ru = ?, notes_ru = ? WHERE id = ?",
            (item.get("meaning_ru"), item.get("formation_ru"), item.get("notes_ru"), key),
        )
        applied += cur.rowcount
    report["grammar"] = dict(stats, expected=len(expected), applied=applied)

    # ----------------------------------------------------- examples ----
    expected, n_files = load_pending("examples")
    got, stats = collect("examples", n_files)
    applied_vocab = applied_grammar = 0
    for key, ru in got.items():
        kind, ref, ordn = key.split("|")
        if not ru:
            continue
        if kind == "vocab":
            applied_vocab += con.execute(
                "UPDATE vocab_examples SET ru = ? WHERE vocab_id = ? AND ord = ?", (ru, ref, int(ordn))
            ).rowcount
        else:
            applied_grammar += con.execute(
                "UPDATE grammar_examples SET ru = ? WHERE grammar_id = ? AND ord = ?", (ru, ref, int(ordn))
            ).rowcount
    report["examples"] = dict(stats, expected=len(expected), applied_vocab=applied_vocab,
                              applied_grammar=applied_grammar)

    # ---------------------------------------------------- quality scan ---
    # Russian glosses must not contain Japanese characters (copy/paste leftovers).
    cjk = re.compile(r"[\u3040-\u30ff\u31f0-\u31ff\u4e00-\u9fff]")
    suspicious = []
    for table, cols in (("vocab", ("meaning_ru",)), ("kanji", ("meaning_ru",))):
        for col in cols:
            for (val,) in con.execute("SELECT %s FROM %s WHERE %s IS NOT NULL" % (col, table, col)):
                if cjk.search(val):
                    suspicious.append("%s.%s: %s" % (table, col, val[:90]))
    for table in ("vocab", "grammar"):
        for (ja, ru) in con.execute("SELECT ja, ru FROM %s_examples WHERE ru IS NOT NULL" % table):
            if not ru or ru.strip() == (ja or "").strip() or not re.search(r"[А-Яа-яЁё]", ru):
                suspicious.append("%s_examples.ru is not a Russian sentence: %s" % (table, (ru or "")[:90]))
    report["suspicious_ru"] = suspicious[:40]
    report["suspicious_count"] = len(suspicious)

    # --------------------------------------------------- rebuild FTS ----
    for name, ddl, fill in (
        (
            "vocab_fts",
            "CREATE VIRTUAL TABLE vocab_fts USING fts5(word, reading, romaji, meanings_en,"
            " meaning_ru, content='vocab', content_rowid='rowid')",
            "INSERT INTO vocab_fts (rowid, word, reading, romaji, meanings_en, meaning_ru)"
            " SELECT rowid, word, reading, romaji, meanings_en, meaning_ru FROM vocab",
        ),
        (
            "grammar_fts",
            "CREATE VIRTUAL TABLE grammar_fts USING fts5(pattern, romaji, meaning_en,"
            " meaning_ru, tags_text, content='grammar', content_rowid='rowid')",
            "INSERT INTO grammar_fts (rowid, pattern, romaji, meaning_en, meaning_ru, tags_text)"
            " SELECT rowid, pattern, romaji, meaning_en, meaning_ru, tags_text FROM grammar",
        ),
    ):
        try:
            con.execute("DROP TABLE IF EXISTS %s" % name)
            con.execute(ddl)
            con.execute(fill)
        except sqlite3.OperationalError:
            pass

    # ------------------------------------------------------- metadata ---
    now = datetime.datetime.now().isoformat(timespec="seconds")
    kinds = ("vocab", "kanji", "grammar", "examples")
    rows = {
        "ru_merged_at": now,
        "ru_coverage": jdump({
            k: (report[k].get("applied")
                or report[k].get("applied_vocab", 0) + report[k].get("applied_grammar", 0))
            for k in kinds
        }),
        "ru_report_json": jdump({k: report[k] for k in kinds}),
        "ru_suspicious": jdump(report["suspicious_ru"]),
    }
    for k, v in rows.items():
        con.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)", (k, v))
    con.commit()

    # integrity checks
    checks = {
        "vocab_without_ru": con.execute("SELECT count(*) FROM vocab WHERE meaning_ru IS NULL OR meaning_ru=''").fetchone()[0],
        "kanji_without_ru": con.execute("SELECT count(*) FROM kanji WHERE meaning_ru IS NULL OR meaning_ru=''").fetchone()[0],
        "grammar_without_ru": con.execute("SELECT count(*) FROM grammar WHERE meaning_ru IS NULL OR meaning_ru=''").fetchone()[0],
        "vocab_examples_without_ru": con.execute("SELECT count(*) FROM vocab_examples WHERE ru IS NULL OR ru=''").fetchone()[0],
        "grammar_examples_without_ru": con.execute("SELECT count(*) FROM grammar_examples WHERE ru IS NULL OR ru=''").fetchone()[0],
        "fk_violations": len(con.execute("PRAGMA foreign_key_check").fetchall()),
    }
    con.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)", ("integrity_json", jdump(checks)))
    con.commit()
    con.close()

    with open(os.path.join(EXPORT_DIR, "ru_report.json"), "w", encoding="utf-8") as fh:
        json.dump({"report": report, "integrity": checks}, fh, ensure_ascii=False, indent=1)

    print(json.dumps({"report": report, "integrity": checks}, ensure_ascii=False, indent=1))


def collect(kind, n_files):
    got = {}
    files_ok = 0
    problems = []
    for i in range(n_files):
        path = os.path.join(RU_DIR, "ru_%s_%02d.json" % (kind, i))
        data, err = read_json(path)
        if err:
            problems.append("%s_%02d: %s" % (kind, i, err))
            continue
        files_ok += 1
        for item in data:
            if not isinstance(item, dict):
                continue
            key = key_of(kind, item)
            if kind == "grammar":
                got[key] = {
                    "meaning_ru": (item.get("meaning_ru") or "").strip(),
                    "formation_ru": (item.get("formation_ru") or "").strip(),
                    "notes_ru": (item.get("notes_ru") or "").strip() or None,
                }
            else:
                got[key] = (item.get("ru") or item.get("meaning_ru") or "").strip()
    return got, {"files_ok": files_ok, "files_total": n_files, "problems": problems}


if __name__ == "__main__":
    main()
