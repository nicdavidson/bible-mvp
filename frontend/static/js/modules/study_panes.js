// bibleApp feature module: study_panes — the study view's non-commentary panes.
// Merged via Object.assign in app.js. Markup: the last two .study-pane sections and the
// .study-tools buttons in <dialog id="study-view"> (index.html); styles in css/study.css.
//
//   cross-references  The selection's cross-references (OpenBible.info, from the Treasury
//                     of Scripture Knowledge) with each verse's text inline. Ranked by
//                     readers' votes: the first screen shows the strongest few per verse,
//                     "Show all" one tap away (John 3:16 has 40, Psalm 23 has 140).
//   notes             The reader's own note on exactly this selection, written and edited
//                     in place, plus notes on overlapping verses, labelled with their verses.
//                     Stored through noteCreate()/noteUpdateContent() (modules/feedback.js):
//                     same format, same keys (book, chapter, startVerse, endVerse).
//   hymns             Hymns linked to the selection, then to the rest of its chapter
//                     (modules/hymns.js). Only on the track when there are some.
//
// Under the cross-references, apart and labelled as computed: "Similar verses"
// (GET /api/search/similar/{ref}), verses close in wording or meaning. Cross-references
// are an editor's judgment; these are found by comparing texts, so they load only when
// asked for and never mix into the list above.
//
// The panes sit after the commentary sources on the track (swipe past the last source)
// and their buttons are pinned at the end of the rail, so they never push commentary
// out of view and are always one tap away. They are not commentary sources: they are
// not in "Your sources" and never become the remembered source.
window.BibleModules = window.BibleModules || {};
(() => {
    const XREF = 'cross-references';
    const NOTES = 'notes';
    const HYMNS = 'hymns';
    const FIRST_SINGLE = 6;     // first screen, one verse
    const FIRST_PER_VERSE = 3;  // first screen, per verse of a range

    const bookIndex = (b) => (typeof BIBLE_BOOKS !== 'undefined' ? BIBLE_BOOKS.indexOf(b) : 0);
    const refOf = (x) => `${x.target_book} ${x.target_chapter}:${x.target_verse}`;
    const bibleOrder = (a, b) => bookIndex(a.target_book) - bookIndex(b.target_book)
        || a.target_chapter - b.target_chapter || a.target_verse - b.target_verse;
    const rankOrder = (a, b) => (b.votes || 0) - (a.votes || 0) || bibleOrder(a, b);
    const narrow = () => window.matchMedia('(max-width: 959px)').matches;

    window.BibleModules.study_panes = {
        studyXref: { key: null, status: 'idle', items: [], credit: '', offline: false, showAll: false, order: 'rank', missing: 0 },
        studyNote: { editing: null, text: '', saving: false },   // editing: null | 'new' | note id
        studySimilar: { key: null, status: 'idle', items: [], showAll: false },   // status: idle | loading | ready | unavailable | error
        studyWriting: false,

        studyToolSlugs() { return [XREF, ...(this.studyHymnsShown() ? [HYMNS] : []), NOTES]; },
        studyIsTool(slug) { return slug === XREF || slug === NOTES || slug === HYMNS; },
        // Every pane on the track, in swipe order
        studyPaneOrder() { return [...this.studyTrack().map(s => s.slug), ...this.studyToolSlugs()]; },
        studyStepPane(dir) {
            const order = this.studyPaneOrder();
            const i = order.indexOf(this.study.active);
            const next = order[Math.min(order.length - 1, Math.max(0, (i < 0 ? 0 : i) + dir))];
            if (next) this.studySelect(next);
        },

        // Called by openStudy() whenever the selection changes
        studyPanesReset() {
            Object.assign(this.studyNote, { editing: null, text: '', saving: false });
            this.studyXref.showAll = false;
            Object.assign(this.studySimilar, { key: null, status: 'idle', items: [], showAll: false });
            this.studyLoadXrefs();
            this.studyLoadHymns();
        },

        // ---------- cross-references ----------
        async studyLoadXrefs() {
            const { book, chapter, vs, ve } = this.study;
            const key = `${book}|${chapter}|${vs}|${ve}|${this.translation}`;
            if (this.studyXref.key === key && this.studyXref.status !== 'error') return;
            Object.assign(this.studyXref, { key, status: 'loading', items: [], offline: false, missing: 0 });
            const ref = `${book} ${chapter}:${vs}${ve > vs ? '-' + ve : ''}`;
            let items = null; let credit = ''; let offline = false;
            try {
                const d = await this.studyFetch(`/api/passage/${encodeURIComponent(ref)}/study/crossrefs?translation=${encodeURIComponent(this.translation)}`);
                items = d.cross_references; credit = d.credit;
            } catch (err) {
                if (err.status && !err.offline) items = null;
                else { items = await this.studyXrefsFromCache({ book, chapter, vs, ve }); offline = true; }
            }
            if (this.studyXref.key !== key) return;   // the selection moved meanwhile
            if (!items) { this.studyXref.status = 'error'; return; }
            Object.assign(this.studyXref, {
                status: 'ready', items, offline,
                credit: credit || 'Cross-references: OpenBible.info, CC BY 4.0',
                missing: items.filter(x => !x.text).length,
            });
        },

        // Offline: links saved with the chapter (reading or a download), text from any
        // saved chapter in the reader's translation. Links without saved text still show.
        async studyXrefsFromCache({ book, chapter, vs, ve }) {
            const os = window.offlineStorage;
            if (!os) return null;
            try {
                const rows = await os.getChapterCrossRefs(book, chapter, vs, ve);
                const seen = new Set();
                const items = [];
                for (const r of rows || []) {
                    const k = `${r.source_verse}|${refOf(r)}`;
                    if (seen.has(k)) continue;
                    seen.add(k);
                    items.push({ source_verse: r.source_verse, target_book: r.target_book, target_chapter: r.target_chapter,
                        target_verse: r.target_verse, votes: r.votes || 0, text: null });
                }
                const chapters = new Map();
                for (const x of items) {
                    const ck = `${x.target_book}|${x.target_chapter}`;
                    if (!chapters.has(ck)) {
                        chapters.set(ck, await os.getChapterVerses(this.translation, x.target_book, x.target_chapter).catch(() => null));
                    }
                    x.text = chapters.get(ck)?.find(v => v.verse === x.target_verse)?.text || null;
                }
                return items;
            } catch (e) {
                console.debug('cross-refs offline fallback failed', e);
                return null;
            }
        },

        studyXrefCount() { return this.studyXref.status === 'ready' ? this.studyXref.items.length : null; },

        // Groups by selected verse (a range), each ranked or in Bible order. The first screen
        // shows the strongest few per verse; showAll shows everything.
        studyXrefGroups() {
            const x = this.studyXref;
            if (x.status !== 'ready') return [];
            const byVerse = new Map();
            for (const it of x.items) {
                if (!byVerse.has(it.source_verse)) byVerse.set(it.source_verse, []);
                byVerse.get(it.source_verse).push(it);
            }
            const multi = byVerse.size > 1;
            const first = multi ? FIRST_PER_VERSE : FIRST_SINGLE;
            return [...byVerse.entries()].sort((a, b) => a[0] - b[0]).map(([verse, list]) => {
                const ranked = [...list].sort(rankOrder);
                const shown = x.showAll ? [...list].sort(x.order === 'bible' ? bibleOrder : rankOrder) : ranked.slice(0, first);
                return {
                    verse, total: list.length,
                    label: multi ? `On verse ${verse}` : null,
                    items: shown.map(it => ({ ...it, ref: refOf(it) })),
                };
            });
        },
        studyXrefHidden() {
            if (this.studyXref.showAll) return 0;
            return this.studyXrefGroups().reduce((n, g) => n + g.total - g.items.length, 0);
        },
        studyXrefShowAll() {
            this.studyXref.showAll = true;
            // Keep the reader's place: the button they tapped is replaced by the rest of the list
            this.$nextTick(() => document.querySelector('.xref-order button[aria-pressed="true"]')?.focus({ preventScroll: true }));
        },

        // ---------- similar verses (computed, on request) ----------
        studySimilarVerse() { return `${this.study.book} ${this.study.chapter}:${this.study.vs}`; },
        studySimilarOffered() {
            return this.isOnline && !this.forcedOffline && !this.studyXref.offline && !!this.study.vs
                && this.srch?.semantic?.available !== false;
        },
        async studyLoadSimilar() {
            const ref = this.studySimilarVerse();
            const key = `${ref}|${this.translation}`;
            if (this.studySimilar.key === key && this.studySimilar.status === 'ready') return;
            Object.assign(this.studySimilar, { key, status: 'loading', items: [], showAll: false });
            try {
                const d = await this.studyFetch(`/api/search/similar/${encodeURIComponent(ref)}?limit=20&translation=${encodeURIComponent(this.translation)}`);
                if (this.studySimilar.key !== key) return;
                if (d.fallback) { this.studySimilar.status = 'unavailable'; return; }
                const xrefs = new Set(this.studyXref.items.map(refOf));
                Object.assign(this.studySimilar, {
                    status: 'ready',
                    // A verse already in the editor's list is not repeated here
                    items: (d.results || []).map(r => ({ ref: `${r.book} ${r.chapter}:${r.verse}`, text: r.snippet }))
                        .filter(r => !xrefs.has(r.ref)),
                });
                this.$nextTick(() => document.querySelector('.similar-list .xref-item')?.focus({ preventScroll: true }));
            } catch (err) {
                if (this.studySimilar.key === key) this.studySimilar.status = err.status === 429 ? 'limited' : 'error';
            }
        },
        studySimilarShown() {
            const x = this.studySimilar;
            return x.showAll ? x.items : x.items.slice(0, FIRST_SINGLE);
        },

        // Path to Christ is a reader dialog: leave the study view, then trace from verse vs
        studyPathToChrist() {
            const ref = `${this.study.book} ${this.study.chapter}:${this.study.vs}`;
            this.studyClose();
            this.findPathToChrist(ref);
        },

        // ---------- notes ----------
        _studyNoteRange(n) { const s = n.startVerse || 1; return [s, n.endVerse || s]; },
        studyNotesExact() {
            const { book, chapter, vs, ve } = this.study;
            return (this.notes || []).filter(n => n.book === book && n.chapter === chapter && n.content?.trim()
                && this._studyNoteRange(n)[0] === vs && this._studyNoteRange(n)[1] === ve);
        },
        studyNotesNearby() {
            const { book, chapter, vs, ve } = this.study;
            return (this.notes || []).filter(n => {
                if (n.book !== book || n.chapter !== chapter || !n.content?.trim()) return false;
                const [s, e] = this._studyNoteRange(n);
                return s <= ve && e >= vs && !(s === vs && e === ve);
            }).sort((a, b) => this._studyNoteRange(a)[0] - this._studyNoteRange(b)[0]);
        },
        studyNoteCount() { return this.studyNotesExact().length + this.studyNotesNearby().length; },
        studyNoteLabel(n) {
            const [s, e] = this._studyNoteRange(n);
            return `${n.book} ${n.chapter}:${s}${e > s ? '–' + e : ''}`;
        },
        // The composer shows when writing a new note, or when there is none yet
        studyNoteComposing() {
            return this.studyNote.editing === 'new' || (this.studyNote.editing === null && this.studyNotesExact().length === 0);
        },

        studyNoteEdit(note) {
            this.studyNote.editing = note.id;
            this.studyNote.text = note.content;
            this.$nextTick(() => document.querySelector('.study-pane[data-slug="notes"] textarea')?.focus());
        },
        studyNoteCancel() {
            this.studyNote.editing = null;
            this.studyNote.text = '';
        },
        async studyNoteSave({ quiet = false } = {}) {
            const text = this.studyNote.text.trim();
            if (!text || this.studyNote.saving) return false;
            const { book, chapter, vs, ve } = this.study;
            this.studyNote.saving = true;
            try {
                const editing = this.studyNote.editing;
                const existing = editing && editing !== 'new' ? this.notes.find(n => n.id === editing) : null;
                if (existing) await this.noteUpdateContent(existing, text);
                else await this.noteCreate({ book, chapter, startVerse: vs, endVerse: ve, content: text });
                Object.assign(this.studyNote, { editing: null, text: '' });
                if (quiet) this.showToast('Note saved', 'success');
                return true;
            } catch (err) {
                console.error('Failed to save note:', err);
                this.showToast(this.isOnline ? "Couldn't save the note. Try again." : "You're offline, so the note couldn't be saved to your account. Try again when you're back online.", 'error');
                return false;
            } finally {
                this.studyNote.saving = false;
            }
        },
        async studyNoteDelete(note) {
            if (!window.confirm(`Delete your note on ${this.studyNoteLabel(note)}?`)) return;
            await this.deleteNote(note.id);
            if (this.studyNote.editing === note.id) this.studyNoteCancel();
        },
        // Unsaved writing is kept when the view closes or the selection moves
        async studyNotesFlush() {
            if (this.studyNote.text.trim()) await this.studyNoteSave({ quiet: true });
        },
        studyNoteOpenVerses(note) {
            const [s, e] = this._studyNoteRange(note);
            this.openStudy(`${note.book} ${note.chapter}:${s}${e > s ? '-' + e : ''}`, { source: NOTES, history: 'push' });
        },

        // ---------- writing on a phone with the keyboard up ----------
        // The visual viewport shrinks under the keyboard (iOS doesn't resize the layout
        // viewport, Android Chrome by default doesn't either). Size the dialog to what is
        // visible, fold the source rail, and keep the verses and the text field on screen.
        studyWritingStart() {
            if (!narrow()) return;
            this.studyWriting = true;
            this.study.stripCollapsed = false;   // the verses being written about stay in view
            const vv = window.visualViewport;
            const dlg = document.getElementById('study-view');
            if (!vv || !dlg) return;
            const fit = () => {
                dlg.style.setProperty('--study-vvh', `${Math.round(vv.height)}px`);
                dlg.style.setProperty('--study-vvtop', `${Math.round(vv.offsetTop)}px`);
                document.activeElement?.closest?.('.snote-form')?.scrollIntoView({ block: 'nearest' });
            };
            this._studyVVFit = fit;
            vv.addEventListener('resize', fit);
            vv.addEventListener('scroll', fit);
            fit();
        },
        studyWritingEnd() {
            // Focus moving to Save/Cancel inside the form isn't the end of writing
            setTimeout(() => {
                if (document.activeElement?.closest?.('.snote-form')) return;
                this.studyWriting = false;
                const vv = window.visualViewport;
                const dlg = document.getElementById('study-view');
                if (vv && this._studyVVFit) {
                    vv.removeEventListener('resize', this._studyVVFit);
                    vv.removeEventListener('scroll', this._studyVVFit);
                }
                this._studyVVFit = null;
                dlg?.style.removeProperty('--study-vvh');
                dlg?.style.removeProperty('--study-vvtop');
            }, 150);
        },
    };
})();
