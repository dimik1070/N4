# Лицензия и атрибуция

База `jlpt_n4.db`, данные в `docs/data/` и скрипты сборки — производная работа, распространяется под
**Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**.
Текст лицензии: https://creativecommons.org/licenses/by-sa/4.0/

## Обязательная атрибуция

> Contains data from [OpenJLPT](https://github.com/evanclan/OpenJLPT) (CC BY-SA 4.0), which uses
> JMdict and KANJIDIC2 (EDRDG), Jonathan Waller's JLPT lists, and Tatoeba.

Эту строку нужно сохранить при любой публикации (в подвале сайта, в README или на странице «О данных»)
и сохранить возможность скачать исходные данные.

## Источники данных

| Источник | Для чего | Лицензия |
|---|---|---|
| [JMdict (EDRDG)](https://www.edrdg.org/jmdict/j_jmdict.html) | идентификаторы слов, части речи, чтения и переводы | CC BY-SA 4.0 |
| [KANJIDIC2 (EDRDG)](https://www.edrdg.org/wiki/KANJIDIC_Project.html) | чтения кандзи, значения, черточки, школьные классы, радикалы, частотность | CC BY-SA 4.0 |
| [Jonathan Waller (tanos.co.uk)](https://www.tanos.co.uk/jlpt/) | отнесение слов и кандзи к уровням JLPT, английские переводы слов | CC BY 4.0 |
| [OpenJLPT](https://github.com/evanclan/OpenJLPT) | словарь, кандзи и грамматика JLPT N5–N4 (сборка) | CC BY-SA 4.0 |
| [Tatoeba](https://tatoeba.org) | примеры предложений | CC BY 2.0 FR |
| [kanjiapi.dev](https://kanjiapi.dev) | данные KANJIDIC2 для 4 кандзи вне списков JLPT (噌 噛 賑 飴) | CC BY-SA 4.0 |

## Русские переводы

Русские значения слов, кандзи, грамматических конструкций и переводы примеров — переводческая работа,
выполненная при сборке этой базы. Они **не входят** в словари-источники и не являются частью их лицензий;
при публикации помечайте их как unofficial.

## Код сайта и скрипты

HTML, CSS и JavaScript в `docs/`, а также скрипты `*.py` — под той же лицензией CC BY-SA 4.0, чтобы
условия лицензии для данных и для кода совпадали.

## Озвучка (аудио произношения)

Файлы `docs/data/audio1.mp3` … `docs/data/audio15.mp3` и манифест `docs/data/audio.js` — это записи
японского произношения, полученные скриптом `gen_audio.py` из открытого голосового сервиса Google
Translate (публичный TTS, используется без ключа и без авторизации). Это **не часть** OpenJLPT, JMdict,
KANJIDIC2 или Tatoeba, и лицензия CC BY-SA 4.0 на них не распространяется: условия использования
определяет сервис, предоставивший голос, и при публикации сайта вы принимаете это решение сами.

Если такой аудиоисточник вам не подходит — удалите `audio*.mp3` и `audio.js`: кнопки 🔊 продолжат
работать через голос браузера (в Chrome, Android и iPhone японский голос есть по умолчанию; на Windows
его нужно добавить в «Параметры → Речь»). Текст для озвучивания берётся из чтений и примеров базы,
то есть из данных под CC BY-SA.
