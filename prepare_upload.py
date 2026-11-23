"""Собрать папку github-upload для загрузки на GitHub (без Git).

Всё, что попадает в github-upload, и есть содержимое репозитория: сайт, база SQLite,
скрипты сборки, исходные данные OpenJLPT и лицензии — один раз перетащили, догружать нечего.

Сайт собирается ПЛОСКО: index.html и все .js/.css лежат в одном уровне, поэтому папки в
репозитории не нужны вовсе, а в GitHub Pages выбирается корень (/). Исходные JSON тоже
раскладываются плоско — build_db.py умеет читать их и так, и из _sources/openjlpt/.

Запуск из папки проекта:  python prepare_upload.py
"""

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "docs")
OUT = os.path.join(HERE, "github-upload")

# файлы проекта, которые копируются как есть
TOP_FILES = [
    "jlpt_n4.db",
    "README.md",
    "LICENSE.md",
    ".gitignore",
    "build_db.py",
    "merge_ru.py",
    "verify_db.py",
    "export_site.py",
    "prepare_upload.py",
    "make_readme.py",
    "qa_ru.py",
]

# сайт: (путь в docs, имя в репозитории, нужно ли переписать пути)
SITE_FILES = [
    (os.path.join("index.html"), "index.html", True),
    (os.path.join("css", "style.css"), "style.css", False),
    (os.path.join("js", "data.js"), "data.js", True),
    (os.path.join("js", "train.js"), "train.js", False),
    (os.path.join("js", "app.js"), "app.js", False),
    (os.path.join("data", "meta.js"), "meta.js", False),
    (os.path.join("data", "kanji.js"), "kanji.js", False),
    (os.path.join("data", "grammar.js"), "grammar.js", False),
    (os.path.join("data", "vocabN5.js"), "vocabN5.js", False),
    (os.path.join("data", "vocabN4.js"), "vocabN4.js", False),
]

# исходные данные: папка OpenJLPT целиком (+ два файла рядом)
SOURCE_DIR = os.path.join(HERE, "_sources", "openjlpt")
SOURCE_EXTRA = [
    os.path.join(HERE, "_sources", "kanji_extra4.json"),
    os.path.join(HERE, "exports", "ru_report.json"),  # отчёт о русских переводах
]


def flatten(text):
    """Переписать пути так, чтобы все файлы лежали рядом с index.html."""
    text = text.replace('href="css/style.css"', 'href="style.css"')
    text = text.replace('src="js/', 'src="')
    text = text.replace('s.src = "data/" + name', 's.src = name')
    text = text.replace('загрузить data/" + name', 'загрузить " + name')
    return text


def put(path, name, used, rewrite=False):
    dst = os.path.join(OUT, name)
    if name in used:
        sys.exit("Конфликт имён: %s уже есть в папке загрузки" % name)
    if rewrite:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        with open(dst, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(flatten(text))
    else:
        shutil.copy2(path, dst)
    used.add(name)
    return name


def main():
    for rel in ("index.html", "css", "js", "data"):
        if not os.path.exists(os.path.join(SITE, rel)):
            sys.exit("Нет папки сайта: %s (запустите python export_site.py)" % os.path.join(SITE, rel))

    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    used = set()
    copied = []

    for rel, name, rewrite in SITE_FILES:
        copied.append(put(os.path.join(SITE, rel), name, used, rewrite))

    for name in TOP_FILES:
        src = os.path.join(HERE, name)
        if not os.path.exists(src):
            sys.exit("Нет файла %s — он нужен в репозитории" % name)
        copied.append(put(src, name, used))

    if os.path.isdir(SOURCE_DIR):
        for name in sorted(os.listdir(SOURCE_DIR)):
            src = os.path.join(SOURCE_DIR, name)
            if os.path.isfile(src):
                copied.append(put(src, name, used))
    else:
        print("папка %s не найдена — исходные данные не включены" % SOURCE_DIR)

    for src in SOURCE_EXTRA:
        if os.path.isfile(src):
            copied.append(put(src, os.path.basename(src), used))

    total = 0
    for name in sorted(copied):
        size = os.path.getsize(os.path.join(OUT, name))
        total += size
        print("%-22s %8.1f KB" % (name, size / 1024.0))
    print("-" * 34)
    print("файлов: %d, всего: %.2f МБ" % (len(copied), total / 1048576.0))
    print()
    print("Загружать одним разом: все %d файлов из папки github-upload (папок нет)." % len(copied))
    print("GitHub Pages: Settings -> Pages -> Deploy from a branch -> main -> / (корень).")


if __name__ == "__main__":
    main()
