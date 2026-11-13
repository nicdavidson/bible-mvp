// bibleApp feature module: wordstudy — a Hebrew/Greek word, from a tap to a full study.
// Merged via Object.assign in app.js. Markup: the word panel (.panel-word) and
// <dialog id="word-study"> in index.html; styles in css/wordstudy.css.
//
// Two steps, so a glance stays a glance:
//   the word panel   tap a word: the word, one lexicon gloss (named), how often it occurs,
//                    and "Study this word". Works offline from the saved Strong's lexicon.
//   the word study   /word/G26: GET /api/word/{strong}/study (docs/WORD_STUDY_2026-11.md).
//                    Lexicon entries first (quoted, each credited), then what the data
//                    counts (renderings, where it occurs, forms), then what is computed
//                    (words it travels with, cross-references, Nave's topics), labelled so.
//                    Every count that stands for verses opens them (/verses, /renderings).
//
// History: the study and its verse lists are entries of their own (/word/G26,
// /word/G26?list=with:G4102), pushed through navPushState() so Back and the return chip
// (modules/nav.js) agree. Leaving for a verse is navigate(ref, { kind: 'jump' }).
window.BibleModules = window.BibleModules || {};
(() => {
    const STRONG_RE = /^([HGhg])0*(\d{1,5})([A-Za-z])?$/;
    const LEX_NAME = { 'abbott-smith': 'Abbott-Smith', dodson: 'Dodson', strongs: "Strong's", bdb: 'Brown–Driver–Briggs' };
    const RELATION = { derived_from: 'comes from', source_of: 'is the root of', compare: 'compare', same_root: 'same root' };
    const SECTIONS = {
        OT: [['Law', 'Genesis', 'Deuteronomy'], ['History', 'Joshua', 'Esther'], ['Wisdom', 'Job', 'Song of Solomon'],
            ['Prophets', 'Isaiah', 'Daniel'], ['Minor Prophets', 'Hosea', 'Malachi']],
        NT: [['Gospels', 'Matthew', 'John'], ['Acts', 'Acts', 'Acts'], ['Paul', 'Romans', 'Philemon'],
            ['Letters', 'Hebrews', 'Jude'], ['Revelation', 'Revelation', 'Revelation']],
    };
    const payloads = new Map();   // "G26|homograph" -> study payload (this session)
    const reduceMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // "g0026" -> "G26"; null if it isn't a Strong's number
    function plainStrong(s) {
        const m = String(s || '').trim().match(STRONG_RE);
        return m ? `${m[1].toUpperCase()}${parseInt(m[2], 10)}` : null;
    }

    // Lists live in the URL: ?list=all | book:Romans | form:N-NS | with:G4102 | edition:TR
    // | rendering:KJV:charity
    function parseList(q) {
        if (!q) return null;
        const [kind, ...rest] = q.split(':');
        if (kind === 'all') return { kind };
        if (kind === 'rendering' && rest.length >= 2) return { kind, tr: rest[0], value: rest.slice(1).join(':') };
        if (['book', 'form', 'with', 'edition', 'topic'].includes(kind) && rest.length) return { kind, value: rest.join(':') };
        return null;
    }
    const listParam = (l) => l.kind === 'all' ? 'all' : l.kind === 'rendering' ? `rendering:${l.tr}:${l.value}` : `${l.kind}:${l.value}`;

    // Wrap the tappable words at `positions` (formatVerseText numbering) in <mark>
    function markWords(html, positions) {
        if (!positions?.length) return html;
        const want = new Set(positions);
        return html.replace(/<span class="word" data-word="([^"]*)" data-position="(\d+)">([^<]*)<\/span>/g,
            (all, w, p, t) => want.has(+p) ? `<mark class="ws-hit">${t}</mark>` : t)
            .replace(/<span class="word" data-word="[^"]*" data-position="\d+">([^<]*)<\/span>/g, '$1')
            .replace(/<\/mark>(\s*)<mark class="ws-hit">/g, '$1');
    }

    window.BibleWordStudy = { plainStrong, parseList, markWords };

    window.BibleModules.wordstudy = {
        ws: {
            open: false, loading: false, error: null, offline: false, offlineEntry: null,
            strong: null, homograph: null, data: null,
            from: null,          // { text, ref, unsure }: the tapped word that led here
            lexMore: {},         // lexicon entries shown in full
            book: null,          // the book picked on the chart
            moreRenderings: {},  // translation -> all listed renderings shown
            moreSamples: false,
            list: null,          // { kind, ..., title, items, total, verses, loading, error, next }
            peek: null,          // { ref, verses, focus, loading, error }
        },
        _wsDepth: 0,
        _wsOpener: null,
        _wsGen: 0,

        // ---------- the word panel (quick look) ----------
        // Fill in a word panel's lexicon gloss and count from the study payload (fetched
        // once; the same request opens the full study instantly and is kept by the
        // service worker for offline). occ: { ref: {book, chapter, verse}, pos } of the tap.
        async wsQuick(strong, occ = null) {
            const plain = plainStrong(strong);
            const w = this.selectedWord;
            if (!plain || !w) return;
            w.quick = { status: 'loading' };
            let data = null;
            try { data = await this.wsFetch(plain, null); } catch (err) {
                if (this.selectedWord === w) w.quick = { status: err.offline || !navigator.onLine ? 'offline' : 'error' };
                return;
            }
            if (this.selectedWord !== w) return;
            const lex = data.lexicons?.[0];
            const entry = lex?.entries?.[0];
            const occs = data.occurrences || {};
            const quick = {
                status: 'ready', strong: plain, homograph: null, pos: data.lemma?.pos?.label || '',
                gloss: entry?.gloss || null, glossSource: entry?.gloss ? LEX_NAME[lex.source] || lex.source : null,
                total: occs.total ?? null, testament: data.language === 'hebrew' ? 'Old Testament' : 'New Testament',
                transliteration: data.lemma?.transliteration || '',
            };
            // A number that covers two words: say which one this is, only when it is the rarer one
            const others = (occs.homographs || []).filter(h => !h.selected);
            if (others.length && occ?.ref && occ.pos) {
                for (const h of others) {
                    try {
                        const r = await this.studyFetch(`/api/word/${plain}/verses?homograph=${encodeURIComponent(h.ext)}&book=${encodeURIComponent(occ.ref.book)}`);
                        if (r.occurrences.some(o => o.chapter === occ.ref.chapter && o.verse === occ.ref.verse && o.word_position === occ.pos)) {
                            const bdb = (data.lexicons || []).find(l => l.source === 'bdb')?.entries.find(e => e.homograph === h.ext);
                            Object.assign(quick, { homograph: h.ext, gloss: bdb?.gloss || h.gloss, glossSource: bdb ? LEX_NAME.bdb : 'STEPBible',
                                total: h.occurrences, homographNote: `Strong's ${plain} also covers a more common word, “${occs.homographs.find(x => x.selected)?.gloss}”. This is the rarer one.` });
                            break;
                        }
                    } catch { /* keep the default */ }
                }
            }
            if (this.selectedWord === w) w.quick = quick;
        },

        // ---------- open / close / history ----------
        // history: 'push' (the reader asked), 'replace' (deep link, switching homograph), 'none' (popstate)
        // from: { text, ref, unsure } when a tapped word led here (kept through Back)
        async openWordStudy(strong, { homograph = null, history = 'push', from = null, list = null } = {}) {
            const plain = plainStrong(strong);
            const dlg = document.getElementById('word-study');
            if (!dlg) return;
            const wasOpen = this.ws.open;
            if (!wasOpen) {
                this._wsOpener = document.activeElement;
                if (this.ttsPlaying) this.ttsStop();
            }
            this.selectedWord = null;
            const same = wasOpen && this.ws.strong === plain && this.ws.homograph === homograph && this.ws.data;
            Object.assign(this.ws, {
                open: true, strong: plain, homograph, peek: null,
                ...(same ? {} : { data: null, error: null, offline: false, offlineEntry: null, lexMore: {}, book: null, moreRenderings: {}, moreSamples: false }),
            });
            if (history === 'push') this.ws.from = from;
            if (!dlg.open) {
                dlg.showModal();
                document.documentElement.classList.add('word-study-open');
            }
            // A verse opened from here comes back here (the chip), not to an older place
            if (history === 'push') this.navReturn = null;
            const url = this.wsURL(list);
            const state = { nav: 1, word: plain, homograph, list: list ? listParam(list) : null, ret: this.navReturn, wsFrom: this.ws.from };
            if (history === 'push') {
                this._wsDepth += 1;
                this.navPushState({ ...state, wsDepth: this._wsDepth }, url);
            } else if (history === 'replace') {
                this.navReplaceState({ ...state, wsDepth: this._wsDepth }, url);
            }
            if (list) this.wsShowList(list); else this.ws.list = null;
            if (!same) await this.wsLoad();
            this.$nextTick(() => {
                if (this.ws.list) document.getElementById('ws-list-title')?.focus({ preventScroll: true });
                else if (!wasOpen || !same) {
                    document.getElementById('ws-title')?.focus({ preventScroll: true });
                    const sc = document.querySelector('#word-study .ws-scroll');
                    if (sc && !same) sc.scrollTop = 0;
                }
            });
        },

        wsURL(list = this.ws.list) {
            const q = new URLSearchParams();
            if (this.ws.homograph) q.set('homograph', this.ws.homograph);
            if (list) q.set('list', listParam(list));
            const s = q.toString();
            return `/word/${this.ws.strong}${s ? '?' + s : ''}`;
        },

        // Close the study: back through its own entries to where it was opened
        wsClose() {
            if (!this.ws.open) return;
            if (this._wsDepth > 0) { window.history.go(-this._wsDepth); return; }
            this.wsHide();
            if (this.currentBook || this.combinedPlanReading) this.updateURL();
            else this.navReplaceState({ nav: 1, home: true, ret: null }, '/');
        },
        // One step back: a peek, a verse list, an earlier word, or out
        wsBack() {
            if (this.ws.peek) { this.wsClosePeek(); return; }
            if (this._wsDepth > 0) window.history.back();
            else if (this.ws.list) { this.ws.list = null; this.navReplaceState({ ...history.state, list: null }, this.wsURL(null)); }
            else this.wsClose();
        },
        wsHide() {
            const dlg = document.getElementById('word-study');
            this.ws.open = false;
            this.ws.peek = null;
            this.ws.list = null;
            this._wsDepth = 0;
            this._wsGen++;
            dlg?.querySelectorAll('dialog[open]').forEach(d => d.close());
            if (dlg?.open) dlg.close();
            document.documentElement.classList.remove('word-study-open');
            const opener = this._wsOpener;
            this._wsOpener = null;
            if (opener && document.contains(opener)) opener.focus({ preventScroll: true });
        },

        // From the app's popstate handler (modules/nav.js), first. True when it showed
        // a word study entry; false otherwise (closing the study if it was open).
        wsHandlePop(e) {
            const st = e?.state;
            const m = window.location.pathname.match(/^\/word\/([^/]+)$/);
            if (m) {
                this._wsDepth = st?.wsDepth || 0;
                const q = new URLSearchParams(window.location.search);
                if (st?.wsFrom) this.ws.from = st.wsFrom;
                this.navReturn = st?.ret || null;
                this.openWordStudy(decodeURIComponent(m[1]), { homograph: q.get('homograph'), history: 'none', list: parseList(q.get('list')) });
                return true;
            }
            if (this.ws.open) this.wsHide();
            return false;
        },

        // Deep link (/word/G26): the reader underneath is Home
        async wsInitFromURL() {
            const m = window.location.pathname.match(/^\/word\/([^/]+)$/);
            if (!m) return false;
            const q = new URLSearchParams(window.location.search);
            const st = history.state;
            await this.navigate({ home: true }, { source: 'init' });
            this._wsDepth = st?.word ? (st.wsDepth || 0) : 0;
            if (st?.wsFrom) this.ws.from = st.wsFrom;
            this.navReturn = st?.ret || null;
            const strong = decodeURIComponent(m[1]);
            this.navReplaceState({ ...(st || {}), nav: 1, home: true, word: plainStrong(strong) || strong }, location.pathname + location.search);
            this.openWordStudy(strong, { homograph: q.get('homograph'), history: 'none', list: parseList(q.get('list')) });
            return true;
        },

        // ---------- data ----------
        async wsFetch(plain, homograph) {
            const key = `${plain}|${homograph || ''}`;
            if (payloads.has(key)) return payloads.get(key);
            const data = await this.studyFetch(`/api/word/${plain}/study${homograph ? '?homograph=' + encodeURIComponent(homograph) : ''}`);
            payloads.set(key, data);
            if (payloads.size > 40) payloads.delete(payloads.keys().next().value);
            return data;
        },

        async wsLoad() {
            const { strong, homograph } = this.ws;
            const gen = ++this._wsGen;
            if (!strong) { this.ws.error = "That isn't a Strong's number. They look like G26 (Greek) or H2617 (Hebrew)."; return; }
            this.ws.loading = true;
            try {
                const data = await this.wsFetch(strong, homograph);
                if (gen !== this._wsGen) return;
                this.ws.data = data;
                this.ws.error = null;
                this.ws.offline = false;
            } catch (err) {
                if (gen !== this._wsGen) return;
                if (err.status === 404) this.ws.error = `There is no word ${strong} in the Hebrew or Greek text.`;
                else if (err.status === 400) this.ws.error = `${strong} isn't a word in these lexicons.`;
                else if (err.offline || !navigator.onLine || err instanceof TypeError) {
                    this.ws.offline = true;
                    this.ws.offlineEntry = await window.offlineStorage?.getLexiconEntry(strong).catch(() => null) || null;
                } else this.ws.error = `Couldn't load the study of ${strong}. Try again.`;
            } finally {
                if (gen === this._wsGen) this.ws.loading = false;
            }
        },
        wsRetry() {
            payloads.delete(`${this.ws.strong}|${this.ws.homograph || ''}`);
            this.ws.error = null;
            this.ws.offline = false;
            this.wsLoad();
        },

        // ---------- what the screen shows ----------
        wsLemma() { return this.ws.data?.lemma || {}; },
        wsLang() { return this.ws.data?.language || (this.ws.strong?.[0] === 'H' ? 'hebrew' : 'greek'); },
        wsLangAttr() { return this.wsLang() === 'hebrew' ? 'he' : 'grc'; },
        wsTestament() { return this.wsLang() === 'hebrew' ? 'Old Testament' : 'New Testament'; },
        wsTitle() { return this.wsLemma().original || this.ws.offlineEntry?.original || this.ws.strong || ''; },
        wsSource(key) { return this.ws.data?.sources?.[key] || null; },
        wsSourceName(key) { return LEX_NAME[key] || this.wsSource(key)?.name || key; },
        wsCredit(key) {
            const s = this.wsSource(key);
            if (!s) return '';
            return [s.name, s.license, s.attribution ? `Credit: ${s.attribution}` : ''].filter(Boolean).join('. ');
        },
        // The one-line answer to "what is this word": the briefest lexicon gloss, named
        wsGlance() {
            const sel = this.wsOcc().homograph;
            const order = this.wsLang() === 'hebrew' ? ['bdb', 'strongs'] : ['abbott-smith', 'dodson', 'strongs'];   // as the word panel
            for (const key of order) {
                const l = (this.ws.data?.lexicons || []).find(x => x.source === key);
                const e = l && ((sel && l.entries.find(x => x.homograph === sel)) || l.entries[0]);
                const g = e?.gloss || (key === 'strongs' ? (e?.definition || '').trim().split(/[;,]/)[0] : '');
                if (g) return { gloss: g, source: LEX_NAME[key] };
            }
            return null;
        },
        wsKindLine() {
            const l = this.wsLemma();
            const lang = this.wsLang() === 'hebrew' ? 'Hebrew' : 'Greek';
            return `${lang}${l.pos?.label ? ' ' + l.pos.label : ''}, Strong's ${this.ws.strong}`;
        },
        wsOcc() { return this.ws.data?.occurrences || {}; },
        wsCountLine() {
            const o = this.wsOcc();
            if (!o.total) return '';
            const t = o.total === 1 ? 'Once' : `${o.total.toLocaleString()} times`;
            const v = o.total === 1 ? '' : o.verses === o.total ? '' : ` in ${o.verses.toLocaleString()} verses`;
            return `${t}${v} in the ${this.wsTestament()}`;
        },
        wsHomographs() { return (this.wsOcc().homographs || []).length > 1 ? this.wsOcc().homographs : []; },
        wsHomographLabel(h) {
            const e = (this.ws.data?.lexicons || []).find(l => l.source === 'bdb')?.entries.find(x => x.homograph === h.ext);
            return { name: `${this.wsLemma().transliteration || ''} ${e?.meta?.homograph || h.ext.slice(-1)}`.trim(), gloss: e?.gloss || h.gloss, count: h.occurrences };
        },
        wsPickHomograph(h) {
            if (h.selected) return;
            this.openWordStudy(this.ws.strong, { homograph: h.ext, history: 'replace' });
        },

        // Lexicons: the fullest first; BDB lists one entry per homograph, the selected first
        wsLexicons() {
            const sel = this.wsOcc().homograph;
            return (this.ws.data?.lexicons || []).map(l => {
                let entries = l.entries || [];
                if (l.source === 'bdb' && sel) entries = [...entries].sort((a, b) => (b.homograph === sel) - (a.homograph === sel));
                return { ...l, entries, name: this.wsSourceName(l.source) };
            }).filter(l => l.entries.length);
        },
        wsLexLong(l, e) { return (e.definition || '').length > 420 || (e.definition || '').split('\n').length > 7; },
        wsLexKey(l, i) { return `${l.source}-${i}`; },
        wsLexNote(e) {
            if (e.meta?.status === 'base') return 'This edition of BDB gives the outline of senses only, without its references.';
            return '';
        },
        wsPlainSense(text) { return String(text || '').trim(); },
        // "from G25 (ἀγαπάω);" -> segments, numbers as links to their own study
        wsLinkify(text) {
            return String(text || '').split(/\b([HG]\d{1,5})\b/).map((t, i) => ({ t, strong: i % 2 ? t : null }));
        },

        // Renderings: the reader's translation first
        wsTranslations() {
            const tr = this.ws.data?.renderings?.translations || {};
            const order = [this.translation, ...['BSB', 'KJV', 'WEB'].filter(t => t !== this.translation)];
            return order.filter(t => tr[t]?.total).map(t => {
                const x = tr[t];
                const max = Math.max(1, ...x.renderings.map(r => r.count));
                const all = x.renderings.map(r => ({ ...r, share: r.count / x.total, width: Math.max(2, Math.round(r.count / max * 100)) }));
                const showAll = this.ws.moreRenderings[t];
                return { tr: t, total: x.total, rows: showAll ? all : all.slice(0, 4), hidden: showAll ? 0 : Math.max(0, all.length - 4), other: x.other };
            });
        },
        wsHasPhrases() {
            return this.wsTranslations().some(t => t.rows.some(r => r.rendering.split(' ').length >= 3));
        },

        // Where it occurs: every book of its testament, grouped by part of the Bible
        wsSections() {
            const o = this.wsOcc();
            const counts = new Map((o.by_book || []).map(b => [b.book, b.count]));
            const t = this.wsLang() === 'hebrew' ? 'OT' : 'NT';
            const books = t === 'OT' ? OT_BOOKS : NT_BOOKS;
            const max = Math.max(1, ...counts.values());
            return SECTIONS[t].map(([name, a, b]) => {
                const list = books.slice(books.indexOf(a), books.indexOf(b) + 1)
                    .map(book => ({ book, count: counts.get(book) || 0, h: Math.round((counts.get(book) || 0) / max * 100) }));
                return { name, books: list, total: list.reduce((n, x) => n + x.count, 0) };
            });
        },
        wsTopBooks(n = 3) {
            return [...(this.wsOcc().by_book || [])].sort((a, b) => b.count - a.count).slice(0, n);
        },
        wsBooksWithCount() { return this.wsOcc().by_book || []; },
        wsPickBook(b) {
            this.ws.book = this.ws.book?.book === b.book ? null : b;
        },
        wsChartSummary() {
            const top = this.wsTopBooks(3);
            const s = this.wsSections().filter(x => x.total);
            if (!top.length) return '';
            const parts = s.map(x => `${x.name} ${x.total}`).join(', ');
            return `By part of the ${this.wsTestament()}: ${parts}. Most in ${top.map(b => `${b.book} (${b.count})`).join(', ')}.`;
        },

        wsEditions() {
            const e = this.wsOcc().by_edition;
            if (!e) return null;
            const vals = Object.values(e);
            return vals.every(v => v === vals[0]) ? null : e;
        },

        // The first few, then the rest on request (the list is up to 12 long)
        wsSamplesShown() { return this.ws.moreSamples ? this.wsSamples() : this.wsSamples().slice(0, 5); },
        wsSamples() {
            return (this.ws.data?.samples?.items || []).map(s => ({
                ...s, ref: `${s.book} ${s.chapter}:${s.verse}`,
                html: s.bsb_text ? markWords(this.formatVerseText(s.bsb_text), s.bsb_word_positions) : '',
            }));
        },
        wsCollocates() { return this.ws.data?.collocates?.items || []; },
        wsGlossSources(items) {
            return [...new Set(items.map(i => i.gloss_source).filter(Boolean))].map(k => this.wsSourceName(k)).join(', ');
        },
        wsRelated() { return this.ws.data?.related?.items || []; },
        wsRelationLabel(link) {
            const r = RELATION[link.relation] || link.relation;
            return `${r}${link.detail && link.relation === 'same_root' ? ' ' + link.detail : ''} (${this.wsSourceName(link.source)})`;
        },
        wsXrefs() {
            return (this.ws.data?.cross_references?.items || []).map(x => ({
                ...x, a: `${x.from.book} ${x.from.chapter}:${x.from.verse}`, b: `${x.to.book} ${x.to.chapter}:${x.to.verse}`,
            }));
        },
        wsTopics() { return this.ws.data?.topics?.items || []; },
        wsTopicName(t) { return String(t.topic || '').toLowerCase().replace(/(^|[\s-])\S/g, c => c.toUpperCase()); },
        // Credits for the sections on screen
        wsSourcesShown() {
            const d = this.ws.data;
            if (!d) return [];
            const keys = new Set(this.wsLexicons().map(l => l.source));
            ['occurrences', 'renderings', 'collocates', 'topics', 'cross_references', 'samples'].forEach(k => {
                const sec = d[k];
                const has = k === 'occurrences' ? sec?.total : k === 'renderings' ? Object.keys(sec?.translations || {}).length : sec?.items?.length;
                if (sec?.source && has) keys.add(sec.source);
            });
            (d.related?.items || []).forEach(r => r.links.forEach(l => keys.add(l.source)));
            return [...keys].filter(k => d.sources?.[k]).map(k => ({ key: k, ...d.sources[k] }));
        },

        // ---------- verse lists ----------
        wsOpenList(list) {
            this._wsDepth += 1;
            this.navPushState({ nav: 1, word: this.ws.strong, homograph: this.ws.homograph, list: listParam(list), ret: this.navReturn, wsFrom: this.ws.from, wsDepth: this._wsDepth }, this.wsURL(list));
            this.wsShowList(list);
            this.$nextTick(() => document.getElementById('ws-list-title')?.focus({ preventScroll: true }));
        },
        wsListTitle(l) {
            const w = this.wsLemma().transliteration || this.ws.strong;
            switch (l.kind) {
                case 'all': return `Every verse with ${w}`;
                case 'book': return `${w} in ${l.value}`;
                case 'form': return `${w}: ${(this.wsOcc().by_form || []).find(f => f.form === l.value)?.label || l.value}`;
                case 'edition': return `${w} in the ${{ TR: 'Textus Receptus', Byz: 'Byzantine text', SBL: 'SBL Greek NT' }[l.value] || l.value}`;
                case 'with': {
                    const c = this.wsCollocates().find(x => x.strong_number === l.value);
                    return `${w} with ${c?.transliteration || l.value}${c?.gloss ? ' (' + c.gloss.split(',')[0] + ')' : ''}`;
                }
                case 'rendering': return `${l.tr}: “${l.value}”`;
                case 'topic': {
                    const t = this.wsTopics().find(x => String(x.topic_id) === String(l.value));
                    return `${w} in Nave's topic ${t ? this.wsTopicName(t) : l.value}`;
                }
                default: return w;
            }
        },
        async wsShowList(list, more = false) {
            if (!more) this.ws.list = { ...list, items: [], total: null, verses: null, loading: true, error: null, next: 0 };
            const l = this.ws.list;   // the reactive copy: compared below to tell if it is still shown
            l.loading = true;
            l.error = null;
            const strong = this.ws.strong;
            const tr = l.kind === 'rendering' ? l.tr : this.translation;
            let url;
            if (l.kind === 'rendering') {
                url = `/api/word/${strong}/renderings?translation=${encodeURIComponent(l.tr)}&rendering=${encodeURIComponent(l.value)}&offset=${l.next}`;
            } else {
                const q = new URLSearchParams({ translation: tr, offset: String(l.next) });
                // Collocates and topics are computed over the whole Strong's number
                if (this.ws.homograph && !['with', 'topic'].includes(l.kind)) q.set('homograph', this.ws.homograph);
                if (l.kind !== 'all') q.set(l.kind, l.value);
                url = `/api/word/${strong}/verses?${q}`;
            }
            try {
                const d = await this.studyFetch(url);
                if (this.ws.list !== l) return;
                const rows = d.occurrences || [];
                const byVerse = new Map(l.items.map(it => [it.ref, it]));
                for (const r of rows) {
                    const ref = `${r.book} ${r.chapter}:${r.verse}`;
                    const pos = r.english_word_positions || r.word_positions || [];
                    if (byVerse.has(ref)) { byVerse.get(ref).positions.push(...pos); continue; }
                    const it = { ref, book: r.book, chapter: r.chapter, verse: r.verse, text: r.text || '', positions: [...pos], original: r.original_text || null };
                    byVerse.set(ref, it);
                    l.items.push(it);
                }
                for (const it of l.items) it.html = it.text ? markWords(this.formatVerseText(it.text), it.positions) : '';
                l.translation = tr;
                l.total = d.total;
                l.verses = l.kind === 'rendering' ? d.total : (d.verses ?? null);
                const page = l.kind === 'rendering' ? 200 : 100;
                l.next = (d.offset || 0) + page;
                l.more = l.next < d.total;
            } catch (err) {
                if (this.ws.list !== l) return;
                l.error = err.offline || !navigator.onLine ? 'These verses need a connection. Try again when you are back online.' : "Couldn't load these verses. Try again.";
            } finally {
                if (this.ws.list === l) l.loading = false;
            }
        },
        wsListCountLine(l) {
            if (l.total == null) return '';
            if (l.kind === 'rendering') return `${l.total} ${l.total === 1 ? 'place' : 'places'} where the ${l.tr} renders ${this.wsLemma().transliteration || this.ws.strong} this way`;
            const t = `${l.total} ${l.total === 1 ? 'time' : 'times'}`;
            return l.verses && l.verses !== l.total ? `${t} in ${l.verses} verses` : t;
        },

        // ---------- a verse, in its place ----------
        async wsPeek(ref) {
            const p = BibleRef.parse(ref);
            if (p.error || !p.vs) return;
            const token = Symbol('peek');
            this.ws.peek = { ref, token, verses: [], focus: [p.vs, p.ve], loading: true, error: null };
            this.$nextTick(() => document.getElementById('ws-peek')?.showModal());
            const ask = `${p.book} ${p.chapter}:${Math.max(1, p.vs - 1)}-${p.ve + 1}`;
            let verses = null;
            try {
                verses = (await this.studyFetch(`/api/passage/${encodeURIComponent(ask)}/study?translation=${encodeURIComponent(this.translation)}`)).verses;
            } catch {
                const cached = await window.offlineStorage?.getChapterVerses(this.translation, p.book, p.chapter).catch(() => null);
                if (cached?.length) verses = cached.filter(v => v.verse >= p.vs - 1 && v.verse <= p.ve + 1);
            }
            if (this.ws.peek?.token !== token) return;
            this.ws.peek.loading = false;
            if (verses?.length) this.ws.peek.verses = verses;
            else this.ws.peek.error = navigator.onLine ? `Couldn't load ${ref}.` : `${ref} isn't saved for offline use.`;
        },
        wsClosePeek() {
            document.getElementById('ws-peek')?.close();
            this.ws.peek = null;
        },
        // Leave for the reader: the return chip and Back come back to this study
        wsPeekRead() {
            const ref = this.ws.peek?.ref;
            this.wsClosePeek();
            if (ref) this.navigate(ref, { kind: 'jump' });
        },
        async wsPeekStudy() {
            const ref = this.ws.peek?.ref;
            this.wsClosePeek();
            if (ref && await this.navigate(ref, { kind: 'jump' })) this.openStudy(ref);
        },

        // From a lexicon line, a related word, a collocate: another word's study
        wsGoWord(strong) {
            const plain = plainStrong(strong);
            if (!plain || plain === this.ws.strong) return;
            this.openWordStudy(plain, { history: 'push', from: null });
        },
        wsScrollTo(id) {
            document.getElementById(id)?.scrollIntoView({ block: 'start', behavior: reduceMotion() ? 'auto' : 'smooth' });
        },
    };
})();
