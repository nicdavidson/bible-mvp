/**
 * BibleMVP - Main Application
 * A free, open-source Bible study platform.
 */

// Old Testament books
const OT_BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
    "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles",
    "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
    "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah",
    "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
    "Haggai", "Zechariah", "Malachi"
];

// New Testament books
const NT_BOOKS = [
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans",
    "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews",
    "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John",
    "Jude", "Revelation"
];

// All Bible books for autocomplete
const BIBLE_BOOKS = [...OT_BOOKS, ...NT_BOOKS];

function bibleApp() {
    return {
        // Book lists for selector
        otBooks: OT_BOOKS,
        ntBooks: NT_BOOKS,

        // State
        referenceInput: '',
        translation: 'WEB',
        currentReference: '',
        currentBook: '',
        currentChapter: 0,
        verses: [],
        highlightedVerses: [],
        commentary: [],
        crossRefs: [],
        notes: [],
        currentNote: '',
        selectedWord: null,
        loading: false,
        error: null,
        darkMode: false,
        activeTab: 'commentary',
        showSearch: false,
        showHelp: false,
        searchQuery: '',
        searchScope: 'all',
        searchResults: [],

        // Autocomplete state
        bookSuggestions: [],
        showSuggestions: false,
        selectedSuggestionIndex: -1,

        // Verse preview tooltip
        versePreview: {
            show: false,
            reference: '',
            text: '',
            x: 0,
            y: 0
        },
        previewTimeout: null,

        // Copy feedback
        copyFeedback: null,

        // Touch detection
        isTouchDevice: false,

        // Mobile resources panel state
        resourcesPanelExpanded: false,

        // Interlinear data
        interlinearData: {},  // verse number -> words array
        showInterlinear: false,

        // Initialize
        async init() {
            // Detect touch device
            this.isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

            // Load dark mode preference
            this.darkMode = localStorage.getItem('darkMode') === 'true';

            // Load notes from IndexedDB
            await this.loadNotes();

            // Check URL for initial reference - support both /Book/Chapter:Verse and ?ref= formats
            const pathRef = this.parsePathReference();
            if (pathRef) {
                this.referenceInput = pathRef;
                await this.loadPassage();
            } else {
                const urlParams = new URLSearchParams(window.location.search);
                const ref = urlParams.get('ref');
                if (ref) {
                    this.referenceInput = ref;
                    await this.loadPassage();
                }
            }

            // Handle browser back/forward
            window.addEventListener('popstate', () => {
                const pathRef = this.parsePathReference();
                if (pathRef) {
                    this.referenceInput = pathRef;
                    this.loadPassage();
                }
            });

            // Setup keyboard shortcuts
            this.setupKeyboardShortcuts();
        },

        // Keyboard shortcuts
        setupKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
                // Ignore if typing in an input
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                    // But allow Escape to blur inputs
                    if (e.key === 'Escape') {
                        e.target.blur();
                        this.showSearch = false;
                        this.showHelp = false;
                        this.selectedWord = null;
                    }
                    return;
                }

                switch (e.key) {
                    case 'ArrowLeft':
                        if (this.currentReference) {
                            e.preventDefault();
                            this.previousChapter();
                        }
                        break;
                    case 'ArrowRight':
                        if (this.currentReference) {
                            e.preventDefault();
                            this.nextChapter();
                        }
                        break;
                    case 'ArrowUp':
                        if (this.currentReference && this.canGoPrevVerse()) {
                            e.preventDefault();
                            this.previousVerse();
                        }
                        break;
                    case 'ArrowDown':
                        if (this.currentReference && this.canGoNextVerse()) {
                            e.preventDefault();
                            this.nextVerse();
                        }
                        break;
                    case '/':
                        e.preventDefault();
                        this.showSearch = true;
                        this.$nextTick(() => this.$refs.searchInput?.focus());
                        break;
                    case 'Escape':
                        this.showSearch = false;
                        this.showHelp = false;
                        this.selectedWord = null;
                        break;
                    case 'd':
                        this.toggleDarkMode();
                        break;
                    case 'c':
                        if (this.highlightedVerses.length === 1) {
                            const verse = this.verses.find(v => v.verse === this.highlightedVerses[0]);
                            if (verse) this.copyVerse(verse);
                        }
                        break;
                    case '?':
                        e.preventDefault();
                        this.showHelp = !this.showHelp;
                        break;
                    case 'g':
                        e.preventDefault();
                        this.$refs.referenceInput?.focus();
                        break;
                }
            });
        },

        // Parse path-based reference from URL (e.g., /John/3/16 or /John/3)
        parsePathReference() {
            const path = window.location.pathname;
            // Match /Book/Chapter or /Book/Chapter/Verse
            const match = path.match(/^\/([^\/]+)\/(\d+)(?:\/(\d+))?$/);
            if (match) {
                const book = decodeURIComponent(match[1]).replace(/-/g, ' ');
                const chapter = match[2];
                const verse = match[3];
                return verse ? `${book} ${chapter}:${verse}` : `${book} ${chapter}`;
            }
            return null;
        },

        // Autocomplete: filter books based on input
        updateSuggestions() {
            const input = this.referenceInput.trim().toLowerCase();

            // Only show suggestions if typing a book name (no chapter yet)
            if (!input || /\d/.test(input)) {
                this.bookSuggestions = [];
                this.showSuggestions = false;
                return;
            }

            this.bookSuggestions = BIBLE_BOOKS.filter(book =>
                book.toLowerCase().startsWith(input)
            ).slice(0, 6);

            this.showSuggestions = this.bookSuggestions.length > 0;
            this.selectedSuggestionIndex = -1;
        },

        // Autocomplete: select a suggestion
        selectSuggestion(book) {
            this.referenceInput = book + ' ';
            this.showSuggestions = false;
            this.bookSuggestions = [];
            // Focus back on input for chapter entry
            this.$nextTick(() => {
                this.$refs.referenceInput?.focus();
            });
        },

        // Autocomplete: handle keyboard navigation
        handleInputKeydown(event) {
            if (!this.showSuggestions) {
                if (event.key === 'Enter') {
                    this.loadPassage();
                }
                return;
            }

            switch (event.key) {
                case 'ArrowDown':
                    event.preventDefault();
                    this.selectedSuggestionIndex = Math.min(
                        this.selectedSuggestionIndex + 1,
                        this.bookSuggestions.length - 1
                    );
                    break;
                case 'ArrowUp':
                    event.preventDefault();
                    this.selectedSuggestionIndex = Math.max(
                        this.selectedSuggestionIndex - 1,
                        -1
                    );
                    break;
                case 'Enter':
                case 'Tab':
                    if (this.selectedSuggestionIndex >= 0) {
                        event.preventDefault();
                        this.selectSuggestion(this.bookSuggestions[this.selectedSuggestionIndex]);
                    } else if (this.bookSuggestions.length === 1) {
                        event.preventDefault();
                        this.selectSuggestion(this.bookSuggestions[0]);
                    } else if (event.key === 'Enter') {
                        this.showSuggestions = false;
                        this.loadPassage();
                    }
                    break;
                case 'Escape':
                    this.showSuggestions = false;
                    break;
            }
        },

        // Hide suggestions when clicking outside
        hideSuggestions() {
            setTimeout(() => {
                this.showSuggestions = false;
            }, 150);
        },

        // Load a passage
        async loadPassage() {
            if (!this.referenceInput.trim()) return;

            this.loading = true;
            this.error = null;
            this.selectedWord = null;

            try {
                const response = await fetch(
                    `/api/passage/${encodeURIComponent(this.referenceInput)}?translation=${this.translation}`
                );

                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.detail || 'Failed to load passage');
                }

                const data = await response.json();
                this.currentReference = data.reference;
                this.verses = data.verses;
                this.crossRefs = data.cross_references || [];
                this.highlightedVerses = data.highlighted_verses || [];

                // Parse reference for navigation
                this.parseCurrentReference();

                // Update URL with clean path format
                this.updateURL();

                // Load commentary
                await this.loadCommentary();

                // Load interlinear data if available (Genesis or Matthew)
                if (this.currentBook === 'Genesis' || this.currentBook === 'Matthew') {
                    await this.loadInterlinearData();
                } else {
                    this.interlinearData = {};
                }

                // Scroll to highlighted verse if any
                if (this.highlightedVerses.length > 0) {
                    this.$nextTick(() => {
                        const firstHighlighted = document.getElementById(`verse-${this.highlightedVerses[0]}`);
                        if (firstHighlighted) {
                            firstHighlighted.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        }
                    });
                }

            } catch (err) {
                this.error = err.message;
                this.verses = [];
            } finally {
                this.loading = false;
            }
        },

        // Load a reference (from cross-ref click, etc.)
        async loadReference(ref) {
            this.referenceInput = ref;
            await this.loadPassage();
        },

        // Load commentary for current passage
        async loadCommentary() {
            try {
                const response = await fetch(
                    `/api/passage/${encodeURIComponent(this.currentReference)}/commentary`
                );

                if (response.ok) {
                    const data = await response.json();
                    this.commentary = data.entries || [];
                }
            } catch (err) {
                console.error('Failed to load commentary:', err);
                this.commentary = [];
            }
        },

        // Parse reference for chapter navigation
        parseCurrentReference() {
            const match = this.currentReference.match(/^(.+?)\s+(\d+)/);
            if (match) {
                this.currentBook = match[1];
                this.currentChapter = parseInt(match[2]);
            }
        },

        // Navigate to previous chapter
        previousChapter() {
            if (this.currentChapter > 1) {
                this.referenceInput = `${this.currentBook} ${this.currentChapter - 1}`;
                this.loadPassage();
            }
        },

        // Navigate to next chapter
        nextChapter() {
            this.referenceInput = `${this.currentBook} ${this.currentChapter + 1}`;
            this.loadPassage();
        },

        // Get first highlighted verse or 1
        getCurrentVerse() {
            return this.highlightedVerses.length > 0 ? this.highlightedVerses[0] : 1;
        },

        // Check if can go to previous verse
        canGoPrevVerse() {
            return this.highlightedVerses.length > 0 && this.highlightedVerses[0] > 1;
        },

        // Check if can go to next verse
        canGoNextVerse() {
            if (this.highlightedVerses.length === 0) return this.verses.length > 0;
            const lastHighlighted = this.highlightedVerses[this.highlightedVerses.length - 1];
            const maxVerse = this.verses.length > 0 ? Math.max(...this.verses.map(v => v.verse)) : 0;
            return lastHighlighted < maxVerse;
        },

        // Navigate to previous verse
        previousVerse() {
            const currentVerse = this.getCurrentVerse();
            if (currentVerse > 1) {
                this.referenceInput = `${this.currentBook} ${this.currentChapter}:${currentVerse - 1}`;
                this.loadPassage();
            }
        },

        // Navigate to next verse
        nextVerse() {
            const currentVerse = this.highlightedVerses.length > 0
                ? this.highlightedVerses[this.highlightedVerses.length - 1]
                : 0;
            const maxVerse = this.verses.length > 0 ? Math.max(...this.verses.map(v => v.verse)) : 0;
            if (currentVerse < maxVerse) {
                this.referenceInput = `${this.currentBook} ${this.currentChapter}:${currentVerse + 1}`;
                this.loadPassage();
            }
        },

        // Handle click on verse box - select verse unless clicking a word
        async handleVerseBoxClick(event, verseNum) {
            // On touch devices, always select the verse (don't trigger word lookup)
            // Word lookup is a power feature better suited for desktop
            if (this.isTouchDevice) {
                await this.selectVerse(verseNum);
                return;
            }

            // On desktop, if clicked on a word, handle word click instead
            const wordEl = event.target.closest('.word');
            if (wordEl) {
                this.handleWordClick(event);
                return;
            }

            // Otherwise select the verse
            await this.selectVerse(verseNum);
        },

        // Select a specific verse (click on verse box)
        async selectVerse(verseNum) {
            // Update highlighted verses without reloading the whole passage
            this.highlightedVerses = [verseNum];
            this.selectedWord = null; // Clear word selection

            // Remove previous word selections
            document.querySelectorAll('.word.selected').forEach(el => {
                el.classList.remove('selected');
            });

            // Update reference display
            this.currentReference = `${this.currentBook} ${this.currentChapter}:${verseNum}`;
            this.referenceInput = this.currentReference;

            // Update URL
            this.updateURL();

            // Reload cross-references and commentary for the selected verse
            await this.loadCrossRefs();
            await this.loadCommentary();
        },

        // Load cross-references for current verse
        async loadCrossRefs() {
            try {
                const response = await fetch(
                    `/api/passage/${encodeURIComponent(this.currentReference)}/crossrefs`
                );

                if (response.ok) {
                    const data = await response.json();
                    this.crossRefs = data.cross_references || [];
                }
            } catch (err) {
                console.error('Failed to load cross-refs:', err);
                this.crossRefs = [];
            }
        },

        // Show verse preview on hover (desktop only)
        async previewVerse(ref, event) {
            // Don't show preview on touch devices - it's annoying
            if (this.isTouchDevice) return;

            // Clear any pending timeout
            if (this.previewTimeout) {
                clearTimeout(this.previewTimeout);
            }

            // Delay slightly to avoid flickering
            this.previewTimeout = setTimeout(async () => {
                try {
                    const response = await fetch(
                        `/api/verse/${encodeURIComponent(ref)}?translation=${this.translation}`
                    );

                    if (response.ok) {
                        const data = await response.json();
                        const rect = event.target.getBoundingClientRect();

                        this.versePreview = {
                            show: true,
                            reference: ref,
                            text: data.text,
                            x: Math.min(rect.left, window.innerWidth - 320),
                            y: rect.bottom + window.scrollY + 8
                        };
                    }
                } catch (err) {
                    console.error('Failed to load verse preview:', err);
                }
            }, 200);
        },

        // Hide verse preview
        hidePreview() {
            if (this.previewTimeout) {
                clearTimeout(this.previewTimeout);
            }
            this.versePreview.show = false;
        },

        // Load interlinear data for highlighted verses
        async loadInterlinearData() {
            this.interlinearData = {};

            // Load interlinear for each verse in the chapter
            const versesToLoad = this.highlightedVerses.length > 0
                ? this.highlightedVerses
                : this.verses.map(v => v.verse);

            for (const verseNum of versesToLoad) {
                try {
                    const ref = `${this.currentBook} ${this.currentChapter}:${verseNum}`;
                    const response = await fetch(
                        `/api/verse/${encodeURIComponent(ref)}/interlinear?translation=${this.translation}`
                    );

                    if (response.ok) {
                        const data = await response.json();
                        if (data.has_interlinear && data.words.length > 0) {
                            this.interlinearData[verseNum] = data;
                        }
                    }
                } catch (err) {
                    console.error(`Failed to load interlinear for verse ${verseNum}:`, err);
                }
            }
        },

        // Check if verse has interlinear data
        hasInterlinear(verseNum) {
            return !!this.interlinearData[verseNum];
        },

        // Get interlinear words for a verse
        getInterlinearWords(verseNum) {
            return this.interlinearData[verseNum]?.words || [];
        },

        // Get language for interlinear display
        getInterlinearLanguage(verseNum) {
            return this.interlinearData[verseNum]?.language || 'unknown';
        },

        // Format verse text with clickable words
        formatVerseText(text) {
            // Just wrap each word in a span for click handling
            return text.split(/\s+/).map((word, i) => {
                const cleanWord = word.replace(/[.,;:!?'"()]/g, '');
                const punct = word.replace(cleanWord, '');
                return `<span class="word" data-word="${cleanWord}">${cleanWord}</span>${punct}`;
            }).join(' ');
        },

        // Handle word click (for interlinear words)
        async handleWordClick(event) {
            const wordEl = event.target.closest('.word');
            if (!wordEl) return;

            const strongNum = wordEl.dataset.strong;

            // Remove previous selection
            document.querySelectorAll('.word.selected').forEach(el => {
                el.classList.remove('selected');
            });
            wordEl.classList.add('selected');

            // If we have a Strong's number, look it up
            if (strongNum && strongNum !== 'null') {
                await this.loadWordDetails(strongNum);
            } else {
                // For words without Strong's data
                const word = wordEl.dataset.word || wordEl.textContent;
                this.selectedWord = {
                    text: word,
                    original: '---',
                    transliteration: '---',
                    strong_number: null,
                    parsing: 'No Strong\'s number available',
                    definition: 'This word does not have interlinear data linked.',
                    occurrences: [],
                    count: 0
                };
            }
        },

        // Handle interlinear word click
        async handleInterlinearWordClick(word) {
            // Remove previous selection
            document.querySelectorAll('.word.selected, .interlinear-word.selected').forEach(el => {
                el.classList.remove('selected');
            });

            if (word.strong_number) {
                await this.loadWordDetails(word.strong_number);
            } else {
                this.selectedWord = {
                    text: word.original_text,
                    original: word.lexeme || word.original_text,
                    transliteration: word.transliteration || '---',
                    strong_number: null,
                    parsing: word.parsing || 'N/A',
                    definition: word.definition || 'No definition available',
                    occurrences: [],
                    count: 0
                };
            }
        },

        // Load word details by Strong's number
        async loadWordDetails(strongNumber) {
            try {
                const response = await fetch(`/api/word/${strongNumber}`);
                if (response.ok) {
                    const data = await response.json();
                    this.selectedWord = {
                        text: data.word.original || strongNumber,
                        original: data.word.original,
                        transliteration: data.word.transliteration,
                        pronunciation: data.word.pronunciation,
                        strong_number: data.word.strong_number,
                        parsing: data.word.language === 'hebrew' ? 'Hebrew' : 'Greek',
                        definition: data.word.definition,
                        extended_definition: data.word.extended_definition,
                        derivation: data.word.derivation,
                        language: data.word.language,
                        occurrences: data.occurrences,
                        count: data.count
                    };
                }
            } catch (err) {
                console.error('Failed to load word details:', err);
            }
        },

        // Toggle dark mode
        toggleDarkMode() {
            this.darkMode = !this.darkMode;
            localStorage.setItem('darkMode', this.darkMode);
        },

        // Search
        async performSearch() {
            if (!this.searchQuery.trim()) return;

            try {
                const response = await fetch(
                    `/api/search?q=${encodeURIComponent(this.searchQuery)}&scope=${this.searchScope}`
                );

                if (response.ok) {
                    const data = await response.json();
                    this.searchResults = data.results;
                }
            } catch (err) {
                console.error('Search failed:', err);
            }
        },

        // Go to search result
        goToSearchResult(result) {
            if (result.book && result.chapter) {
                const ref = result.verse
                    ? `${result.book} ${result.chapter}:${result.verse}`
                    : `${result.book} ${result.chapter}`;
                this.loadReference(ref);
                this.showSearch = false;
            }
        },

        // Notes (IndexedDB)
        async loadNotes() {
            // Simple localStorage fallback for now
            // Full implementation would use IndexedDB
            try {
                const saved = localStorage.getItem('bible-notes');
                this.notes = saved ? JSON.parse(saved) : [];
            } catch (err) {
                console.error('Failed to load notes:', err);
                this.notes = [];
            }
        },

        // Note editing state
        noteEndVerse: null,
        showNoteRange: false,

        // Get the current start verse for notes
        getNoteStartVerse() {
            return this.highlightedVerses.length > 0 ? this.highlightedVerses[0] : 1;
        },

        // Format note reference display
        formatNoteReference(note) {
            if (note.endVerse && note.endVerse !== note.startVerse) {
                return `${note.book} ${note.chapter}:${note.startVerse}-${note.endVerse}`;
            }
            return `${note.book} ${note.chapter}:${note.startVerse}`;
        },

        // Check if note applies to current verse
        noteMatchesCurrentVerse(note) {
            if (note.book !== this.currentBook || note.chapter !== this.currentChapter) {
                return false;
            }
            const currentVerse = this.highlightedVerses[0];
            if (!currentVerse) return true; // Show all notes for chapter if no verse selected
            const start = note.startVerse || 1;
            const end = note.endVerse || start;
            return currentVerse >= start && currentVerse <= end;
        },

        // Get notes that match current selection
        getRelevantNotes() {
            return this.notes.filter(note => this.noteMatchesCurrentVerse(note));
        },

        async saveNote() {
            if (!this.currentNote.trim() || !this.currentBook) return;

            const startVerse = this.getNoteStartVerse();
            const endVerse = this.showNoteRange && this.noteEndVerse ? parseInt(this.noteEndVerse) : startVerse;

            const note = {
                id: Date.now(),
                book: this.currentBook,
                chapter: this.currentChapter,
                startVerse: startVerse,
                endVerse: endVerse,
                content: this.currentNote,
                created_at: new Date().toISOString()
            };

            this.notes.unshift(note);
            localStorage.setItem('bible-notes', JSON.stringify(this.notes));
            this.currentNote = '';
            this.noteEndVerse = null;
            this.showNoteRange = false;
        },

        // Delete a note
        deleteNote(noteId) {
            this.notes = this.notes.filter(n => n.id !== noteId);
            localStorage.setItem('bible-notes', JSON.stringify(this.notes));
        },

        // Format date
        formatDate(isoString) {
            return new Date(isoString).toLocaleDateString();
        },

        // Check if a verse should be highlighted
        isVerseHighlighted(verseNum) {
            return this.highlightedVerses.includes(verseNum);
        },

        // Update URL with clean path format (/Book/Chapter/Verse)
        updateURL() {
            if (!this.currentBook || !this.currentChapter) return;

            const bookSlug = this.currentBook.replace(/\s+/g, '-');
            const verse = this.highlightedVerses.length === 1 ? this.highlightedVerses[0] : null;
            const path = verse
                ? `/${bookSlug}/${this.currentChapter}/${verse}`
                : `/${bookSlug}/${this.currentChapter}`;

            window.history.pushState({}, '', path);
        },

        // Copy verse to clipboard
        async copyVerse(verse) {
            const text = `"${verse.text}" — ${this.currentBook} ${this.currentChapter}:${verse.verse} ${this.translation}`;

            try {
                await navigator.clipboard.writeText(text);
                this.copyFeedback = verse.verse;
                setTimeout(() => {
                    this.copyFeedback = null;
                }, 1500);
            } catch (err) {
                console.error('Failed to copy:', err);
            }
        },

        // Get reading progress percentage
        getReadingProgress() {
            if (!this.verses.length || !this.highlightedVerses.length) return 0;
            const currentVerse = this.highlightedVerses[0];
            return Math.round((currentVerse / this.verses.length) * 100);
        }
    };
}
