/* Данные, хранилище прогресса и мелкие утилиты. */
(function () {
  "use strict";
  const JLPT = (window.JLPT = window.JLPT || {});

  /* ------------------------------------------------ data loader ---------- */
  const cache = {};
  const DATA_DIR = ""; // prepare_upload.py меняет это на "" при плоской сборке
  function dataUrl(name) { return DATA_DIR + name; }
  function loadChunk(name) {
    if (cache[name]) return Promise.resolve(cache[name]);
    return new Promise(function (resolve, reject) {
      const s = document.createElement("script");
      s.src = dataUrl(name + ".js");
      s.onload = function () {
        const data = (window.JLPTDATA || {})[name];
        if (!data) return reject(new Error("chunk " + name + " пуст"));
        cache[name] = data;
        resolve(data);
      };
      s.onerror = function () {
        reject(new Error("не удалось загрузить " + dataUrl(name + ".js")));
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

  /* ------------------------------------------------ озвучка ------------- */
  // Текст произношения: фуригана -> чтение, скобки убрать. Та же нормализация,
  // что в gen_audio.py, поэтому ключи манифеста data/audio.js совпадают.
  const SAY_STRIP = /[「」『』（）()〈〉《》・…※→〜~＠]/g;
  JLPT.sayText = function (raw) {
    let t = String(raw == null ? "" : raw).normalize("NFKC");
    t = t.replace(/\{[^{}|]*\|([^{}|]+)\}/g, "$1");
    t = t.replace(/\{([^{}|]+)\}/g, "$1");
    t = t.replace(SAY_STRIP, "");
    return t.replace(/\s+/g, " ").trim();
  };
  JLPT.canSay = function (text) { return (/[぀-ヿ㐀-䶿一-鿿]/.test(text)); };

  // ДВА РЕЖИМА ОЗВУЧКИ.
  //   CLIPS_BUILT = true  — рядом лежат MP3-части (docs/data/audio*.mp3), сайт играет
  //                         готовые записи, а голос браузера служит запасным вариантом.
  //   CLIPS_BUILT = false — записей нет вообще: весь звук создаёт сам браузер через
  //                         Web Speech API (speechSynthesis), поэтому в репозиторий не
  //                         нужно класть ~94 МБ аудио. prepare_upload.py меняет эту
  //                         строку на false при плоской сборке для GitHub.
  let CLIPS_BUILT = false; // prepare_upload.py меняет это на false
  JLPT.clipsBuilt = function () { return CLIPS_BUILT; };

  let audioMeta = null, audioPromise = null, audioFailed = false;
  function loadAudio() {
    if (!CLIPS_BUILT) return Promise.resolve(null);
    if (audioMeta) return Promise.resolve(audioMeta);
    if (audioFailed) return Promise.resolve(null);
    if (audioPromise) return audioPromise;
    audioPromise = loadChunk("audio").then(function (data) {
      audioMeta = data; audioPromise = null; return data;
    }).catch(function () { audioFailed = true; audioPromise = null; return null; });
    return audioPromise;
  }

  const partCache = {};
  function partBuffer(index) {
    if (partCache[index]) return partCache[index];
    partCache[index] = fetch(dataUrl(audioMeta.parts[index].file)).then(function (r) {
      if (!r.ok) throw new Error("http " + r.status);
      return r.arrayBuffer();
    }).catch(function (e) { delete partCache[index]; throw e; });
    return partCache[index];
  }

  let player = null;
  function playClip(text) {
    const clip = audioMeta && audioMeta.clips ? audioMeta.clips[text] : null;
    if (!clip) return Promise.resolve(false);
    return partBuffer(clip[0]).then(function (buf) {
      const blob = new Blob([buf.slice(clip[1], clip[1] + clip[2])], { type: "audio/mpeg" });
      const url = URL.createObjectURL(blob);
      return new Promise(function (resolve) {
        const a = new Audio(url);
        a.playbackRate = JLPT.sayRate();
        if (player) { try { player.pause(); } catch (e) { /* уже остановлен */ } }
        player = a;
        let settled = false;
        const done = function (ok) {
          if (settled) return;
          settled = true;
          URL.revokeObjectURL(url);
          if (player === a) player = null;
          resolve(ok);
        };
        a.addEventListener("playing", function () { done(true); });
        a.addEventListener("error", function () { done(false); });
        const started = a.play();
        if (started && started.catch) started.catch(function () { done(false); });
      });
    }).catch(function () { return false; });
  }

  // Запасной вариант: голос браузера (Web Speech API), если готовой записи нет.
  let voices = [];
  function grabVoices() { voices = (window.speechSynthesis && speechSynthesis.getVoices()) || []; }
  if (window.speechSynthesis) {
    grabVoices();
    speechSynthesis.onvoiceschanged = grabVoices;
    setTimeout(grabVoices, 400);
  }
  JLPT.jaVoices = function () {
    return voices.filter(function (v) { return /^ja/i.test(v.lang || ""); });
  };
  JLPT.allVoices = function () { return voices; };

  function pickVoice() {
    if (!voices.length) grabVoices();
    const wanted = state.settings.voiceName;
    if (wanted) {
      const exact = voices.filter(function (v) { return v.name === wanted; })[0];
      if (exact) return exact;
    }
    return JLPT.jaVoices()[0] || null;
  }
  // Имя голоса, которым сайт будет говорить (пусто, если японского голоса нет).
  JLPT.voiceName = function () { return pickVoice() ? pickVoice().name : ""; };

  let lastVoiceName = "";
  function speakWithBrowserVoice(text) {
    if (!window.speechSynthesis) return false;
    const chosen = pickVoice();
    if (!chosen) return false;
    try {
      const u = new SpeechSynthesisUtterance(text);
      u.lang = chosen.lang || "ja-JP";
      u.voice = chosen;
      u.rate = JLPT.sayRate();
      lastVoiceName = chosen.name;
      // В Chrome speak() сразу после cancel() иногда молчит — говорим следующим кадром.
      try { speechSynthesis.cancel(); } catch (e) { /* уже остановлен */ }
      setTimeout(function () {
        try { speechSynthesis.speak(u); } catch (e) { /* не важно */ }
      }, 24);
      return true;
    } catch (e) { return false; }
  }

  JLPT.voiceOn = function () { return state.settings.voice !== false; };
  JLPT.autoSayOn = function () { return state.settings.autosay !== false; };
  JLPT.browserVoiceOn = function () { return state.settings.speech !== false; };
  JLPT.sayRate = function () { return state.settings.rate || 1; };
  JLPT.stopSay = function () {
    if (player) { try { player.pause(); } catch (e) { /* уже остановлен */ } player = null; }
    if (window.speechSynthesis) { try { speechSynthesis.cancel(); } catch (e) { /* не важно */ } }
  };

  // Главная точка входа: голос браузера; если сборка содержит MP3-записи — сначала они.
  JLPT.say = function (raw) {
    if (!JLPT.voiceOn()) return Promise.resolve(false);
    const text = JLPT.sayText(raw);
    if (!text || !JLPT.canSay(text)) return Promise.resolve(false);
    if (!CLIPS_BUILT) {
      return Promise.resolve(JLPT.browserVoiceOn() ? speakWithBrowserVoice(text) : false);
    }
    return loadAudio().then(function () { return playClip(text); }).then(function (ok) {
      if (ok) return true;
      if (JLPT.browserVoiceOn()) return speakWithBrowserVoice(text);
      return false;
    });
  };

  // Краткое состояние для панели настроек озвучки.
  JLPT.audioStatus = function () {
    return loadAudio().then(function (meta) {
      return {
        clipsBuilt: CLIPS_BUILT,
        clips: meta && meta.clips ? Object.keys(meta.clips).length : 0,
        parts: meta && meta.parts ? meta.parts.length : 0,
        failed: audioFailed,
        voiceName: JLPT.voiceName(),
        lastVoiceName: lastVoiceName,
        jaVoices: JLPT.jaVoices().length,
        voices: JLPT.allVoices().length
      };
    });
  };

  /* ------------------------------------------------ progress store ------ */
  const KEY = "jlpt4.progress.v1";
  const BOX_SECONDS = [1800, 21600, 86400, 3 * 86400, 7 * 86400, 21 * 86400]; // 30м, 6ч, 1д, 3д, 7д, 21д
  const MAX_BOX = BOX_SECONDS.length - 1;

  function defaults() {
    return { items: {}, sessions: [], settings: { sound: true, voice: true, autosay: true, speech: true, rate: 1 }, created: Date.now() };
  }
  let state = defaults();
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      state = Object.assign(defaults(), parsed);
      state.items = state.items || {};
      state.sessions = state.sessions || [];
      state.settings = Object.assign({ sound: true, voice: true, autosay: true, speech: true, rate: 1 }, state.settings || {});
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
