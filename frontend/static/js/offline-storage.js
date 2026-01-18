/**
 * Offline Storage Manager
 * Handles IndexedDB storage for offline Bible data
 */

const DB_NAME = 'BibleMVP';
const DB_VERSION = 1;

// Store names
const STORES = {
    VERSES: 'verses',
    ALIGNMENTS: 'alignments',
    LEXICON: 'lexicon',
    CROSS_REFS: 'crossRefs',
    COMMENTARY: 'commentary',
    INTERLINEAR: 'interlinear',
    META: 'meta'  // Track what's downloaded
};

class OfflineStorage {
    constructor() {
        this.db = null;
        this.ready = this.init();
    }

    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                this.db = request.result;
                resolve(this);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // Verses store: key = "translation:book:chapter"
                if (!db.objectStoreNames.contains(STORES.VERSES)) {
                    const versesStore = db.createObjectStore(STORES.VERSES, { keyPath: 'id' });
                    versesStore.createIndex('by_ref', ['translation', 'book', 'chapter']);
                }

                // Alignments store: key = "translation:book:chapter:verse:position"
                if (!db.objectStoreNames.contains(STORES.ALIGNMENTS)) {
                    const alignStore = db.createObjectStore(STORES.ALIGNMENTS, { keyPath: 'id' });
                    alignStore.createIndex('by_ref', ['translation', 'book', 'chapter']);
                }

                // Lexicon store: key = strong_number
                if (!db.objectStoreNames.contains(STORES.LEXICON)) {
                    db.createObjectStore(STORES.LEXICON, { keyPath: 'strong_number' });
                }

                // Cross-references store: key = "book:chapter:verse"
                if (!db.objectStoreNames.contains(STORES.CROSS_REFS)) {
                    const xrefStore = db.createObjectStore(STORES.CROSS_REFS, { keyPath: 'id' });
                    xrefStore.createIndex('by_ref', ['book', 'chapter']);
                }

                // Commentary store: key = "source:book:chapter"
                if (!db.objectStoreNames.contains(STORES.COMMENTARY)) {
                    const commStore = db.createObjectStore(STORES.COMMENTARY, { keyPath: 'id' });
                    commStore.createIndex('by_ref', ['book', 'chapter']);
                }

                // Interlinear store: key = "book:chapter:verse:position"
                if (!db.objectStoreNames.contains(STORES.INTERLINEAR)) {
                    const intStore = db.createObjectStore(STORES.INTERLINEAR, { keyPath: 'id' });
                    intStore.createIndex('by_ref', ['book', 'chapter']);
                }

                // Meta store: track what's downloaded
                if (!db.objectStoreNames.contains(STORES.META)) {
                    db.createObjectStore(STORES.META, { keyPath: 'key' });
                }
            };
        });
    }

    // ========== VERSES ==========

    async saveChapterVerses(translation, book, chapter, verses) {
        await this.ready;
        const tx = this.db.transaction(STORES.VERSES, 'readwrite');
        const store = tx.objectStore(STORES.VERSES);

        for (const verse of verses) {
            await store.put({
                id: `${translation}:${book}:${chapter}:${verse.verse}`,
                translation,
                book,
                chapter,
                verse: verse.verse,
                text: verse.text
            });
        }

        // Mark chapter as cached
        await this.setMeta(`verses:${translation}:${book}:${chapter}`, {
            cached: true,
            timestamp: Date.now(),
            count: verses.length
        });
    }

    async getChapterVerses(translation, book, chapter) {
        await this.ready;
        const tx = this.db.transaction(STORES.VERSES, 'readonly');
        const store = tx.objectStore(STORES.VERSES);
        const index = store.index('by_ref');

        return new Promise((resolve, reject) => {
            const request = index.getAll([translation, book, chapter]);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async hasChapterVerses(translation, book, chapter) {
        const meta = await this.getMeta(`verses:${translation}:${book}:${chapter}`);
        return meta?.cached === true;
    }

    // ========== ALIGNMENTS ==========

    async saveChapterAlignments(translation, book, chapter, alignments) {
        await this.ready;
        const tx = this.db.transaction(STORES.ALIGNMENTS, 'readwrite');
        const store = tx.objectStore(STORES.ALIGNMENTS);

        for (const align of alignments) {
            await store.put({
                id: `${translation}:${book}:${chapter}:${align.verse}:${align.position}`,
                translation,
                book,
                chapter,
                ...align
            });
        }

        await this.setMeta(`alignments:${translation}:${book}:${chapter}`, {
            cached: true,
            timestamp: Date.now(),
            count: alignments.length
        });
    }

    async getWordAlignment(translation, book, chapter, verse, position) {
        await this.ready;
        const tx = this.db.transaction(STORES.ALIGNMENTS, 'readonly');
        const store = tx.objectStore(STORES.ALIGNMENTS);

        return new Promise((resolve, reject) => {
            const request = store.get(`${translation}:${book}:${chapter}:${verse}:${position}`);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async hasChapterAlignments(translation, book, chapter) {
        const meta = await this.getMeta(`alignments:${translation}:${book}:${chapter}`);
        return meta?.cached === true;
    }

    // ========== LEXICON ==========

    async saveLexiconEntries(entries) {
        await this.ready;
        const tx = this.db.transaction(STORES.LEXICON, 'readwrite');
        const store = tx.objectStore(STORES.LEXICON);

        for (const entry of entries) {
            await store.put(entry);
        }

        await this.setMeta('lexicon', {
            cached: true,
            timestamp: Date.now(),
            count: entries.length
        });
    }

    async getLexiconEntry(strongNumber) {
        await this.ready;
        const tx = this.db.transaction(STORES.LEXICON, 'readonly');
        const store = tx.objectStore(STORES.LEXICON);

        return new Promise((resolve, reject) => {
            const request = store.get(strongNumber);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async hasLexicon() {
        const meta = await this.getMeta('lexicon');
        return meta?.cached === true;
    }

    // ========== CROSS-REFERENCES ==========

    async saveChapterCrossRefs(book, chapter, refs) {
        await this.ready;
        const tx = this.db.transaction(STORES.CROSS_REFS, 'readwrite');
        const store = tx.objectStore(STORES.CROSS_REFS);

        for (const ref of refs) {
            await store.put({
                id: `${book}:${chapter}:${ref.source_verse}:${ref.target_book}:${ref.target_chapter}:${ref.target_verse}`,
                book,
                chapter,
                ...ref
            });
        }

        await this.setMeta(`crossrefs:${book}:${chapter}`, {
            cached: true,
            timestamp: Date.now(),
            count: refs.length
        });
    }

    async getChapterCrossRefs(book, chapter, verseStart, verseEnd) {
        await this.ready;
        const tx = this.db.transaction(STORES.CROSS_REFS, 'readonly');
        const store = tx.objectStore(STORES.CROSS_REFS);
        const index = store.index('by_ref');

        return new Promise((resolve, reject) => {
            const request = index.getAll([book, chapter]);
            request.onsuccess = () => {
                // Filter by verse range if specified
                let results = request.result;
                if (verseStart !== undefined) {
                    results = results.filter(r =>
                        r.source_verse >= verseStart &&
                        r.source_verse <= (verseEnd || verseStart)
                    );
                }
                resolve(results);
            };
            request.onerror = () => reject(request.error);
        });
    }

    // ========== COMMENTARY ==========

    async saveChapterCommentary(book, chapter, entries) {
        await this.ready;
        const tx = this.db.transaction(STORES.COMMENTARY, 'readwrite');
        const store = tx.objectStore(STORES.COMMENTARY);

        for (const entry of entries) {
            await store.put({
                id: `${entry.source}:${book}:${chapter}:${entry.reference_start}`,
                book,
                chapter,
                ...entry
            });
        }

        await this.setMeta(`commentary:${book}:${chapter}`, {
            cached: true,
            timestamp: Date.now(),
            count: entries.length
        });
    }

    async getChapterCommentary(book, chapter, verseStart, verseEnd) {
        await this.ready;
        const tx = this.db.transaction(STORES.COMMENTARY, 'readonly');
        const store = tx.objectStore(STORES.COMMENTARY);
        const index = store.index('by_ref');

        return new Promise((resolve, reject) => {
            const request = index.getAll([book, chapter]);
            request.onsuccess = () => {
                let results = request.result;
                if (verseStart !== undefined) {
                    results = results.filter(entry => {
                        const entryStart = entry.reference_start;
                        const entryEnd = entry.reference_end || entryStart;
                        return entryStart <= verseEnd && entryEnd >= verseStart;
                    });
                }
                resolve(results);
            };
            request.onerror = () => reject(request.error);
        });
    }

    // ========== INTERLINEAR ==========

    async saveChapterInterlinear(book, chapter, words) {
        await this.ready;
        const tx = this.db.transaction(STORES.INTERLINEAR, 'readwrite');
        const store = tx.objectStore(STORES.INTERLINEAR);

        for (const word of words) {
            await store.put({
                id: `${book}:${chapter}:${word.verse}:${word.position}`,
                book,
                chapter,
                ...word
            });
        }

        await this.setMeta(`interlinear:${book}:${chapter}`, {
            cached: true,
            timestamp: Date.now(),
            count: words.length
        });
    }

    async getChapterInterlinear(book, chapter) {
        await this.ready;
        const tx = this.db.transaction(STORES.INTERLINEAR, 'readonly');
        const store = tx.objectStore(STORES.INTERLINEAR);
        const index = store.index('by_ref');

        return new Promise((resolve, reject) => {
            const request = index.getAll([book, chapter]);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    // ========== META ==========

    async setMeta(key, value) {
        await this.ready;
        const tx = this.db.transaction(STORES.META, 'readwrite');
        const store = tx.objectStore(STORES.META);
        await store.put({ key, ...value });
    }

    async getMeta(key) {
        await this.ready;
        const tx = this.db.transaction(STORES.META, 'readonly');
        const store = tx.objectStore(STORES.META);

        return new Promise((resolve, reject) => {
            const request = store.get(key);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    // ========== STATS ==========

    async getStorageStats() {
        await this.ready;
        const stats = {
            verses: { translations: {} },
            alignments: { translations: {} },
            lexicon: { cached: false, count: 0 },
            crossRefs: { books: 0, chapters: 0 },
            commentary: { books: 0, chapters: 0 },
            interlinear: { books: 0, chapters: 0 }
        };

        // Count all meta entries to build stats
        const tx = this.db.transaction(STORES.META, 'readonly');
        const store = tx.objectStore(STORES.META);

        return new Promise((resolve, reject) => {
            const request = store.getAll();
            request.onsuccess = () => {
                for (const meta of request.result) {
                    const parts = meta.key.split(':');
                    const type = parts[0];

                    if (type === 'verses' && parts.length >= 4) {
                        const translation = parts[1];
                        if (!stats.verses.translations[translation]) {
                            stats.verses.translations[translation] = { chapters: 0, verses: 0 };
                        }
                        stats.verses.translations[translation].chapters++;
                        stats.verses.translations[translation].verses += meta.count || 0;
                    } else if (type === 'alignments' && parts.length >= 4) {
                        const translation = parts[1];
                        if (!stats.alignments.translations[translation]) {
                            stats.alignments.translations[translation] = { chapters: 0, words: 0 };
                        }
                        stats.alignments.translations[translation].chapters++;
                        stats.alignments.translations[translation].words += meta.count || 0;
                    } else if (type === 'lexicon') {
                        stats.lexicon.cached = true;
                        stats.lexicon.count = meta.count || 0;
                    } else if (type === 'crossrefs') {
                        stats.crossRefs.chapters++;
                    } else if (type === 'commentary') {
                        stats.commentary.chapters++;
                    } else if (type === 'interlinear') {
                        stats.interlinear.chapters++;
                    }
                }
                resolve(stats);
            };
            request.onerror = () => reject(request.error);
        });
    }

    // ========== CLEAR ==========

    async clearAll() {
        await this.ready;
        const storeNames = Object.values(STORES);
        const tx = this.db.transaction(storeNames, 'readwrite');

        for (const storeName of storeNames) {
            tx.objectStore(storeName).clear();
        }

        return new Promise((resolve, reject) => {
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error);
        });
    }

    async clearStore(storeName) {
        await this.ready;
        const tx = this.db.transaction(storeName, 'readwrite');
        tx.objectStore(storeName).clear();

        return new Promise((resolve, reject) => {
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error);
        });
    }
}

// Export singleton instance
window.offlineStorage = new OfflineStorage();
