/* Данные, хранилище прогресса и мелкие утилиты. */
(function () {
  "use strict";
  const JLPT = (window.JLPT = window.JLPT || {});

  /* ------------------------------------------------ data loader ---------- */
  const cache = {};
  function loadChunk(name) {
    if (cache[name]) return Promise.resolve(cache[name]);
    return new Promise(function (resolve, reject) {
      const s = document.createElement("script");
      s.src = name + ".js";
      s.onload = function () {
        const data = (window.JLPTDATA || {})[name];
        if (!data) return reject(new Error("chunk " + name + " пуст"));
        cache[name] = data;
        resolve(data);
      };
      s.onerror = function () {
        reject(new Error("не удалось загрузить " + name + ".js"));
      };
      document.head.appendChild(s);
    });
  }

  JLPT.meta = function () { return loadChunk("meta"); };
  JLPT.kanji = function () { return loadChunk("kanji"); };
  JLPT.grammar = function () { return loadChunk("grammar"); };
  JLPT.vocab = function (level) {
    const parts = [];
    if (!level || level === "N5") parts.push(loadChunk("vocabN5"));
    if (!level || level === "N4") parts.push(loadChunk("vocabN4"));
    return Promise.all(parts).then(function (list) {
      const out = [];
      list.forEach(function (part) { out.push.apply(out, part); });
      return out;
    });
  };
  JLPT.vocabByLevel = function (level) { return loadChunk(level === "N5" ? "vocabN5" : "vocabN4"); };

  /* ------------------------------------------------ utils --------------- */
  JLPT.esc = function (v) {
    return String(v == null ? "" : v)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  };

  // {漢字|かんじ} → <ruby>漢字<rt>かんじ</rt></ruby>
  JLPT.furigana = function (text) {
    const src = String(text == null ? "" : text);
    let out = "", i = 0;
    while (i < src.length) {
      const open = src.indexOf("{", i);
      if (open < 0) { out += JLPT.esc(src.slice(i)); break; }
      out += JLPT.esc(src.slice(i, open));
      const close = src.indexOf("}", open);
      if (close < 0) { out += JLPT.esc(src.slice(open)); break; }
      const inner = src.slice(open + 1, close);
      const bar = inner.indexOf("|");
      if (bar < 0) { out += JLPT.esc(inner); }
      else {
        out += "<ruby>" + JLPT.esc(inner.slice(0, bar)) + "<rt>" +
               JLPT.esc(inner.slice(bar + 1)) + "</rt></ruby>";
      }
      i = close + 1;
    }
    return out;
  };

  JLPT.shuffle = function (arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  };
  JLPT.pick = function (arr, n) { return JLPT.shuffle(arr).slice(0, n); };

  // kana/romaji normalization for typed answers
  JLPT.normKana = function (s) {
    return String(s || "")
      .replace(/[\s\u3000\-–—·・]/g, "")
      .replace(/ー{2,}/g, "ー")
      .toLowerCase();
  };
  JLPT.normRomaji = function (s) {
    let r = String(s || "").toLowerCase().replace(/[\s\u3000\-–—·・']/g, "");
    r = r.replace(/[ā]/g, "a").replace(/[ī]/g, "i").replace(/[ū]/g, "u")
         .replace(/[ē]/g, "e").replace(/[ō]/g, "o");
    r = r.replace(/oo/g, "o").replace(/ee/g, "e").replace(/ou/g, "o");
    return r;
  };
  JLPT.hasKana = function (s) { return (/[぀-ヿ]/.test(s)); };
  JLPT.hasKanji = function (s) { return (/[㐀-䶿一-鿿豈-﫿]/.test(s)); };

  JLPT.levelBadge = function (lv) {
    return '<span class="badge ' + (lv === "N5" ? "n5" : "n4") + '">' + lv + "</span>";
  };

  /* ------------------------------------------------ sound --------------- */
  let audioCtx = null;
  JLPT.soundOn = function () { return state.settings.sound !== false; };
  JLPT.beep = function (kind) {
    if (!JLPT.soundOn()) return;
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = "triangle";
      osc.frequency.value = kind === "ok" ? 880 : 220;
      gain.gain.setValueAtTime(0.0001, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.16, audioCtx.currentTime + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.28);
      osc.connect(gain).connect(audioCtx.destination);
      osc.start(); osc.stop(audioCtx.currentTime + 0.3);
    } catch (e) { /* игнорируем */ }
  };

  /* ------------------------------------------------ progress store ------ */
  const KEY = "jlpt4.progress.v1";
  const BOX_SECONDS = [1800, 21600, 86400, 3 * 86400, 7 * 86400, 21 * 86400]; // 30м, 6ч, 1д, 3д, 7д, 21д
  const MAX_BOX = BOX_SECONDS.length - 1;

  function defaults() {
    return { items: {}, sessions: [], settings: { sound: true }, created: Date.now() };
  }
  let state = defaults();
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      state = Object.assign(defaults(), parsed);
      state.items = state.items || {};
      state.sessions = state.sessions || [];
      state.settings = Object.assign({ sound: true }, state.settings || {});
    }
  } catch (e) { state = defaults(); }

  const store = {
    get state() { return state; },
    save: function () {
      try { localStorage.setItem(KEY, JSON.stringify(state)); }
      catch (e) { /* переполнение хранилища */ }
    },
    settings: state.settings,
    reset: function () { state = defaults(); store.save(); }
  };
  JLPT.store = store;
  JLPT.item = function (key) {
    return state.items[key] || (state.items[key] = {
      box: 0, seen: 0, correct: 0, wrong: 0, last: 0, due: 0
    });
  };
  JLPT.isNew = function (key) {
    const it = state.items[key];
    return !it || it.seen === 0;
  };
  JLPT.isDue = function (key) {
    const it = state.items[key];
    return !!it && it.seen > 0 && (it.due || 0) <= Date.now();
  };
  JLPT.isWeak = function (key) {
    const it = state.items[key];
    return !!it && it.wrong >= 2;
  };
  JLPT.grade = function (key, ok) {
    const it = JLPT.item(key);
    it.seen++; it.last = Date.now();
    if (ok) { it.correct++; it.box = Math.min(MAX_BOX, it.box + 1); }
    else { it.wrong++; it.box = 0; }
    it.due = Date.now() + BOX_SECONDS[it.box] * 1000;
    store.save();
    return it;
  };
  JLPT.stats = function () {
    const keys = Object.keys(state.items);
    let seen = 0, correct = 0, wrong = 0, due = 0, weak = 0;
    const boxes = new Array(MAX_BOX + 1).fill(0);
    const byKind = {};
    keys.forEach(function (k) {
      const it = state.items[k];
      if (!it.seen) return;
      seen++; correct += it.correct; wrong += it.wrong;
      boxes[it.box]++;
      if (it.due <= Date.now()) due++;
      if (it.wrong >= 2) weak++;
      const kind = k.split(":")[0];
      byKind[kind] = (byKind[kind] || 0) + 1;
    });
    const sessions = state.sessions.length;
    const answered = correct + wrong;
    return {
      items: seen, correct: correct, wrong: wrong, due: due, weak: weak,
      boxes: boxes, byKind: byKind, sessions: sessions, maxBox: MAX_BOX,
      accuracy: answered ? Math.round((correct / answered) * 100) : 0
    };
  };

  /* queue selection for a training session */
  JLPT.buildQueue = function (pool, count, focus) {
    const now = Date.now();
    const news = [], dues = [], weaks = [], rest = [];
    pool.forEach(function (item) {
      const key = item.key;
      if (JLPT.isNew(key)) news.push(item);
      else if (JLPT.isWeak(key)) weaks.push(item);
      else if ((state.items[key].due || 0) <= now) dues.push(item);
      else rest.push(item);
    });
    let queue;
    if (focus === "new") queue = JLPT.shuffle(news).concat(JLPT.shuffle(dues), JLPT.shuffle(weaks));
    else if (focus === "due") queue = JLPT.shuffle(dues).concat(JLPT.shuffle(weaks), JLPT.shuffle(news));
    else if (focus === "weak") queue = JLPT.shuffle(weaks).concat(JLPT.shuffle(dues), JLPT.shuffle(news));
    else queue = JLPT.shuffle(weaks).concat(JLPT.shuffle(dues), JLPT.shuffle(news), JLPT.shuffle(rest));
    if (!queue.length) queue = JLPT.shuffle(pool);
    return queue.slice(0, count);
  };
  JLPT.logSession = function (rec) { state.sessions.push(rec); store.save(); };
})();
