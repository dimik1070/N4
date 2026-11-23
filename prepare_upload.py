"""Собрать папку github-upload для загрузки на GitHub (без Git).

Всё, что попадает в github-upload, и есть содержимое репозитория: сайт, база SQLite,
скрипты сборки, исходные данные OpenJLPT и лицензии — один раз перетащили, догружать нечего.

Сайт собирается ПЛОСКО: index.html и все .js/.css лежат в одном уровне, поэтому папки в
репозитории не нужны вовсе, а в GitHub Pages выбирается корень (/). Исходные JSON тоже
раскладываются плоско — build_db.py умеет читать их и так, и из _sources/openjlpt/.

ОЗВУЧКА. По умолчанию (INCLUDE_AUDIO = False) в репозиторий НЕ попадают MP3-части:
кнопки 🔊 произносят японский текст голосом самого браузера (Web Speech API), поэтому
весь набор весит около 7 МБ вместо ~101 МБ. В собранном data.js появляется
CLIPS_BUILT = false, и сайт даже не пытается качать audio.js/audio*.mp3.
Если захотите вернуть готовые MP3-записи (локальный сайт или догрузка позже):
сначала `python gen_audio.py`, затем INCLUDE_AUDIO = True (строка ниже).

Запуск из папки проекта:  python prepare_upload.py
Куда складывать: переменная окружения UPLOAD_DIR (по умолчанию github-upload рядом
с этим скриптом). Например, чтобы собрать сразу на Рабочем столе:
    $env:UPLOAD_DIR = "$env:USERPROFILE\\OneDrive\\Desktop\\github-upload"
    python prepare_upload.py
"""

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "docs")
OUT = os.environ.get("UPLOAD_DIR") or os.path.join(HERE, "github-upload")

# False — озвучку создаёт браузер, MP3-частей в репозитории нет (рекомендуется).
# True  — положить готовые записи audio.js + audio1.mp3 … audio15.mp3 (~94 МБ).
INCLUDE_AUDIO = False

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

# эти два скрипта нужны только для режима MP3-записей
AUDIO_TOOLS = ["gen_audio.py", "check_audio.py"]

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
    text = text.replace('const DATA_DIR = "data/";', 'const DATA_DIR = "";')
    if not INCLUDE_AUDIO:
        # MP3-частей нет: озвучку полностью берёт на себя браузер.
        text = text.replace('let CLIPS_BUILT = true;', 'let CLIPS_BUILT = false;')
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

    # озвучка MP3-записями: манифест audio.js и части audio1.mp3, audio2.mp3 ...
    if INCLUDE_AUDIO:
        data_dir = os.path.join(SITE, "data")
        for name in sorted(os.listdir(data_dir)):
            if name.startswith("audio"):
                copied.append(put(os.path.join(data_dir, name), name, used))
        for name in AUDIO_TOOLS:
            src = os.path.join(HERE, name)
            if os.path.exists(src):
                copied.append(put(src, name, used))

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
    if INCLUDE_AUDIO:
        print("Озвучка: готовые MP3-записи, голос браузера — запасной путь.")
    else:
        print("Озвучка: её создаёт браузер (Web Speech API), MP3-частей в наборе нет.")
    if total > 90 * 1048576:
        print("ВНИМАНИЕ: набор тяжелее 90 МБ — веб-загрузка на GitHub может не пройти.")
    print("Загружать одним разом: все файлы из папки %s — %d шт., папок нет." % (OUT, len(copied)))
    print("GitHub Pages: Settings -> Pages -> Deploy from a branch -> main -> / (корень).")


if __name__ == "__main__":
    main()
