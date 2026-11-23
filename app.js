/* Страницы сайта и маршрутизация. */
(function () {
  "use strict";
  var JLPT = window.JLPT;
  var esc = JLPT.esc, fu = JLPT.furigana;

  var SCOPE_LABEL = { vocab: "Слова", kanji: "Кандзи", grammar: "Грамматика" };

  function modeValid(scope, id) {
    var ok = false;
    (window.JLPT.trainModes || []).forEach(function (m) { if (m.scope === scope && m.id === id) ok = true; });
    return ok;
  }

  /* ------------------------------------------------ sakura petals ------- */
  (function petals() {
    var host = document.getElementById("petals");
    if (!host) return;
    for (var i = 0; i < 14; i++) {
      var p = document.createElement("i");
      p.className = "petal";
      p.style.left = (Math.random() * 100).toFixed(2) + "%";
      p.style.animationDuration = (9 + Math.random() * 14).toFixed(2) + "s";
      p.style.animationDelay = (-Math.random() * 16).toFixed(2) + "s";
      p.style.transform = "scale(" + (0.6 + Math.random() * 0.8).toFixed(2) + ")";
      host.appendChild(p);
    }
  })();

  /* ------------------------------------------------ helpers ------------- */
  function ruby(text) { return fu(text); }
  function setHTML(el, html) { el.innerHTML = html; }

  function cardWord(v) {
    var pos = (v.pos || []).slice(0, 3).map(function (p) { return "<span class='badge'>" + esc(p) + "</span>"; }).join(" ");
    var ex = (v.ex || []).slice(0, 2).map(function (e) {
      return "<div class='example'><div class='ja'>" + ruby(e.fu) + "</div><div class='ru'>" + esc(e.ru) + "</div></div>";
    }).join("");
    var chips = (v.kanji || []).map(function (ch) {
      return "<a class='kchip' href='#/kanji/" + encodeURIComponent(ch) + "'>" + esc(ch) + "</a>";
    }).join("");
    return "<article class='card entry' data-wordid='" + v.id + "'>" +
      "<div class='head'><span class='word'>" + ruby(v.word) + "</span>" +
        (v.reading !== v.word ? "<span class='reading'>" + esc(v.reading) + "</span>" : "") +
        "<span class='romaji'>" + esc(v.romaji) + "</span>" + JLPT.levelBadge(v.level) + "</div>" +
      "<div class='mean'>" + esc(v.ru) + "</div>" +
      "<div class='pos'>" + pos + "</div>" +
      (chips ? "<div class='kanji-chips'>" + chips + "</div>" : "") +
      ex + "</article>";
  }

  function cardKanji(k) {
    return "<a class='card' style='text-decoration:none;color:inherit' href='#/kanji/" + encodeURIComponent(k.char) + "'>" +
      "<div class='row' style='justify-content:space-between'>" +
        "<div class='kanji-glyph'>" + esc(k.char) + "</div>" +
        "<div class='kanji-meta' style='text-align:right'>" + JLPT.levelBadge(k.level) +
          "<div>черточек: " + esc(k.strokes == null ? "?" : k.strokes) + (k.grade ? " · класс " + k.grade : "") +
          (k.freq ? " · #" + k.freq : "") + "</div></div>" +
      "</div>" +
      "<div class='readings'>" +
        "<span><b>オン:</b> " + esc((k.on || []).join("、") || "—") + "</span>" +
        "<span><b>クン:</b> " + ruby((k.kun || []).join("、") || "—") + "</span>" +
      "</div>" +
      "<div class='mean' style='margin-top:8px'>" + esc(k.ru) + "</div>" +
      "</a>";
  }

  function cardGrammar(g, tagNames) {
    var tags = (g.tags || []).map(function (t) {
      return "<span class='badge'>" + esc((tagNames && tagNames[t]) || t) + "</span>";
    }).join(" ");
    var ex = (g.ex || []).slice(0, 2).map(function (e) {
      return "<div class='example'><div class='ja'>" + ruby(e.fu) + "</div><div class='ru'>" + esc(e.ru) + "</div></div>";
    }).join("");
    return "<article class='card entry'>" +
      "<div class='head'><span class='word'>" + esc(g.pattern) + "</span>" +
        (g.romaji ? "<span class='romaji'>" + esc(g.romaji) + "</span>" : "") + JLPT.levelBadge(g.level) + "</div>" +
      "<div class='mean'>" + esc(g.ru) + "</div>" +
      "<div class='pos'>" + tags + "</div>" +
      (g.formationRu ? "<div class='example'><div class='ja'>Образование</div><div class='ru'>" + esc(g.formationRu) + "</div></div>" : "") +
      (g.notes ? "<p class='sub' style='margin-top:8px'>" + esc(g.notes) + "</p>" : "") +
      ex + "</article>";
  }

  /* ------------------------------------------------- home --------------- */
  function pageHome() {
    setHTML(appEl, "<div class='empty'>Загрузка…</div>");
    Promise.all([JLPT.meta(), JLPT.vocab(), JLPT.kanji(), JLPT.grammar()]).then(function (res) {
      var meta = res[0], words = res[1], kanji = res[2], grammar = res[3];
      var st = JLPT.stats();
      var daily = JLPT.pick(words, 4);
      var dueCount = 0;
      words.forEach(function (v) { if (JLPT.isDue("w:" + v.id)) dueCount++; });

      setHTML(appEl,
        "<section class='hero'>" +
          "<h1>日本語 N4 · японский по базе JLPT</h1>" +
          "<p>1304 слова уровней N5+N4, " + kanji.length + " иероглифов и " + grammar.length +
          " грамматических конструкций с примерами и русскими переводами — и тренажёр, который возвращает то, что вы забываете.</p>" +
          "<div class='hero-stats'>" +
            "<div class='stat'><b>" + words.length + "</b><span>слов</span></div>" +
            "<div class='stat'><b>" + kanji.length + "</b><span>кандзи</span></div>" +
            "<div class='stat'><b>" + grammar.length + "</b><span>конструкций</span></div>" +
            "<div class='stat'><b>" + meta.counts.examples + "</b><span>примеров</span></div>" +
          "</div>" +
          "<div class='row' style='margin-top:18px'>" +
            "<a class='btn pink' href='#/train'>Начать тренировку</a>" +
            "<a class='btn ghost' href='#/words'>Смотреть слова</a>" +
          "</div>" +
        "</section>" +

        "<section class='section'><h2>Что внутри</h2>" +
        "<p class='sub'>База для JLPT N4: сначала N5 как фундамент, затем весь материал N4.</p>" +
        "<div class='grid cols-3'>" +
          "<a class='card link' href='#/words'><h3>Слова</h3><p>" + words.length + " слов: кандзи, кана, ромадзи, часть речи, перевод и примеры.</p></a>" +
          "<a class='card link' href='#/kanji'><h3>Кандзи</h3><p>" + kanji.length + " иероглифов: чтения, значения, черточки, слова с этим кандзи.</p></a>" +
          "<a class='card link' href='#/grammar'><h3>Грамматика</h3><p>" + grammar.length + " конструкций: образование, значение, темы, примеры.</p></a>" +
        "</div></section>" +

        "<section class='section'><h2>Тренировка запоминания</h2>" +
        "<p class='sub'>12 режимов: карточки, выбор перевода, чтение кандзи, определения конструкции в предложении. Ошибочное возвращается чаще — интервальный повтор.</p>" +
        "<div class='grid cols-3'>" +
          modeCard("vocab", "flash") + modeCard("vocab", "reading") + modeCard("kanji", "kanji-reading") +
        "</div>" +
        "<div class='row' style='margin-top:14px'>" +
          "<span class='pill'>изучено " + st.items + "</span>" +
          "<span class='pill'>верных " + st.accuracy + "%</span>" +
          "<span class='pill'>к повтору сейчас: " + dueCount + " слов</span>" +
          "<a class='btn' href='#/train'>Все режимы</a>" +
        "</div></section>" +

        "<section class='section'><h2>Слова дня</h2>" +
        "<div class='grid cols-2'>" + daily.map(cardWord).join("") + "</div>" +
        "<div class='row' style='margin-top:14px'><button class='btn ghost' id='shuffle'>Другие четыре слова</button></div>" +
        "</section>" +

        "<section class='section'><div class='notice'>" + esc(meta.attribution) + "</div></section>");

      document.getElementById("shuffle").onclick = function () {
        var cards = document.querySelectorAll(".grid.cols-2 .card.entry");
        var fresh = JLPT.pick(words, 4).map(cardWord).join("");
        if (cards.length === 4) {
          var holder = cards[0].parentNode;
          holder.innerHTML = fresh;
        }
      };
    });
  }

  function modeCard(scope, id) {
    var m = null;
    JLPT.trainModes.forEach(function (x) { if (x.scope === scope && x.id === id) m = x; });
    if (!m) return "";
    return "<a class='card link mode-card' href='#/train'><div class='emoji'>" + m.emoji + "</div>" +
      "<h3>" + esc(m.title) + "</h3><p>" + esc(m.desc) + "</p></a>";
  }

  /* ------------------------------------------------- words page --------- */
  var wordFilters = { level: "", pos: "", q: "", limit: 40 };
  function pageWords(preset) {
    setHTML(appEl, "<div class='empty'>Загрузка словаря…</div>");
    JLPT.vocab().then(function (all) {
      var posList = {};
      all.forEach(function (v) { (v.pos || []).forEach(function (p) { posList[p] = (posList[p] || 0) + 1; }); });
      var posKeys = Object.keys(posList).sort(function (a, b) { return posList[b] - posList[a]; });
      if (preset && preset.level) wordFilters.level = preset.level;

      setHTML(appEl,
        "<section class='section'><h2>Слова N5 + N4</h2>" +
        "<p class='sub'>Поиск по кандзи, кане, ромадзи и русскому переводу.</p>" +
        "<div class='filters'>" +
          "<input class='input' id='q' placeholder='есть, 食べる, taberu…' value=" + JSON.stringify(wordFilters.q) + ">" +
          "<button class='chip" + (wordFilters.level === "" ? " active" : "") + "' data-l=''>Все</button>" +
          "<button class='chip" + (wordFilters.level === "N5" ? " active" : "") + "' data-l='N5'>N5</button>" +
          "<button class='chip" + (wordFilters.level === "N4" ? " active" : "") + "' data-l='N4'>N4</button>" +
          "<select class='input' id='pos' style='min-width:200px'><option value=''>Все части речи</option>" +
            posKeys.map(function (p) {
              return "<option value='" + esc(p) + "'" + (wordFilters.pos === p ? " selected" : "") + ">" + esc(p) + " (" + posList[p] + ")</option>";
            }).join("") + "</select>" +
          "<button class='btn violet' id='drill'>Тренировать этот набор</button>" +
          "<span class='count' id='count'></span>" +
        "</div><div class='grid cols-2' id='list'></div></section>");

      var qEl = document.getElementById("q");
      var posEl = document.getElementById("pos");
      var listEl = document.getElementById("list");
      var countEl = document.getElementById("count");

      function filtered() {
        var q = wordFilters.q.trim().toLowerCase();
        var qn = JLPT.normRomaji(q);
        return all.filter(function (v) {
          if (wordFilters.level && v.level !== wordFilters.level) return false;
          if (wordFilters.pos && (v.pos || []).indexOf(wordFilters.pos) < 0) return false;
          if (!q) return true;
          if (v.word.indexOf(q) >= 0 || v.reading.indexOf(q) >= 0) return true;
          if (v.ru && v.ru.toLowerCase().indexOf(q) >= 0) return true;
          if (qn && JLPT.normRomaji(v.romaji).indexOf(qn) >= 0) return true;
          return (v.en || []).join(" ").toLowerCase().indexOf(q) >= 0;
        });
      }
      function draw() {
        var rows = filtered();
        countEl.textContent = rows.length + " слов";
        var shown = rows.slice(0, wordFilters.limit);
        listEl.innerHTML = shown.map(cardWord).join("") || "<div class='empty'>Ничего не найдено.</div>";
        if (rows.length > shown.length) {
          var more = document.createElement("button");
          more.className = "btn ghost";
          more.textContent = "Показать ещё " + Math.min(40, rows.length - shown.length);
          more.onclick = function () { wordFilters.limit += 40; draw(); };
          listEl.appendChild(more);
        }
      }
      qEl.oninput = function () { wordFilters.q = qEl.value; wordFilters.limit = 40; draw(); };
      posEl.onchange = function () { wordFilters.pos = posEl.value; wordFilters.limit = 40; draw(); };
      Array.prototype.forEach.call(document.querySelectorAll("[data-l]"), function (b) {
        b.onclick = function () {
          wordFilters.level = b.getAttribute("data-l"); wordFilters.limit = 40;
          Array.prototype.forEach.call(document.querySelectorAll("[data-l]"), function (x) {
            x.classList.toggle("active", x === b);
          });
          draw();
        };
      });
      document.getElementById("drill").onclick = function () {
        var rows = filtered();
        if (!rows.length) return;
        location.hash = "#/train?scope=vocab&level=" + (wordFilters.level || "") + "&keys=" +
          encodeURIComponent(rows.map(function (v) { return v.id; }).join(","));
      };
      draw();
    });
  }

  /* ------------------------------------------------- kanji page --------- */
  var kanjiFilters = { level: "", q: "", limit: 60 };
  function pageKanji() {
    setHTML(appEl, "<div class='empty'>Загрузка кандзи…</div>");
    JLPT.kanji().then(function (all) {
      setHTML(appEl,
        "<section class='section'><h2>Кандзи</h2>" +
        "<p class='sub'>253 иероглифа из списков N5 и N4 и " + all.filter(function (k) { return !k.core; }).length +
        " тех, что встречаются в лексике N4.</p>" +
        "<div class='filters'>" +
          "<input class='input' id='q' placeholder='иероглиф, чтение или значение' value=" + JSON.stringify(kanjiFilters.q) + ">" +
          "<button class='chip" + (kanjiFilters.level === "" ? " active" : "") + "' data-l=''>Все</button>" +
          "<button class='chip" + (kanjiFilters.level === "N5" ? " active" : "") + "' data-l='N5'>N5</button>" +
          "<button class='chip" + (kanjiFilters.level === "N4" ? " active" : "") + "' data-l='N4'>N4</button>" +
          "<button class='chip" + (kanjiFilters.level === "core" ? " active" : "") + "' data-l='core'>Только из списка JLPT</button>" +
          "<button class='btn violet' id='drill'>Тренировать кандзи</button>" +
          "<span class='count' id='count'></span>" +
        "</div><div class='grid cols-3' id='list'></div></section>");

      var qEl = document.getElementById("q"), listEl = document.getElementById("list"), countEl = document.getElementById("count");
      function filtered() {
        var q = kanjiFilters.q.trim().toLowerCase();
        return all.filter(function (k) {
          if (kanjiFilters.level === "core" && !k.core) return false;
          if (kanjiFilters.level && kanjiFilters.level !== "core" && k.level !== kanjiFilters.level) return false;
          if (!q) return true;
          if (k.char.indexOf(q) >= 0) return true;
          if ((k.on || []).join(" ").toLowerCase().indexOf(q) >= 0) return true;
          if ((k.kun || []).join(" ").toLowerCase().indexOf(q) >= 0) return true;
          return !!k.ru && k.ru.toLowerCase().indexOf(q) >= 0;
        });
      }
      function draw() {
        var rows = filtered();
        countEl.textContent = rows.length + " иероглифов";
        var shown = rows.slice(0, kanjiFilters.limit);
        listEl.innerHTML = shown.map(cardKanji).join("") || "<div class='empty'>Не найдено.</div>";
        if (rows.length > shown.length) {
          var more = document.createElement("button");
          more.className = "btn ghost"; more.textContent = "Показать ещё";
          more.onclick = function () { kanjiFilters.limit += 60; draw(); };
          listEl.appendChild(more);
        }
      }
      qEl.oninput = function () { kanjiFilters.q = qEl.value; kanjiFilters.limit = 60; draw(); };
      Array.prototype.forEach.call(document.querySelectorAll("[data-l]"), function (b) {
        b.onclick = function () {
          kanjiFilters.level = b.getAttribute("data-l"); kanjiFilters.limit = 60;
          Array.prototype.forEach.call(document.querySelectorAll("[data-l]"), function (x) { x.classList.toggle("active", x === b); });
          draw();
        };
      });
      document.getElementById("drill").onclick = function () {
        var rows = filtered();
        if (!rows.length) return;
        var level = (kanjiFilters.level === "core") ? "" : kanjiFilters.level;
        location.hash = "#/train?scope=kanji&level=" + level + "&keys=" +
          encodeURIComponent(rows.map(function (k) { return k.char; }).join(","));
      };
      draw();
    });
  }

  function pageKanjiChar(ch) {
    setHTML(appEl, "<div class='empty'>Загрузка…</div>");
    JLPT.kanji().then(function (all) {
      var k = all.filter(function (x) { return x.char === ch; })[0];
      if (!k) { setHTML(appEl, "<div class='empty'>Иероглиф «" + esc(ch) + "» не найден в базе.</div>"); return; }
      var words = k.words || [];
      setHTML(appEl,
        "<section class='section'><a class='btn ghost' href='#/kanji'>← Все кандзи</a>" +
        "<div class='card' style='margin-top:14px'>" +
          "<div class='row' style='justify-content:space-between;align-items:flex-start'>" +
            "<div class='kanji-glyph' style='font-size:96px'>" + esc(k.char) + "</div>" +
            "<div class='kanji-meta' style='text-align:right'>" + JLPT.levelBadge(k.level) +
              (k.core ? "" : " <span class='badge kanji'>вне списка JLPT</span>") +
              "<div style='margin-top:8px'>черточек: " + esc(k.strokes == null ? "?" : k.strokes) +
              (k.grade ? " · школьный класс " + k.grade : "") + (k.freq ? " · частотность #" + k.freq : "") +
              (k.radical ? " · радикал " + k.radical : "") + "</div>" +
              "<div style='margin-top:8px'><a class='btn pink' href='#/train?scope=kanji&keys=" + encodeURIComponent(k.char) + "'>Потренировать</a></div>" +
            "</div>" +
          "</div>" +
          "<div class='readings' style='margin-top:14px'>" +
            "<span><b>Онъёме (オン):</b> " + esc((k.on || []).join("、") || "—") + "</span>" +
            "<span><b>Кунъёме (クン):</b> " + ruby((k.kun || []).join("、") || "—") + "</span>" +
            "<span><b>Русское значение:</b> " + esc(k.ru) + "</span>" +
            "<span><b>English:</b> " + esc((k.meaningsEn || []).join("; ")) + "</span>" +
            (k.sourceNote ? "<span class='notice'>" + esc(k.sourceNote) + "</span>" : "") +
          "</div>" +
        "</div>" +
        "<h2 class='section' style='margin-top:26px'>Слова с этим иероглифом</h2>" +
        "<div class='grid cols-2'>" + words.map(function (w) {
          return "<div class='card entry'><div class='head'><span class='word'>" + ruby(w.word) + "</span>" +
            (w.reading && w.reading !== w.word ? "<span class='reading'>" + esc(w.reading) + "</span>" : "") +
            (w.level ? JLPT.levelBadge(w.level) : "") + "</div><div class='mean'>" + esc(w.ru || "") + "</div></div>";
        }).join("") + "</div></section>");
    });
  }

  /* ------------------------------------------------- grammar page ------- */
  var gramFilters = { level: "", tag: "", q: "" };
  function pageGrammar() {
    setHTML(appEl, "<div class='empty'>Загрузка грамматики…</div>");
    Promise.all([JLPT.grammar(), JLPT.meta()]).then(function (res) {
      var all = res[0], meta = res[1];
      var tagNames = {};
      meta.tags.forEach(function (t) { tagNames[t.tag] = t.ru; });
      var usedTags = {};
      all.forEach(function (g) { (g.tags || []).forEach(function (t) { usedTags[t] = (usedTags[t] || 0) + 1; }); });
      var tagKeys = Object.keys(usedTags).sort(function (a, b) { return usedTags[b] - usedTags[a]; });

      setHTML(appEl,
        "<section class='section'><h2>Грамматика N5 + N4</h2>" +
        "<p class='sub'>" + all.length + " конструкций: образование, значение, темы и примеры с переводом.</p>" +
        "<div class='filters'>" +
          "<input class='input' id='q' placeholder='например: たい, conditional, если бы' value=" + JSON.stringify(gramFilters.q) + ">" +
          "<button class='chip" + (gramFilters.level === "" ? " active" : "") + "' data-l=''>Все</button>" +
          "<button class='chip" + (gramFilters.level === "N5" ? " active" : "") + "' data-l='N5'>N5</button>" +
          "<button class='chip" + (gramFilters.level === "N4" ? " active" : "") + "' data-l='N4'>N4</button>" +
          "<select class='input' id='tag' style='min-width:210px'><option value=''>Все темы</option>" +
            tagKeys.map(function (t) {
              return "<option value='" + esc(t) + "'" + (gramFilters.tag === t ? " selected" : "") + ">" + esc(tagNames[t] || t) + " (" + usedTags[t] + ")</option>";
            }).join("") + "</select>" +
          "<button class='btn violet' id='drill'>Тренировать этот набор</button>" +
          "<span class='count' id='count'></span>" +
        "</div><div class='grid cols-2' id='list'></div></section>");

      var qEl = document.getElementById("q"), tagEl = document.getElementById("tag");
      var listEl = document.getElementById("list"), countEl = document.getElementById("count");
      function filtered() {
        var q = gramFilters.q.trim().toLowerCase();
        return all.filter(function (g) {
          if (gramFilters.level && g.level !== gramFilters.level) return false;
          if (gramFilters.tag && (g.tags || []).indexOf(gramFilters.tag) < 0) return false;
          if (!q) return true;
          if (g.pattern.toLowerCase().indexOf(q) >= 0) return true;
          if (g.ru && g.ru.toLowerCase().indexOf(q) >= 0) return true;
          if (g.formationRu && g.formationRu.toLowerCase().indexOf(q) >= 0) return true;
          if (g.romaji && JLPT.normRomaji(g.romaji).indexOf(JLPT.normRomaji(q)) >= 0) return true;
          return false;
        });
      }
      function draw() {
        var rows = filtered();
        countEl.textContent = rows.length + " конструкций";
        listEl.innerHTML = rows.map(function (g) { return cardGrammar(g, tagNames); }).join("") || "<div class='empty'>Не найдено.</div>";
      }
      qEl.oninput = function () { gramFilters.q = qEl.value; draw(); };
      tagEl.onchange = function () { gramFilters.tag = tagEl.value; draw(); };
      Array.prototype.forEach.call(document.querySelectorAll("[data-l]"), function (b) {
        b.onclick = function () {
          gramFilters.level = b.getAttribute("data-l");
          Array.prototype.forEach.call(document.querySelectorAll("[data-l]"), function (x) { x.classList.toggle("active", x === b); });
          draw();
        };
      });
      document.getElementById("drill").onclick = function () {
        var rows = filtered();
        if (!rows.length) return;
        location.hash = "#/train?scope=grammar&level=" + (gramFilters.level || "") + "&keys=" +
          encodeURIComponent(rows.map(function (g) { return g.id; }).join(","));
      };
      draw();
    });
  }

  /* ------------------------------------------------- train page --------- */
  var trainSel = { scope: "vocab", mode: "flash", level: "", count: 20, focus: "mix" };
  function pageTrain(query) {
    if (query.scope) trainSel.scope = query.scope;
    trainSel.keys = query.keys ? query.keys.split(",").filter(Boolean) : null;
    if (query.level) trainSel.level = query.level;
    if (!modeValid(trainSel.scope, trainSel.mode)) trainSel.mode = "flash";
    var scopeLabel = SCOPE_LABEL[trainSel.scope];

    setHTML(appEl,
      "<section class='section'><h2>Тренажёр запоминания</h2>" +
      "<p class='sub'>Выберите материал и режим. Ответы попадают в интервальную очередь: то, что вы путаете, возвращается чаще.</p>" +
      "<div class='filters'>" +
        "<button class='chip" + (trainSel.scope === "vocab" ? " active" : "") + "' data-s='vocab'>Слова</button>" +
        "<button class='chip" + (trainSel.scope === "kanji" ? " active" : "") + "' data-s='kanji'>Кандзи</button>" +
        "<button class='chip" + (trainSel.scope === "grammar" ? " active" : "") + "' data-s='grammar'>Грамматика</button>" +
        "<span style='width:14px'></span>" +
        "<button class='chip" + (trainSel.level === "" ? " active" : "") + "' data-l=''>N5 + N4</button>" +
        "<button class='chip" + (trainSel.level === "N5" ? " active" : "") + "' data-l='N5'>N5</button>" +
        "<button class='chip" + (trainSel.level === "N4" ? " active" : "") + "' data-l='N4'>N4</button>" +
        "<span style='width:14px'></span>" +
        "<button class='chip" + (trainSel.focus === "mix" ? " active" : "") + "' data-f='mix'>смешанный</button>" +
        "<button class='chip" + (trainSel.focus === "new" ? " active" : "") + "' data-f='new'>новые</button>" +
        "<button class='chip" + (trainSel.focus === "due" ? " active" : "") + "' data-f='due'>к повторению</button>" +
        "<button class='chip" + (trainSel.focus === "weak" ? " active" : "") + "' data-f='weak'>слабые</button>" +
        "<span style='width:14px'></span>" +
        "<button class='chip" + (trainSel.count === 10 ? " active" : "") + "' data-c='10'>10 вопросов</button>" +
        "<button class='chip" + (trainSel.count === 20 ? " active" : "") + "' data-c='20'>20</button>" +
        "<button class='chip" + (trainSel.count === 40 ? " active" : "") + "' data-c='40'>40</button>" +
      "</div>" +
      (trainSel.keys ? "<div class='notice'>Тренировка из выбранного вами набора (" + trainSel.keys.length + "). <a href='#/train'>сбросить</a></div>" : "") +
      "<div class='train-hub section' id='modes'></div>" +
      "<div id='trainer' class='section'></div></section>");

    var modesEl = document.getElementById("modes");
    function drawModes() {
      modesEl.innerHTML = JLPT.trainModes.filter(function (m) { return m.scope === trainSel.scope; }).map(function (m) {
        return "<div class='card link mode-card' data-m='" + m.id + "'><div class='emoji'>" + m.emoji + "</div>" +
          "<h3>" + esc(m.title) + "</h3><p>" + esc(m.desc) + "</p>" +
          "<div class='row' style='margin-top:12px'><button class='btn pink'>Начать</button></div></div>";
      }).join("");
      Array.prototype.forEach.call(modesEl.querySelectorAll("[data-m]"), function (el) {
        el.onclick = function () { startTraining(el.getAttribute("data-m")); };
      });
    }
    drawModes();

    Array.prototype.forEach.call(document.querySelectorAll("[data-s]"), function (b) {
      b.onclick = function () {
        trainSel.scope = b.getAttribute("data-s"); trainSel.keys = null;
        pageTrain({ scope: trainSel.scope });
      };
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-l]"), function (b) {
      b.onclick = function () {
        trainSel.level = b.getAttribute("data-l");
        Array.prototype.forEach.call(document.querySelectorAll("[data-l]"), function (x) { x.classList.toggle("active", x === b); });
      };
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-f]"), function (b) {
      b.onclick = function () {
        trainSel.focus = b.getAttribute("data-f");
        Array.prototype.forEach.call(document.querySelectorAll("[data-f]"), function (x) { x.classList.toggle("active", x === b); });
      };
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-c]"), function (b) {
      b.onclick = function () {
        trainSel.count = parseInt(b.getAttribute("data-c"), 10);
        Array.prototype.forEach.call(document.querySelectorAll("[data-c]"), function (x) { x.classList.toggle("active", x === b); });
      };
    });

    if (trainSel.keys && trainSel.keys.length) startTraining(trainSel.mode || "flash");
    function startTraining(modeId) {
      trainSel.mode = modeId;
      var mount = document.getElementById("trainer");
      mount.innerHTML = "<div class='empty'>Подбираю карточки…</div>";
      JLPT.pool(trainSel.scope, trainSel.level).then(function (pool) {
        if (trainSel.scope === "vocab" && modeId === "reading") {
          pool = pool.filter(function (e) { return !e.data.kanaOnly; });
        }
        var keys = trainSel.keys;
        if (keys && keys.length) {
          pool = pool.filter(function (e) {
            return keys.indexOf(e.kind === "w" ? String(e.data.id) : e.key.split(":")[1]) >= 0;
          });
        }
        if (!pool.length) { mount.innerHTML = "<div class='empty'>В этом наборе нет материала.</div>"; return; }
        var queue = JLPT.buildQueue(pool, trainSel.count, trainSel.focus);
        var cfg = {
          scope: trainSel.scope, mode: modeId, level: trainSel.level,
          scopeLabel: scopeLabel + (keys && keys.length ? " (выбранный набор)" : ""),
          pool: pool, queue: queue,
          start: function (m) { JLPT.train(cfg, m); }
        };
        JLPT.train(cfg, mount);
        mount.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
  }

  /* ------------------------------------------------- progress page ------ */
  function pageProgress() {
    var st = JLPT.stats();
    var max = Math.max.apply(null, st.boxes) || 1;
    var bars = st.boxes.map(function (n, i) {
      var label = ["совсем новое", "почти забыто", "нормально", "хорошо помню", "знаю", "отлично"][i] || ("уровень " + i);
      return "<div class='bar'><span>" + label + "</span><span class='track'><i style='width:" +
        Math.round((n / max) * 100) + "%'></i></span><span>" + n + "</span></div>";
    }).join("");
    var sessions = (JLPT.store.state.sessions || []).slice(-12).reverse().map(function (s) {
      return "<div class='pill'>" + new Date(s.at).toLocaleString("ru-RU") + " · " + esc(SCOPE_LABEL[s.scope] || s.scope) +
        " · " + s.right + "/" + s.asked + " (" + s.accuracy + "%)</div>";
    }).join(" ");

    setHTML(appEl,
      "<section class='section'><h2>Прогресс</h2>" +
      "<p class='sub'>Данные хранятся в этом браузере (localStorage), ничего не отправляется на сервер.</p>" +
      "<div class='hero-stats' style='margin-bottom:18px'>" +
        "<div class='stat'><b>" + st.items + "</b><span>изучаемых элементов</span></div>" +
        "<div class='stat'><b>" + st.accuracy + "%</b><span>верных ответов</span></div>" +
        "<div class='stat'><b>" + st.due + "</b><span>к повторению сейчас</span></div>" +
        "<div class='stat'><b>" + st.weak + "</b><span>слабых мест</span></div>" +
        "<div class='stat'><b>" + (st.byKind.w || 0) + " / " + (st.byKind.k || 0) + " / " + (st.byKind.g || 0) + "</b><span>слова / кандзи / грамматика</span></div>" +
      "</div>" +
      "<div class='card'><h3>Уровни памяти</h3><div style='margin-top:12px;display:grid;gap:8px'>" + bars + "</div></div>" +
      "<div class='card' style='margin-top:14px'><h3>Последние тренировки</h3><div class='row' style='margin-top:10px'>" +
        (sessions || "<span class='count'>пока нет тренировок</span>") + "</div></div>" +
      "<div class='row' style='margin-top:16px'>" +
        "<a class='btn pink' href='#/train'>Продолжить тренировку</a>" +
        "<button class='btn ghost' id='reset'>Сбросить прогресс</button>" +
      "</div></section>");
    document.getElementById("reset").onclick = function () {
      if (window.confirm("Удалить весь прогресс тренировок?")) { JLPT.store.reset(); pageProgress(); }
    };
  }

  /* ------------------------------------------------- router ------------- */
  var appEl = document.getElementById("app");
  function parseHash() {
    var raw = (location.hash || "#/").slice(1);
    var q = "";
    var qi = raw.indexOf("?");
    if (qi >= 0) { q = raw.slice(qi + 1); raw = raw.slice(0, qi); }
    var query = {};
    q.split("&").forEach(function (pair) {
      if (!pair) return;
      var kv = pair.split("=");
      query[decodeURIComponent(kv[0])] = decodeURIComponent(kv[1] || "");
    });
    var parts = raw.split("/").filter(Boolean);
    return { path: parts.map(function (p) { return decodeURIComponent(p); }), query: query };
  }

  function route() {
    var r = parseHash();
    var top = r.path[0] || "home";
    Array.prototype.forEach.call(document.querySelectorAll("#nav a"), function (a) {
      a.classList.toggle("active", a.getAttribute("href") === "#/" + (top === "home" ? "" : top));
    });
    if (top === "words") return pageWords(r.query);
    if (top === "kanji") return r.path[1] ? pageKanjiChar(r.path[1]) : pageKanji();
    if (top === "grammar") return pageGrammar();
    if (top === "train") return pageTrain(r.query);
    if (top === "progress") return pageProgress();
    return pageHome();
  }
  window.addEventListener("hashchange", route);

  var soundBtn = document.getElementById("sound-btn");
  function paintSound() { soundBtn.setAttribute("aria-pressed", JLPT.soundOn() ? "true" : "false"); }
  paintSound();
  soundBtn.onclick = function () {
    JLPT.store.state.settings.sound = !JLPT.soundOn();
    JLPT.store.save(); paintSound();
  };

  route();
})();
