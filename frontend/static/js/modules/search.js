// bibleApp feature module: search — one search screen for every way people look things up.
// Merged via Object.assign in app.js. Markup: <dialog id="search-view"> (index.html);
// styles in css/search.css. Data: GET /api/search (keyword; one result per verse, in the
// reader's translation), GET /api/search/meaning (docs/SEMANTIC_SEARCH_2026-11.md),
// GET /api/topics/search (Nave's), and, offline, chapters saved in IndexedDB.
//
// The reader never picks a mode. What they type decides what leads:
//   reference   "rom 8 28"         -> "Go to Romans 8:28" (Enter goes there)
//   word        G26, ἀγάπη          -> the word's card -> its word study (Enter opens it)
//   phrase      "green pastures"   -> verses with exactly those words, nothing else
//   words       forgiveness        -> verses with the words, then verses about the idea
//   question    verses about ...   -> verses about the idea first, then verses with the words
// Verses "about the idea" come from comparing meanings. They are verses to weigh, never an
// answer, and the screen says so. They load on Enter or after a pause in typing (the
// endpoint allows 30 a minute), are cached, and a verse in both lists is shown once.
//
// The open screen is a history entry (?search=...), so a result opens as a jump and both
// Back and the return chip's "Results" come back to the same query, lists and scroll.
window.BibleModules = window.BibleModules || {};
(() => {
    const KEYWORD_DELAY = 300;     // live keyword search, as before
    const MEANING_DELAY = 1000;    // a pause long enough to mean "I've finished typing"
    const FIRST = 5;               // verses shown per list before "Show all"
    const COMMENTARY_FIRST = 3;
    const ORIGINAL = /[Ͱ-Ͽἀ-῿֐-׿]/;
    const QUESTION = /^(what|what's|whats|how|why|where|when|who|which|is|are|does|do|did|can|could|should|would|will|verses?|scriptures?|passages?|bible|find|show)\b/i;
    const EXAMPLES = ['John 3:16', 'green pastures', 'forgiveness', 'verses about waiting on God', 'G26'];
    const meaningCache = new Map();
    let kwTimer = null;
    let meaningTimer = null;
    let kwGen = 0;
    let meaningGen = 0;

    const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const keyOf = (h) => `${h.book}|${h.chapter}|${h.verse}`;
    const refOf = (h) => `${h.book} ${h.chapter}:${h.verse}`;
    const online = (app) => app.isOnline && !app.forcedOffline && navigator.onLine;

    // The words of a query for the offline search: phrases stay together
    function terms(q) {
        const out = [];
        for (const m of q.matchAll(/"([^"]+)"|([\p{L}\p{N}']+)/gu)) out.push((m[1] || m[2]).toLowerCase());
        return out;
    }

    window.BibleModules.search = {
        srch: {
            q: '', scope: 'all', words: false,    // words: search a reference's words instead
            kw: { status: 'idle', q: null, verses: [], commentary: [], word: null, suggestions: [], offline: false, chapters: 0 },
            meaning: { status: 'idle', q: null, items: [], fallback: false, reveal: false },
            topic: null,
            all: { kw: false, meaning: false, commentary: false },
            semantic: null,                        // /api/semantic/status, once
            announce: '',
            lastHit: null,
        },
        _srchOpener: null,

        srchInit() {
            const dlg = document.getElementById('search-view');
            if (!dlg) return;
            dlg.addEventListener('cancel', (e) => { e.preventDefault(); this.srchClose(); });
            dlg.addEventListener('close', () => { if (this.showSearch) this.showSearch = false; });
            // Other code closes overlays by clearing the flag (a jump, the menu): follow it
            this.$watch('showSearch', (v) => { if (!v && dlg.open) this._srchHideDialog(); });
            this.$watch('translation', () => { if (this.showSearch && this.srch.q) this.srchRun({ meaning: this.srch.meaning.q != null }); });
        },

        // ---------- open / close / history ----------
        openSearch({ q = null, entry = 'push' } = {}) {
            const dlg = document.getElementById('search-view');
            if (!dlg) return;
            if (q != null) this.srch.q = q;
            if (!dlg.open) {
                this._srchOpener = document.activeElement;
                dlg.showModal();
            }
            this.showSearch = true;
            if (entry === 'push' && !window.history.state?.srch) {
                this.navPushState({ ...(window.history.state || {}), srch: this._srchState(true) }, this._srchURL());
            } else if (entry === 'replace') {
                this.navReplaceState({ ...(window.history.state || {}), srch: this._srchState(false) }, this._srchURL());
            }
            if (this.srch.semantic === null) this._srchStatus();
            if (this.srch.q && this.srch.kw.q !== this._srchKey()) this.srchRun();
            this.$nextTick(() => {
                const input = document.getElementById('srch-input');
                input?.focus({ preventScroll: true });
                // A fresh open keeps the last search, selected: typing replaces it
                if (entry === 'push') input?.select();
            });
        },

        // Close: back through the entry this screen pushed, so Back and Close agree
        srchClose() {
            if (!this.showSearch) return;
            if (window.history.state?.srch?.pushed) { window.history.back(); return; }
            this.srchHide();
            if (window.history.state?.srch) {
                const { srch, srchScroll, ...rest } = window.history.state;
                this.navReplaceState(rest, location.pathname);
            }
        },
        srchHide() {
            this.showSearch = false;
            this._srchHideDialog();
        },
        _srchHideDialog() {
            const dlg = document.getElementById('search-view');
            if (dlg?.open) dlg.close();
            const opener = this._srchOpener;
            this._srchOpener = null;
            if (opener && document.contains(opener) && !this.study?.open && !this.ws?.open) opener.focus({ preventScroll: true });
        },

        // From the app's popstate handler (modules/nav.js), when the entry is a search.
        // The passage underneath is put back first (a result may have opened another).
        async srchHandlePop(e) {
            const st = e.state;
            const s = st.srch;
            const loc = this.parsePathReference();
            const r = loc ? BibleRef.parse(loc) : null;
            const sameHere = r?.chapter ? (r.book === this.currentBook && r.chapter === this.currentChapter && !this.combinedPlanReading)
                : (!this.currentBook && !this.combinedPlanReading);
            if (!sameHere) await this.navigate(loc || { home: true }, { source: 'pop', state: st });
            else this.navReturn = st.ret || null;
            if (s.q !== this.srch.q || s.scope !== this.srch.scope) {
                Object.assign(this.srch, { q: s.q || '', scope: s.scope || 'all', words: !!s.words });
                this.srch.kw.q = null;
            }
            this.openSearch({ entry: 'none' });
            if (s.meaning && this.srch.meaning.q !== this._srchKey()) this.srchMeaning();
            this._srchRestoreScroll(st.srchScroll);
        },

        _srchState(pushed) {
            const prev = window.history.state?.srch;
            return { q: this.srch.q, scope: this.srch.scope, words: this.srch.words,
                meaning: this.srch.meaning.q === this._srchKey() && this.srch.meaning.q != null,
                pushed: prev ? !!prev.pushed : pushed };
        },
        _srchURL() {
            return `${location.pathname}?search=${encodeURIComponent(this.srch.q)}`;
        },
        _srchSaveState() {
            if (!window.history.state?.srch) return;
            const body = document.querySelector('#search-view .srch-body');
            this.navReplaceState({ ...window.history.state, srch: this._srchState(false), srchScroll: body ? Math.round(body.scrollTop) : 0 }, this._srchURL());
        },
        _srchRestoreScroll(top) {
            this.$nextTick(() => requestAnimationFrame(() => {
                const body = document.querySelector('#search-view .srch-body');
                if (body && top != null) body.scrollTop = top;
                const last = this.srch.lastHit && document.querySelector(`#search-view [data-hit="${CSS.escape(this.srch.lastHit)}"]`);
                if (last && window.matchMedia('(pointer: fine)').matches) last.focus({ preventScroll: true });
            }));
        },

        // ---------- what was typed ----------
        srchKind(q = this.srch.q) {
            const s = q.trim();
            if (s.length < 2) return 'empty';
            if (/^[GH]\d+$/i.test(s)) return 'strongs';
            if (ORIGINAL.test(s)) return 'original';
            if (!this.srch.words && BibleRef.parse(s).chapter) return 'reference';
            if (/"/.test(s)) return 'phrase';
            const n = s.split(/\s+/).filter(Boolean).length;
            return n >= 3 || QUESTION.test(s) ? 'question' : 'words';
        },
        srchRefLabel() {
            const r = BibleRef.parse(this.srch.q.trim());
            return r.chapter ? BibleRef.format(r) : '';
        },
        _srchKey() { return `${this.srch.q.trim()}|${this.srch.scope}|${this.translation}`; },
        // Meaning search suits words and questions, never a reference, a word number or a quoted phrase
        srchWantsMeaning() {
            const k = this.srchKind();
            return (k === 'words' || k === 'question') && this.srch.scope !== 'commentary' && this.srch.q.trim().length >= 3;
        },

        srchInput() {
            this.srch.words = false;
            this.srch.all = { kw: false, meaning: false, commentary: false };
            clearTimeout(kwTimer);
            clearTimeout(meaningTimer);
            kwTimer = setTimeout(() => this.srchRun(), KEYWORD_DELAY);
            if (this.srchWantsMeaning()) {
                meaningTimer = setTimeout(() => { if (this.srchWantsMeaning()) this.srchMeaning(); }, MEANING_DELAY);
            }
        },
        srchSetScope(scope) {
            if (this.srch.scope === scope) return;
            this.srch.scope = scope;
            this.srch.all = { kw: false, meaning: false, commentary: false };
            this.srchRun({ meaning: this.srch.meaning.q != null && this.srchWantsMeaning() });
        },
        srchExample(q) {
            this.srch.q = q;
            this.srch.words = false;
            this.srchSubmit();
        },
        srchSearchWords() {
            this.srch.words = true;
            this.srchRun({ meaning: this.srchWantsMeaning() });
            this.$nextTick(() => document.getElementById('srch-input')?.focus());
        },

        // Enter / the keyboard's Search key: do the obvious thing for what was typed
        srchSubmit() {
            clearTimeout(kwTimer);
            const kind = this.srchKind();
            if (kind === 'reference') { this.srchGoRef(); return; }
            if ((kind === 'strongs' || kind === 'original') && this.srch.kw.word && this.srch.kw.q === this._srchKey()) {
                this.srchWordStudy(this.srch.kw.word.strong_number);
                return;
            }
            this.srchRun({ meaning: this.srchWantsMeaning() });
            document.getElementById('srch-input')?.blur();   // phones: put the keyboard away to show results
        },

        srchRun({ meaning = false } = {}) {
            this.srchKeyword();
            this.srchTopic();
            if (meaning) this.srchMeaning();
            else if (this.srch.meaning.q !== this._srchKey()) {
                Object.assign(this.srch.meaning, { status: 'idle', q: null, items: [], fallback: false, reveal: false });
                const hit = meaningCache.get(this._srchKey());   // seen before: show it at once
                if (hit && this.srchWantsMeaning()) this._srchMeaningShow(this._srchKey(), hit);
            }
            if (window.history.state?.srch) this._srchSaveState();
        },

        // ---------- keyword search (live) ----------
        async srchKeyword() {
            const q = this.srch.q.trim();
            const key = this._srchKey();
            const kind = this.srchKind();
            const gen = ++kwGen;
            if (kind === 'empty' || kind === 'reference') {
                Object.assign(this.srch.kw, { status: 'idle', q: key, verses: [], commentary: [], word: null, suggestions: [] });
                this._srchAnnounce();
                return;
            }
            this.srch.kw.status = 'loading';
            let data = null;
            let offline = false;
            if (online(this)) {
                try {
                    const r = await fetch(`/api/search?q=${encodeURIComponent(q)}&scope=${encodeURIComponent(this.srch.scope)}&translation=${encodeURIComponent(this.translation)}`);
                    if (r.status === 429) { if (gen === kwGen) Object.assign(this.srch.kw, { status: 'limited', q: key }); this._srchAnnounce(); return; }
                    if (r.ok) data = await r.json();
                    else if (r.status === 503) offline = true;
                } catch { offline = true; }
            } else offline = true;
            if (offline) data = await this._srchLocal(q);
            if (gen !== kwGen) return;
            if (!data) { Object.assign(this.srch.kw, { status: 'error', q: key, verses: [], commentary: [] }); this._srchAnnounce(); return; }
            const results = data.results || [];
            Object.assign(this.srch.kw, {
                status: 'ready', q: key, offline, chapters: data.chapters || 0,
                verses: results.filter(r => r.type === 'verse'),
                commentary: results.filter(r => r.type === 'commentary'),
                word: data.word_info || null, suggestions: data.word_suggestions || [],
            });
            // No verse has these words: look for the idea without waiting for a pause
            if (!offline && !this.srch.kw.verses.length && this.srchWantsMeaning() && this.srch.meaning.q !== key) this.srchMeaning();
            this._srchAnnounce();
        },

        // Offline: verses saved on this device (chapters read with auto-save on, or downloads),
        // in the reader's translation. Every word must appear; a phrase must appear as written.
        async _srchLocal(q) {
            const os = window.offlineStorage;
            const words = terms(q);
            if (!os || !words.length) return { results: [], chapters: 0 };
            const books = this.srch.scope === 'ot' ? new Set(OT_BOOKS) : this.srch.scope === 'nt' ? new Set(NT_BOOKS)
                : this.srch.scope.startsWith('book:') ? new Set([this.srch.scope.slice(5)]) : null;
            if (this.srch.scope === 'commentary') return { results: [], chapters: 0 };
            const pats = words.map(w => new RegExp(`(^|[^\\p{L}])(${w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'iu'));
            try {
                const rows = await os.allVerses(this.translation);
                const chapters = new Set();
                const hits = [];
                for (const v of rows) {
                    chapters.add(`${v.book}|${v.chapter}`);
                    if (books && !books.has(v.book)) continue;
                    if (!pats.every(p => p.test(v.text))) continue;
                    let html = esc(v.text);
                    for (const w of words) {
                        html = html.replace(new RegExp(`(^|[^\\p{L}])(${esc(w).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[\\p{L}']*)`, 'giu'), '$1<mark>$2</mark>');
                    }
                    hits.push({ type: 'verse', book: v.book, chapter: v.chapter, verse: v.verse, snippet: html, translation: this.translation });
                }
                const order = (h) => BIBLE_BOOKS.indexOf(h.book) * 1e6 + h.chapter * 1e3 + h.verse;
                hits.sort((a, b) => order(a) - order(b));
                return { results: hits.slice(0, 100), chapters: chapters.size };
            } catch (e) {
                console.debug('offline search failed', e);
                return { results: [], chapters: 0 };
            }
        },

        // ---------- meaning search (on Enter or a pause) ----------
        async srchMeaning() {
            const key = this._srchKey();
            if (!this.srchWantsMeaning()) return;
            if (!online(this)) {
                Object.assign(this.srch.meaning, { status: 'offline', q: key, items: [] });
                this._srchAnnounce();
                return;
            }
            if (meaningCache.has(key)) { this._srchMeaningShow(key, meaningCache.get(key)); return; }
            const gen = ++meaningGen;
            Object.assign(this.srch.meaning, { status: 'loading', q: key, items: [], fallback: false, reveal: false });
            this._srchAnnounce();
            const scope = this.srch.scope === 'all' ? 'all' : this.srch.scope;
            try {
                const r = await fetch(`/api/search/meaning?q=${encodeURIComponent(this.srch.q.trim())}&mode=meaning&limit=30&scope=${encodeURIComponent(scope)}&translation=${encodeURIComponent(this.translation)}`);
                if (gen !== meaningGen) return;
                if (r.status === 429) { Object.assign(this.srch.meaning, { status: 'limited' }); this._srchAnnounce(); return; }
                if (!r.ok) throw new Error(`HTTP ${r.status}`);
                const d = await r.json();
                if (gen !== meaningGen) return;
                if (!d.fallback) meaningCache.set(key, d);   // a fallback is never kept in place of real results
                this._srchMeaningShow(key, d);
            } catch {
                if (gen !== meaningGen) return;
                Object.assign(this.srch.meaning, { status: online(this) ? 'error' : 'offline', items: [] });
                this._srchAnnounce();
            }
            if (window.history.state?.srch) this._srchSaveState();
        },
        _srchMeaningShow(key, d) {
            Object.assign(this.srch.meaning, {
                status: 'ready', q: key, fallback: !!d.fallback, reveal: false,
                items: (d.results || []).filter(r => r.type === 'verse').map(r => ({ ...r, translation: d.translation })),
            });
            this._srchAnnounce();
        },

        async _srchStatus() {
            this.srch.semantic = { available: true };   // assume yes until told otherwise
            try {
                const r = await fetch('/api/semantic/status');
                if (r.ok) this.srch.semantic = await r.json();
            } catch { /* offline: handled per request */ }
        },

        // ---------- Nave's topic with exactly this name ----------
        async srchTopic() {
            const q = this.srch.q.trim();
            this.srch.topic = null;
            if (this.srchKind() !== 'words' || !this.currentBook || !online(this) || this.srch.scope === 'commentary') return;
            try {
                const r = await fetch(`/api/topics/search?q=${encodeURIComponent(q)}&limit=1`);
                if (!r.ok) return;
                const d = await r.json();
                const t = (d.results || []).find(x => x.exact);
                if (t && this.srch.q.trim() === q) this.srch.topic = { id: t.id, name: t.topic.charAt(0) + t.topic.slice(1).toLowerCase(), count: (t.refs || []).length };
            } catch { /* topics are an extra */ }
        },
        srchOpenTopic() {
            const t = this.srch.topic;
            if (!t) return;
            this._srchSaveState();
            this.srchHide();             // the entry stays: Back comes back to the results
            this.openSheet('topics');
            this.viewTopic(t.id);
        },

        // ---------- the two lists, each verse once ----------
        // Which list leads: the idea for questions (and when no verse has the words),
        // the words for a word or two.
        srchMeaningFirst() {
            if (this.srchKind() === 'question') return true;
            return this.srch.kw.status === 'ready' && this.srch.kw.q === this._srchKey() && !this.srch.kw.verses.length;
        },
        srchOrder() { return this.srchMeaningFirst() ? ['meaning', 'kw'] : ['kw', 'meaning']; },
        srchMeaningShown() {
            return this.srchWantsMeaning() && this.srch.meaning.status !== 'idle' && this.srch.meaning.q === this._srchKey();
        },
        srchKwVerses() {
            if (this.srch.kw.q !== this._srchKey()) return [];
            const kw = this.srch.kw.verses;
            if (!this.srchMeaningFirst() || !this.srchMeaningShown()) return kw;
            const seen = new Set(this.srchMeaningAll().map(keyOf));
            return kw.filter(h => !seen.has(keyOf(h)));
        },
        // Every meaning result, before trimming against the keyword list
        srchMeaningAll() {
            if (!this.srchMeaningShown() || this.srch.meaning.status !== 'ready') return [];
            if (this.srchMeaningGuessOnly() && !this.srch.meaning.reveal) return [];
            return this.srch.meaning.items;
        },
        srchMeaningItems() {
            const all = this.srchMeaningAll();
            if (this.srchMeaningFirst()) return all;
            const seen = new Set(this.srch.kw.verses.map(keyOf));
            return all.filter(h => !seen.has(keyOf(h)));
        },
        // None of the reader's words occur in Scripture (a typo, nonsense): what comes back is
        // the nearest verses to nothing in particular. Say so instead of listing them.
        srchMeaningGuessOnly() {
            const m = this.srch.meaning;
            return m.status === 'ready' && !m.fallback && m.items.length > 0 && !m.items.some(r => r.match !== 'meaning')
                && !(this.srch.kw.q === this._srchKey() && this.srch.kw.verses.length);
        },
        srchShown(list, name) {
            return this.srch.all[name] ? list : list.slice(0, name === 'commentary' ? COMMENTARY_FIRST : FIRST);
        },
        srchShowAll(name) {
            this.srch.all[name] = true;
            // Keep the reader's place: focus the first newly shown result
            const n = name === 'commentary' ? COMMENTARY_FIRST : FIRST;
            this.$nextTick(() => document.querySelectorAll(`#search-view [data-list="${name}"] [data-srch-nav]`)[n]?.focus({ preventScroll: false }));
        },
        srchHeading(list) {
            const k = this.srchKind();
            if (list === 'kw') {
                if (this.srch.kw.word) return 'Verses with this word';
                return k === 'phrase' ? 'Verses with this exact phrase' : 'Verses with your words';
            }
            if (this.srch.meaning.fallback) return 'Verses with some of your words';
            return !this.srchMeaningFirst() && this.srch.kw.verses.length ? 'More verses that may be about this idea' : 'Verses that may be about this idea';
        },
        srchNothing() {
            const kwDone = this.srch.kw.status === 'ready' && this.srch.kw.q === this._srchKey();
            if (!kwDone || this.srch.kw.verses.length || this.srch.kw.commentary.length || this.srch.kw.word || this.srch.kw.suggestions.length || this.srch.topic) return false;
            if (!this.srchWantsMeaning()) return true;
            const m = this.srch.meaning;
            return m.q === this._srchKey() && m.status === 'ready' && (!m.items.length || (this.srchMeaningGuessOnly() && !m.reveal));
        },
        srchLoading() {
            return this.srch.kw.status === 'loading' || this.srch.meaning.status === 'loading';
        },

        // A screen reader hears one short sentence when something arrives
        _srchAnnounce() {
            const parts = [];
            const kw = this.srch.kw;
            const kind = this.srchKind();
            if (kind === 'reference') parts.push(`Press Enter to go to ${this.srchRefLabel()}.`);
            if (kw.word) parts.push(`${kw.word.transliteration || kw.word.strong_number}, ${kw.word.strong_number}. Press Enter for its word study.`);
            if (kw.status === 'ready' && kw.q === this._srchKey() && kind !== 'reference') {
                const n = kw.verses.length;
                const what = kw.word ? 'this word' : 'your words';
                parts.push(n ? `${n} verse${n === 1 ? '' : 's'} with ${what}.` : 'No verse has these words.');
                if (kw.commentary.length) parts.push(`${kw.commentary.length} commentary results.`);
            }
            const m = this.srch.meaning;
            if (this.srchMeaningShown()) {
                if (m.status === 'loading') parts.push('Looking for verses about this idea.');
                else if (m.status === 'ready' && m.fallback) parts.push(`Search by meaning is unavailable; ${m.items.length} verses with some of your words.`);
                else if (m.status === 'ready' && this.srchMeaningGuessOnly()) parts.push('None of these words are in the Bible text.');
                else if (m.status === 'ready') parts.push(`${this.srchMeaningItems().length} verses that may be about this idea.`);
                else if (m.status === 'offline') parts.push('Search by meaning needs a connection.');
                else if (m.status === 'limited') parts.push('Too many searches in a minute. Try again shortly.');
            }
            this.srch.announce = parts.join(' ');
        },

        // ---------- going somewhere ----------
        srchGo(hit) {
            this.srch.lastHit = keyOf(hit);
            this._srchSaveState();
            this.navigate(refOf(hit), { kind: 'jump', fromSearch: true });
        },
        srchGoRef() {
            const ref = this.srchRefLabel();
            if (!ref) return;
            this._srchSaveState();
            this.navigate(ref, { kind: 'jump', fromSearch: true });
        },
        srchGoCommentary(hit) {
            this.srch.lastHit = `c|${hit.book}|${hit.chapter}|${hit.source}`;
            this._srchSaveState();
            this.srchHide();             // the entry stays: Back from the study view returns here
            this.openStudy(`${hit.book} ${hit.chapter}`, { source: hit.source });
        },
        srchWordStudy(strong) {
            this._srchSaveState();
            this.srchHide();
            this.openWordStudy(strong);
        },

        // ---------- keyboard: arrows move through everything that can be opened ----------
        srchKeydown(e) {
            const items = [...document.querySelectorAll('#search-view [data-srch-nav]')].filter(el => el.offsetParent);
            const input = document.getElementById('srch-input');
            const i = items.indexOf(document.activeElement);
            if (e.key === 'ArrowDown') {
                if (e.target === input || i >= 0) {
                    e.preventDefault();
                    const next = items[i + 1];
                    if (next) { next.focus({ preventScroll: true }); next.scrollIntoView({ block: 'nearest' }); }
                }
            } else if (e.key === 'ArrowUp' && i >= 0) {
                e.preventDefault();
                const prev = items[i - 1];
                if (prev) { prev.focus({ preventScroll: true }); prev.scrollIntoView({ block: 'nearest' }); }
                else input?.focus();
            } else if (i >= 0 && e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey && e.key !== ' ') {
                input?.focus();   // typing on a result goes back to the field
            }
        },

        srchScopes() {
            const out = [{ id: 'all', label: 'All', name: 'The whole Bible and commentary' },
                { id: 'ot', label: 'OT', name: 'Old Testament' }, { id: 'nt', label: 'NT', name: 'New Testament' }];
            if (this.currentBook) out.push({ id: `book:${this.currentBook}`, label: this.currentBook, name: `Only ${this.currentBook}` });
            out.push({ id: 'commentary', label: 'Commentary', name: 'Commentary only' });
            return out;
        },
        srchExamples() { return EXAMPLES; },
        srchHitRef(h) { return `${h.book} ${h.chapter}:${h.verse}`; },
        srchHitKey(h) { return keyOf(h); },
    };
})();
