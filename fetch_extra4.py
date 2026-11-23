"""Fetch the four kanji that OpenJLPT's level lists omit but N4 vocabulary uses.

Source: kanjiapi.dev (data derived from KANJIDIC2, EDRDG). Output is written in the
same shape as OpenJLPT's kanji JSON so build_db.py can merge it.
"""

import json
import os
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "kanji_extra4.json")

CHARS = {
    "噌": {"level": "N3", "note": "used in 味噌 (N4 vocabulary)"},
    "噛": {"level": "N3", "note": "used in 噛む (N4 vocabulary)"},
    "賑": {"level": "N3", "note": "used in 賑やか (N4 vocabulary)"},
    "飴": {"level": "N3", "note": "飴 (N4 vocabulary)"},
}


def fetch(ch):
    url = "https://kanjiapi.dev/v1/kanji/" + urllib.parse.quote(ch)
    req = urllib.request.Request(url, headers={"User-Agent": "jlpt-n4-db-builder/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    rows = []
    for ch, info in CHARS.items():
        d = fetch(ch)
        rows.append(
            {
                "character": ch,
                "level": info["level"],
                "strokes": d.get("stroke_count"),
                "grade": d.get("grade"),
                "freq": d.get("freq_mainichi_shinbun"),
                "radical": None,
                "radical_number": None,
                "onyomi": d.get("on_readings") or [],
                "kunyomi": d.get("kun_readings") or [],
                "nanori": d.get("name_readings") or [],
                "meanings": d.get("meanings") or [],
                "words": [],
                "supplementary": True,
                "source_note": "kanjiapi.dev (KANJIDIC2-derived); " + info["note"],
            }
        )
        print(ch, rows[-1]["strokes"], d.get("on_readings"), d.get("kun_readings"), d.get("meanings"))
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    print("written:", OUT)


if __name__ == "__main__":
    import urllib.parse

    main()
