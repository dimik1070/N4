"""Quality check of the translation batches in exports/ru against exports/pending_*.json."""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT_DIR = os.path.join(HERE, "exports")
RU_DIR = os.path.join(EXPORT_DIR, "ru")

CJK = re.compile(r"[\u3040-\u30ff\u31f0-\u31ff\u4e00-\u9fff]")
CYR = re.compile(r"[А-Яа-яЁё]")


def read_json(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def key_of(kind, item):
    if kind == "vocab":
        return item["id"]
    if kind == "kanji":
        return item["character"]
    if kind == "grammar":
        return item["id"]
    return "%s|%s|%s" % (item["kind"], item["ref"], item["ord"])


def main():
    problems = []
    summary = {}
    for kind in ("vocab", "kanji", "grammar", "examples"):
        expected_keys = []
        idx = 0
        while True:
            path = os.path.join(EXPORT_DIR, "pending_%s_%02d.json" % (kind, idx))
            if not os.path.exists(path):
                break
            expected_keys.extend(key_of(kind, it) for it in read_json(path))
            idx += 1
        n_pending_files = idx
        seen = {}
        short = 0
        cjk_hits = []
        no_cyr = []
        dupes = 0
        for i in range(n_pending_files):
            path = os.path.join(RU_DIR, "ru_%s_%02d.json" % (kind, i))
            if not os.path.exists(path):
                problems.append("missing output file: %s" % os.path.basename(path))
                continue
            data = read_json(path)
            pending = read_json(os.path.join(EXPORT_DIR, "pending_%s_%02d.json" % (kind, i)))
            if len(data) != len(pending):
                problems.append("%s_%02d: %d items, expected %d" % (kind, i, len(data), len(pending)))
            for item in data:
                key = key_of(kind, item)
                if key in seen:
                    dupes += 1
                seen[key] = item
                if kind == "grammar":
                    text = " ".join(str(item.get(f) or "") for f in ("meaning_ru", "formation_ru"))
                else:
                    text = item.get("ru") or item.get("meaning_ru") or ""
                if len(text) < 2:
                    short += 1
                if CJK.search(text):
                    cjk_hits.append((key, text[:80]))
                if not CYR.search(text):
                    no_cyr.append((key, text[:80]))
        missing = [k for k in expected_keys if k not in seen]
        extra = [k for k in seen if k not in set(expected_keys)]
        summary[kind] = {
            "pending_items": len(expected_keys),
            "translated_items": len(seen),
            "missing_items": len(missing),
            "extra_items": len(extra),
            "empty_or_short": short,
            "duplicates": dupes,
            "ru_contains_japanese": len(cjk_hits),
            "ru_without_cyrillic": len(no_cyr),
        }
        if missing:
            problems.append("%s: %d items untranslated (e.g. %s)" % (kind, len(missing), missing[:6]))
        for key, text in cjk_hits[:12]:
            problems.append("%s %r contains Japanese characters: %s" % (kind, key, text))
        for key, text in no_cyr[:12]:
            problems.append("%s %r has no Cyrillic: %s" % (kind, key, text))

    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print("\nPROBLEMS:", len(problems))
    for p in problems[:60]:
        print(" -", p)


if __name__ == "__main__":
    main()
