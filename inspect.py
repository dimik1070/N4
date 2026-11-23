import json, os, collections

D = os.path.dirname(os.path.abspath(__file__))

def load(name):
    with open(os.path.join(D, name + ".json"), encoding="utf-8") as fh:
        return json.load(fh)

for name in ["vocab_n5", "vocab_n4", "kanji_n5", "kanji_n4", "grammar_n5", "grammar_n4"]:
    arr = load(name)
    print("==", name, len(arr))
    for e in arr[:2]:
        print(json.dumps(e, ensure_ascii=False)[:900])
    print()

# field coverage / distinct values
voc = load("vocab_n5") + load("vocab_n4")
kan = load("kanji_n5") + load("kanji_n4")
grm = load("grammar_n5") + load("grammar_n4")

print("vocab keys:", collections.Counter(k for e in voc for k in e))
pos = collections.Counter(p for e in voc for p in e.get("pos", []))
print("pos codes:", pos.most_common())
print("kanji keys:", collections.Counter(k for e in kan for k in e))
print("grammar keys:", collections.Counter(k for e in grm for k in e))
print("grammar tags:", collections.Counter(t for e in grm for t in e.get("tags", [])).most_common())
print("examples present:", sum(1 for e in voc if e.get("examples")), "of", len(voc))
print("kanji with furigana-less vocab:", sum(1 for e in voc if e.get("word") != e.get("reading")))
# kanji that appear in vocab words but are missing from kanji lists
chars = {e["character"] for e in kan}
missing = collections.Counter()
for e in voc:
    for ch in e["word"]:
        if "\u4e00" <= ch <= "\u9fff" and ch not in chars:
            missing[ch] += 1
print("kanji used by vocab but absent from kanji lists:", len(missing), missing.most_common(30))
