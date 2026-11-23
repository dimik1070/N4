/* Тренажёр: карточки, тесты с вариантами и ввод ответа. */
(function () {
  "use strict";
  var JLPT = window.JLPT;
  var esc = JLPT.esc, fu = JLPT.furigana;

  var MODES = [
    { scope: "vocab", id: "flash", title: "Карточки слов", emoji: "🌸", desc: "Японская карточка → перевод. Отмечайте, помните вы слово или нет: сложное возвращается чаще." },
    { scope: "vocab", id: "choice-ru", title: "Слово → перевод", emoji: "🎴", desc: "Показано японское слово, нужно выбрать русское значение." },
    { scope: "vocab", id: "choice-jp", title: "Перевод → слово", emoji: "🔎", desc: "Показано значение, нужно найти японское слово." },
    { scope: "vocab", id: "reading", title: "Прочитай слово", emoji: "✍️", desc: "Кандзи без фуриганы — введите чтение хираганой или ромадзи." },
    { scope: "kanji", id: "flash", title: "Карточки кандзи", emoji: "🈯", desc: "Иероглиф → чтения и значения." },
    { scope: "kanji", id: "kanji-reading", title: "Чтение кандзи", emoji: "🔊", desc: "Выберите верное онъёме или кунъёме иероглифа." },
    { scope: "kanji", id: "kanji-meaning", title: "Значение кандзи", emoji: "💡", desc: "Выберите значение иероглифа." },
    { scope: "kanji", id: "kanji-strokes", title: "Сколько черточек", emoji: "🖊️", desc: "Тренирует зрительную память на структуру иероглифа." },
    { scope: "grammar", id: "flash", title: "Карточки грамматики", emoji: "📚", desc: "Конструкция → значение, образование и пример." },
    { scope: "grammar", id: "gram-meaning", title: "Конструкция → смысл", emoji: "🧩", desc: "Выберите значение грамматической конструкции." },
    { scope: "grammar", id: "gram-pattern", title: "Смысл → конструкция", emoji: "🎯", desc: "По русскому значению нужно восстановить конструкцию." },
    { scope: "grammar", id: "gram-example", title: "Что за конструкция?", emoji: "🔍", desc: "Предложение на японском — определите использованную конструкцию." }
  ];
  JLPT.trainModes = MODES;

  function modeById(scope, id) {
    for (var i = 0; i < MODES.length; i++) if (MODES[i].scope === scope && MODES[i].id === id) return MODES[i];
    return null;
  }

  /* ------------------------------------------------------ pools ---------- */
  function poolFrom(list, kind) {
    return list.map(function (item) {
      var o = { kind: kind };
      if (kind === "w") { o.key = "w:" + item.id; o.data = item; }
      else if (kind === "k") { o.key = "k:" + item.char; o.data = item; }
      else { o.key = "g:" + item.id; o.data = item; }
      return o;
    });
  }
  JLPT.pool = function (scope, level) {
    if (scope === "vocab") return JLPT.vocab(level).then(poolFromFactory("w"));
    if (scope === "kanji") {
      return JLPT.kanji().then(function (list) {
        var filtered = level ? list.filter(function (k) { return k.level === level; }) : list;
        return poolFrom(filtered, "k");
      });
    }
    return JLPT.grammar().then(function (list) {
      var filtered = level ? list.filter(function (g) { return g.level === level; }) : list;
      return poolFrom(filtered, "g");
    });
  };
  function poolFromFactory(kind) {
    return function (list) { return poolFrom(list, kind); };
  }

  /* -------------------------------------------------- distractors ------- */
  function pickOptions(correctText, pool, exclude, labeler, limit) {
    var seen = {}; seen[correctText] = true;
    var opts = [{ text: correctText, correct: true }];
    var shuffled = JLPT.shuffle(pool);
    for (var i = 0; i < shuffled.length && opts.length < (limit || 4); i++) {
      var entry = shuffled[i];
      if (entry === exclude) continue;
      var label = labeler(entry);
      if (!label || seen[label]) continue;
      if (sameAnswer(correctText, label)) continue;
      seen[label] = true;
      opts.push({ text: label, correct: false });
    }
    return JLPT.shuffle(opts);
  }
  function sameAnswer(a, b) {
    var na = String(a).toLowerCase().replace(/[\s;,.、。]/g, "");
    var nb = String(b).toLowerCase().replace(/[\s;,.、。]/g, "");
    return na === nb;
  }

  /* -------------------------------------------------- questions --------- */
  function vocabQuestion(mode, entry, pool) {
    var v = entry.data;
    if (mode === "flash") {
      return {
        type: "flash", key: entry.key,
        front: "<div class='big'>" + fu(v.word) + "</div>" +
               "<div class='answer-field'>" + fu(v.reading !== v.word ? v.reading : "") + "</div>",
        back: "<div class='answer-field'>" + esc(v.ru) + "</div>" +
              "<div class='kanji-meta'><span>" + esc(v.romaji) + "</span><span>" + esc((v.pos || []).join(", ")) + "</span>" +
              (v.ex[0] ? "<span>" + fu(v.ex[0].ja) + "</span>" : "") + "</div>",
        explain: v.word + " [" + v.reading + "] — " + v.ru
      };
    }
    if (mode === "choice-ru") {
      var opts = pickOptions(v.ru, pool, entry, function (e) { return e.data.ru; });
      return {
        type: "choice", key: entry.key,
        prompt: "<div class='big'>" + fu(v.word) + "</div>" +
                "<div class='answer-field'>" + (v.reading !== v.word ? fu(v.reading) : esc(v.romaji)) + "</div>",
        question: "Что означает это слово?",
        options: opts, explain: v.ru + " · " + (v.ex[0] ? fu(v.ex[0].ja) + " — " + v.ex[0].ru : "")
      };
    }
    if (mode === "choice-jp") {
      var o2 = pickOptions(v.word, pool, entry, function (e) { return e.data.word; });
      return {
        type: "choice", key: entry.key,
        prompt: "<div class='big' style='font-size:30px'>" + esc(v.ru) + "</div>",
        question: "Какое японское слово так переводится?",
        options: o2, explain: v.word + " [" + v.reading + "] — " + v.ru
      };
    }
    if (mode === "reading") {
      var acceptKana = JLPT.normKana(v.reading);
      var acceptRo = JLPT.normRomaji(v.romaji);
      return {
        type: "type", key: entry.key,
        prompt: "<div class='big'>" + esc(v.word) + "</div>",
        question: "Введите чтение хираганой или ромадзи" +
                  (v.ex[0] ? " · подсказка: " + esc(v.ex[0].ru) : ""),
        check: function (input) {
          var i = String(input || "");
          if (JLPT.hasKana(i)) return JLPT.normKana(i) === acceptKana;
          return JLPT.normRomaji(i) === acceptRo && acceptRo.length > 0;
        },
        expected: fu(v.reading) + " · " + esc(v.romaji),
        explain: (v.ex[0] ? fu(v.ex[0].ja) + " — " + v.ex[0].ru : "")
      };
    }
    return null;
  }

  function validReading(kanji, reading) {
    var norm = JLPT.normKana(reading);
    var lists = (kanji.on || []).concat(kanji.kun || []);
    for (var i = 0; i < lists.length; i++) {
      var r = String(lists[i]).replace(/[‧．.]/g, "").replace(/[々〻]/g, "");
      if (JLPT.normKana(r) === norm) return true;
      if (JLPT.normKana(reading).length > 1 && JLPT.normKana(r).indexOf(norm) === 0) return true;
    }
    return false;
  }
  function kanjiQuestion(mode, entry, pool) {
    var k = entry.data;
    var meta = "черточек: " + (k.strokes || "?") + (k.grade ? " · класс " + k.grade : "") +
               (k.radical ? " · радикал " + k.radical : "");
    if (mode === "flash") {
      return {
        type: "flash", key: entry.key,
        front: "<div class='big' style='font-size:76px'>" + esc(k.char) + "</div><div class='kanji-meta'><span>" + meta + "</span></div>",
        back: "<div class='answer-field'>" + esc(k.ru) + "</div>" +
              "<div class='kanji-meta'><span>オン: " + esc((k.on || []).join("・")) + "</span><span>クン: " + esc((k.kun || []).join("・")) + "</span></div>",
        explain: k.char + " — " + k.ru
      };
    }
    if (mode === "kanji-reading") {
      var lists = (k.on || []).concat(k.kun || []);
      var correct = lists.length ? lists[Math.floor(Math.random() * lists.length)].replace(/[‧．.]/g, "") : (k.on[0] || "");
      var opts = pickOptions(correct, pool, entry, function (e) {
        var d = e.data, l = (d.on || []).concat(d.kun || []);
        return l.length ? l[Math.floor(Math.random() * l.length)].replace(/[‧．.]/g, "") : "";
      });
      opts.forEach(function (o) { o.correct = validReading(k, o.text); });
      if (!opts.some(function (o) { return o.correct; })) opts[0] = { text: correct, correct: true };
      return {
        type: "choice", key: entry.key,
        prompt: "<div class='big' style='font-size:76px'>" + esc(k.char) + "</div>",
        question: "Выберите верное чтение этого иероглифа",
        options: opts.map(function (o) { return { text: o.text, html: fu(o.text), correct: o.correct }; }),
        explain: k.char + ": " + (k.on || []).join("・") + " / " + (k.kun || []).join("・") + " — " + k.ru
      };
    }
    if (mode === "kanji-meaning") {
      var o3 = pickOptions(k.ru, pool, entry, function (e) { return e.data.ru; });
      return {
        type: "choice", key: entry.key,
        prompt: "<div class='big' style='font-size:76px'>" + esc(k.char) + "</div>",
        question: "Что означает этот иероглиф?",
        options: o3, explain: k.char + " — " + k.ru + " (" + meta + ")"
      };
    }
    if (mode === "kanji-strokes") {
      var trueN = k.strokes || 0;
      var nums = [trueN];
      while (nums.length < 4) {
        var cand = Math.max(1, trueN + (Math.floor(Math.random() * 9) - 4));
        if (nums.indexOf(cand) < 0) nums.push(cand);
      }
      var opts2 = JLPT.shuffle(nums).map(function (n) { return { text: String(n), correct: n === trueN }; });
      return {
        type: "choice", key: entry.key,
        prompt: "<div class='big' style='font-size:76px'>" + esc(k.char) + "</div>",
        question: "Сколько черточек в этом иероглифе?",
        options: opts2, explain: k.char + " — " + trueN + " черточек · " + k.ru
      };
    }
    return null;
  }

  function grammarQuestion(mode, entry, pool) {
    var g = entry.data;
    var ex = g.ex[0];
    if (mode === "flash") {
      return {
        type: "flash", key: entry.key,
        front: "<div class='big'>" + esc(g.pattern) + "</div>" +
               "<div class='answer-field'>" + esc(g.romaji || "") + "</div>",
        back: "<div class='answer-field'>" + esc(g.ru) + "</div>" +
              "<div class='kanji-meta'><span>" + esc(g.formationRu || "") + "</span></div>" +
              (ex ? "<div class='example'><div class='ja'>" + fu(ex.fu) + "</div><div class='ru'>" + esc(ex.ru) + "</div></div>" : ""),
        explain: g.pattern + " — " + g.ru
      };
    }
    if (mode === "gram-meaning") {
      var opts = pickOptions(g.ru, pool, entry, function (e) { return e.data.ru; });
      return {
        type: "choice", key: entry.key,
        prompt: "<div class='big' style='font-size:40px'>" + esc(g.pattern) + "</div>" +
                (g.romaji ? "<div class='answer-field'>" + esc(g.romaji) + "</div>" : ""),
        question: "Что выражает эта конструкция?",
        options: opts, explain: g.pattern + " — " + g.ru + (g.formationRu ? " · " + g.formationRu : "")
      };
    }
    if (mode === "gram-pattern") {
      var o2 = pickOptions(g.pattern, pool, entry, function (e) { return e.data.pattern; });
      return {
        type: "choice", key: entry.key,
        prompt: "<div class='big' style='font-size:30px'>" + esc(g.ru) + "</div>",
        question: "Какая конструкция так работает?",
        options: o2, explain: g.pattern + " — " + g.ru
      };
    }
    if (mode === "gram-example") {
      var examples = g.ex.length ? g.ex : null;
      if (!examples) return grammarQuestion("gram-meaning", entry, pool);
      var e = examples[Math.floor(Math.random() * examples.length)];
      var o3 = pickOptions(g.pattern, pool, entry, function (x) { return x.data.pattern; });
      return {
        type: "choice", key: entry.key,
        prompt: "<div class='big' style='font-size:26px'>" + fu(e.fu) + "</div>" +
                "<div class='answer-field' style='font-size:16px'>" + esc(e.ru) + "</div>",
        question: "Какая конструкция здесь использована?",
        options: o3, explain: g.pattern + " — " + g.ru + (g.formationRu ? " · " + g.formationRu : "")
      };
    }
    return null;
  }

  function buildQuestion(scope, mode, entry, pool) {
    var q = null;
    if (scope === "vocab") q = vocabQuestion(mode, entry, pool);
    else if (scope === "kanji") q = kanjiQuestion(mode, entry, pool);
    else q = grammarQuestion(mode, entry, pool);
    if (q && q.key === undefined) return null;
    if (q) { q.scope = scope; q.mode = mode; }
    return q;
  }

  /* -------------------------------------------------- session ----------- */
  JLPT.train = function (cfg, mount) {
    var pool = cfg.pool, queue = cfg.queue, idx = 0;
    var right = 0, wrong = 0, streak = 0, bestStreak = 0, mistakes = [];
    var started = Date.now();
    var answered = [];
    var keyFilter = cfg.keys ? new Set(cfg.keys) : null;
    if (keyFilter) {
      queue = queue.filter(function (entry) { return keyFilter.has(entry.key); });
      var extra = pool.filter(function (entry) { return keyFilter.has(entry.key) && queue.indexOf(entry) < 0; });
      queue = queue.concat(extra);
    }
    if (!queue.length) {
      mount.innerHTML = "<div class='empty'>Нет материала для тренировки — выберите другой уровень или набор.</div>";
      return;
    }
    var levelText = cfg.level ? cfg.level : "N5 + N4";
    var mode = modeById(cfg.scope, cfg.mode);

    function renderShell(body) {
      var done = right + wrong;
      var total = queue.length;
      mount.innerHTML =
        "<div class='session'>" +
          "<div class='row' style='justify-content:space-between;margin-bottom:12px'>" +
            "<div class='session-stats'>" +
              "<span class='pill'>" + esc(mode ? mode.title : cfg.mode) + " · " + esc(cfg.scopeLabel) + " · " + esc(levelText) + "</span>" +
              "<span class='pill'>" + (done + 1) + " / " + total + "</span>" +
              "<span class='pill'>верных " + right + " · ошибочных " + wrong + "</span>" +
              (streak >= 3 ? "<span class='pill streak'>серия " + streak + " 🔥</span>" : "") +
            "</div>" +
            "<button class='btn ghost' id='quit'>Завершить</button>" +
          "</div>" +
          "<div class='progress-line'><i style='width:" + Math.round((done / total) * 100) + "%'></i></div>" +
          body +
        "</div>";
      var quit = document.getElementById("quit");
      if (quit) quit.onclick = finish;
    }

    function current() {
      var entry = queue[idx];
      var q = buildQuestion(cfg.scope, cfg.mode, entry, pool);
      if (!q) { idx++; return null; }
      q.entry = entry;
      return q;
    }

    function renderQuestion() {
      if (idx >= queue.length) {
        if (!answered.length) {
          mount.innerHTML = "<div class='empty'>Для этого режима в выбранном наборе нет подходящего материала.</div>";
          return;
        }
        return finish();
      }
      var q = current();
      if (!q) return renderQuestion();
      if (q.type === "flash") {
        renderShell(
          "<div class='prompt'>Карточка " + (idx + 1) + " — нажмите, чтобы перевернуть</div>" +
          "<div class='flashcard' id='fc'>" + q.front + "<div class='flip-hint'>нажмите / пробел</div></div>" +
          "<div id='fb'></div>"
        );
        var fc = document.getElementById("fc");
        var flipped = false;
        function flip() {
          if (flipped) return;
          flipped = true;
          fc.innerHTML = q.back + "<div class='flip-hint'>оцените себя</div>";
          document.getElementById("fb").innerHTML =
            "<div class='row' style='margin-top:16px'>" +
            "<button class='btn pink' data-grade='0'>Не помню</button>" +
            "<button class='btn violet' data-grade='1'>Почти</button>" +
            "<button class='btn' data-grade='2'>Помню</button>" +
            "</div>";
          Array.prototype.forEach.call(document.querySelectorAll("[data-grade]"), function (b) {
            b.onclick = function () {
              var ok = b.getAttribute("data-grade") === "2";
              var half = b.getAttribute("data-grade") === "1";
              var graded = JLPT.grade(q.key, ok ? true : (half && JLPT.item(q.key).box >= 2));
              if (ok) { right++; streak++; } else { wrong++; mistakes.push(q); streak = 0; }
              answered.push({ key: q.key, ok: ok });
              bestStreak = Math.max(bestStreak, streak);
              JLPT.beep(ok ? "ok" : "no");
              idx++;
              renderQuestion();
            };
          });
        }
        fc.onclick = flip;
        mount._flip = flip;
        mount._type = null;
        return;
      }
      if (q.type === "choice") {
        var optsHtml = q.options.map(function (o, i) {
          return "<button class='opt' data-i='" + i + "'><b>" + (i + 1) + ".</b> " + (o.html || esc(o.text)) + "</button>";
        }).join("");
        renderShell(
          "<div class='prompt'>" + esc(q.question) + "</div>" + q.prompt +
          "<div class='opts' id='opts'>" + optsHtml + "</div><div id='fb'></div>"
        );
        mount._flip = null; mount._type = null;
        var buttons = document.querySelectorAll("#opts .opt");
        Array.prototype.forEach.call(buttons, function (b) {
          b.onclick = function () { answerChoice(parseInt(b.getAttribute("data-i"), 10)); };
        });
        function answerChoice(i) {
          var chosen = q.options[i];
          if (chosen._done) return;
          Array.prototype.forEach.call(buttons, function (b) {
            var o = q.options[parseInt(b.getAttribute("data-i"), 10)];
            b.disabled = true;
            if (o.correct) b.classList.add("correct");
            else if (o === chosen) b.classList.add("wrong");
            else b.classList.add("dim");
          });
          var ok = !!chosen.correct;
          JLPT.grade(q.key, ok);
          if (ok) { right++; streak++; } else { wrong++; mistakes.push(q); streak = 0; }
          answered.push({ key: q.key, ok: ok });
          bestStreak = Math.max(bestStreak, streak);
          JLPT.beep(ok ? "ok" : "no");
          document.getElementById("fb").innerHTML =
            "<div class='feedback " + (ok ? "ok" : "no") + "'>" + (ok ? "Верно. " : "Неверно. ") + fu(q.explain || "") +
            "</div><div class='row' style='margin-top:14px'><button class='btn' id='next'>Далее →</button></div>";
          var next = document.getElementById("next");
          next.onclick = function () { idx++; renderQuestion(); };
          next.focus();
        }
        mount._answer = answerChoice;
        return;
      }
      // typed answer
      renderShell(
        "<div class='prompt'>" + esc(q.question) + "</div>" + q.prompt +
        "<div class='row' style='margin-top:18px'>" +
          "<input class='input' id='ans' autocomplete='off' spellcheck='false' placeholder='ваш ответ' style='flex:1;min-width:220px'>" +
          "<button class='btn' id='check'>Проверить</button>" +
        "</div><div id='fb'></div>"
      );
      var input = document.getElementById("ans");
      input.focus();
      var checked = false;
      function checkType() {
        if (checked) return;
        var value = input.value;
        if (!value.trim()) { input.focus(); return; }
        checked = true;
        var ok = !!q.check(value);
        JLPT.grade(q.key, ok);
        if (ok) { right++; streak++; } else { wrong++; mistakes.push(q); streak = 0; }
        answered.push({ key: q.key, ok: ok });
        bestStreak = Math.max(bestStreak, streak);
        JLPT.beep(ok ? "ok" : "no");
        input.disabled = true;
        document.getElementById("check").disabled = true;
        document.getElementById("fb").innerHTML =
          "<div class='feedback " + (ok ? "ok" : "no") + "'>" +
          (ok ? "Верно. " : "Неверно. Правильный ответ: ") + q.expected +
          (q.explain ? "<br>" + fu(q.explain) : "") +
          "</div><div class='row' style='margin-top:14px'><button class='btn' id='next'>Далее →</button></div>";
        var next = document.getElementById("next");
        next.onclick = function () { idx++; renderQuestion(); };
        next.focus();
      }
      document.getElementById("check").onclick = checkType;
      input.onkeydown = function (e) { if (e.key === "Enter") { e.preventDefault(); checkType(); } };
      mount._flip = null; mount._type = input;
    }

    function finish() {
      var done = right + wrong;
      var accuracy = done ? Math.round((right / done) * 100) : 0;
      var seconds = Math.max(1, Math.round((Date.now() - started) / 1000));
      JLPT.logSession({
        at: Date.now(), scope: cfg.scope, mode: cfg.mode, level: cfg.level || "N5+N4",
        asked: done, right: right, wrong: wrong, accuracy: accuracy, seconds: seconds, bestStreak: bestStreak
      });
      var wrongHtml = mistakes.slice(0, 12).map(function (q) {
        return "<div class='example'><div class='ja'>" + fu(q.explain || "") + "</div></div>";
      }).join("");
      mount.innerHTML =
        "<div class='session'>" +
          "<div class='prompt'>Тренировка завершена</div>" +
          "<div class='big'>" + accuracy + "%</div>" +
          "<div class='session-stats' style='margin-top:12px'>" +
            "<span class='pill'>ответов " + done + "</span>" +
            "<span class='pill'>верных " + right + "</span>" +
            "<span class='pill'>ошибочных " + wrong + "</span>" +
            "<span class='pill'>лучшая серия " + bestStreak + "</span>" +
            "<span class='pill'>" + seconds + " с</span>" +
          "</div>" +
          (mistakes.length
            ? "<h3 style='margin-top:20px'>Ошибочные моменты</h3>" + wrongHtml +
              "<div class='row' style='margin-top:16px'><button class='btn pink' id='redo'>Потренировать ошибки</button></div>"
            : "<div class='feedback ok' style='margin-top:16px'>Ни одной ошибки — отлично! すごい！</div>") +
          "<div class='row' style='margin-top:14px'>" +
            "<button class='btn violet' id='again'>Ещё раунд</button>" +
            "<a class='btn ghost' href='#/train'>Выбрать другой режим</a>" +
          "</div>" +
        "</div>";
      var redo = document.getElementById("redo");
      if (redo) {
        redo.onclick = function () {
          JLPT.train({
            scope: cfg.scope, scopeLabel: cfg.scopeLabel, mode: cfg.mode, level: cfg.level,
            pool: pool, queue: queue.filter(function (e) { return mistakes.some(function (q) { return q.key === e.key; }); }),
            keys: mistakes.map(function (q) { return q.key; })
          }, mount);
        };
      }
      var again = document.getElementById("again");
      if (again) again.onclick = function () { cfg.start(mount); };
      mount._flip = null; mount._type = null; mount._answer = null;
    }

    document.onkeydown = function (e) {
      if (e.target && /INPUT|TEXTAREA/.test(e.target.tagName)) return;
      if (e.key === " " && mount._flip) { e.preventDefault(); mount._flip(); }
      if ((e.key === "Enter") && document.getElementById("next")) { e.preventDefault(); document.getElementById("next").click(); }
      if (/^[1-9]$/.test(e.key) && mount._answer) {
        var i = parseInt(e.key, 10) - 1;
        var btns = document.querySelectorAll("#opts .opt");
        if (btns[i]) btns[i].click();
      }
    };

    renderQuestion();
  };
})();
