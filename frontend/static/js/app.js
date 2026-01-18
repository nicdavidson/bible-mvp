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

// Chapter counts for each book
const BOOK_CHAPTERS = {
    "Genesis": 50, "Exodus": 40, "Leviticus": 27, "Numbers": 36, "Deuteronomy": 34,
    "Joshua": 24, "Judges": 21, "Ruth": 4, "1 Samuel": 31, "2 Samuel": 24,
    "1 Kings": 22, "2 Kings": 25, "1 Chronicles": 29, "2 Chronicles": 36,
    "Ezra": 10, "Nehemiah": 13, "Esther": 10, "Job": 42, "Psalms": 150, "Proverbs": 31,
    "Ecclesiastes": 12, "Song of Solomon": 8, "Isaiah": 66, "Jeremiah": 52,
    "Lamentations": 5, "Ezekiel": 48, "Daniel": 12, "Hosea": 14, "Joel": 3, "Amos": 9,
    "Obadiah": 1, "Jonah": 4, "Micah": 7, "Nahum": 3, "Habakkuk": 3, "Zephaniah": 3,
    "Haggai": 2, "Zechariah": 14, "Malachi": 4,
    "Matthew": 28, "Mark": 16, "Luke": 24, "John": 21, "Acts": 28, "Romans": 16,
    "1 Corinthians": 16, "2 Corinthians": 13, "Galatians": 6, "Ephesians": 6,
    "Philippians": 4, "Colossians": 4, "1 Thessalonians": 5, "2 Thessalonians": 3,
    "1 Timothy": 6, "2 Timothy": 4, "Titus": 3, "Philemon": 1, "Hebrews": 13,
    "James": 5, "1 Peter": 5, "2 Peter": 3, "1 John": 5, "2 John": 1, "3 John": 1,
    "Jude": 1, "Revelation": 22
};

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
        showAllOccurrences: false,
        loading: false,
        loadingCommentary: false,
        error: null,
        darkMode: false,
        activeTab: 'commentary',
        showSearch: false,
        showHelp: false,
        searchQuery: '',
        searchScope: 'all',
        searchResults: [],
        searchWordInfo: null,  // Strong's word info for Strong's searches
        searchLoading: false,
        searchPerformed: false,
        searchDebounceTimer: null,
        selectedResultIndex: -1,

        // Autocomplete state
        bookSuggestions: [],
        showSuggestions: false,
        selectedSuggestionIndex: -1,

        // Book picker state
        showBookPicker: false,
        pickerSelectedBook: null,
        bookChapters: BOOK_CHAPTERS,

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
                        this.openSearch();
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

        // Book picker methods
        toggleBookPicker() {
            this.showBookPicker = !this.showBookPicker;
            if (this.showBookPicker) {
                this.pickerSelectedBook = null;
            }
        },

        selectPickerBook(book) {
            this.pickerSelectedBook = book;
        },

        selectPickerChapter(chapter) {
            this.referenceInput = `${this.pickerSelectedBook} ${chapter}`;
            this.showBookPicker = false;
            this.pickerSelectedBook = null;
            this.loadPassage();
        },

        getChapterCount(book) {
            return this.bookChapters[book] || 1;
        },

        getChaptersArray(book) {
            const count = this.getChapterCount(book);
            return Array.from({ length: count }, (_, i) => i + 1);
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

                // Load interlinear data if available (OT books or Matthew)
                if (OT_BOOKS.includes(this.currentBook) || NT_BOOKS.includes(this.currentBook)) {
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
            this.loadingCommentary = true;
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
            } finally {
                this.loadingCommentary = false;
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

        // Navigate to previous verse (within same chapter - no reload)
        previousVerse() {
            const currentVerse = this.getCurrentVerse();
            if (currentVerse > 1) {
                this.navigateToVerse(currentVerse - 1);
            }
        },

        // Navigate to next verse (within same chapter - no reload)
        nextVerse() {
            const currentVerse = this.highlightedVerses.length > 0
                ? this.highlightedVerses[this.highlightedVerses.length - 1]
                : 0;
            const maxVerse = this.verses.length > 0 ? Math.max(...this.verses.map(v => v.verse)) : 0;
            if (currentVerse < maxVerse) {
                this.navigateToVerse(currentVerse + 1);
            }
        },

        // Navigate to a verse within the current chapter without reloading
        navigateToVerse(verseNum) {
            // Update state
            this.highlightedVerses = [verseNum];
            this.currentReference = `${this.currentBook} ${this.currentChapter}:${verseNum}`;
            this.referenceInput = this.currentReference;
            this.selectedWord = null;

            // Update URL
            this.updateURL();

            // Load cross-refs for the new verse
            this.loadCrossRefs(verseNum);

            // Load commentary for new verse
            this.loadCommentary();

            // Scroll to verse
            this.$nextTick(() => {
                const verseEl = document.getElementById(`verse-${verseNum}`);
                if (verseEl) {
                    verseEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            });
        },

        // Load cross-references for a specific verse
        async loadCrossRefs(verseNum) {
            try {
                const ref = `${this.currentBook} ${this.currentChapter}:${verseNum}`;
                const response = await fetch(
                    `/api/passage/${encodeURIComponent(ref)}/crossrefs`
                );
                if (response.ok) {
                    const data = await response.json();
                    this.crossRefs = data.cross_references || [];
                }
            } catch (err) {
                console.error('Failed to load cross-refs:', err);
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

        // Handle clicks on Bible reference links in commentary
        handleCommentaryClick(event) {
            const link = event.target.closest('.commentary-ref');
            if (link) {
                event.preventDefault();
                const ref = link.dataset.ref;
                if (ref) {
                    this.loadReference(ref);
                }
            }
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

        // Load interlinear data for the entire chapter
        async loadInterlinearData() {
            this.interlinearData = {};

            try {
                const ref = `${this.currentBook} ${this.currentChapter}`;
                const response = await fetch(
                    `/api/passage/${encodeURIComponent(ref)}/interlinear?translation=${this.translation}`
                );

                if (response.ok) {
                    const data = await response.json();
                    if (data.has_interlinear && data.verses) {
                        // Store language for the chapter
                        this.interlinearLanguage = data.language;
                        // Convert verses object to our format
                        for (const [verseNum, words] of Object.entries(data.verses)) {
                            this.interlinearData[parseInt(verseNum)] = {
                                language: data.language,
                                words: words
                            };
                        }
                    }
                }
            } catch (err) {
                console.error('Failed to load interlinear data:', err);
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

        // Get gloss for a word (translation for Greek, short definition for Hebrew)
        getWordGloss(word) {
            // Greek words have translation field from OpenGNT
            if (word.translation) {
                return word.translation;
            }
            // Hebrew words - extract first part of definition
            if (word.definition) {
                // Get first clause/phrase (up to comma, semicolon, or 40 chars)
                let def = word.definition;
                const comma = def.indexOf(',');
                const semi = def.indexOf(';');
                let cutoff = Math.min(
                    comma > 0 ? comma : 999,
                    semi > 0 ? semi : 999,
                    40
                );
                if (cutoff < def.length) {
                    def = def.substring(0, cutoff);
                }
                return def;
            }
            return '·';
        },

        // Format verse text with clickable words
        formatVerseText(text) {
            // Wrap each word in a span with position for alignment lookup
            let wordPosition = 0;
            return text.split(/\s+/).map((word) => {
                const cleanWord = word.replace(/[.,;:!?'"()]/g, '');
                const punct = word.replace(cleanWord, '');
                if (cleanWord) wordPosition++;
                return `<span class="word" data-word="${cleanWord}" data-position="${wordPosition}">${cleanWord}</span>${punct}`;
            }).join(' ');
        },

        // Handle word click (for English words in verse text)
        async handleWordClick(event) {
            const wordEl = event.target.closest('.word');
            if (!wordEl) return;

            // Remove previous selection
            document.querySelectorAll('.word.selected, .interlinear-word.selected').forEach(el => {
                el.classList.remove('selected');
            });
            wordEl.classList.add('selected');

            const word = wordEl.dataset.word || wordEl.textContent;
            const wordPosition = parseInt(wordEl.dataset.position, 10);

            // Get verse number from parent verse-box
            const verseBox = wordEl.closest('.verse-box');
            const verseId = verseBox?.id || '';
            const verseNum = parseInt(verseId.replace('verse-', ''), 10);

            // Try database lookup for word alignment
            if (this.currentBook && this.currentChapter && verseNum && wordPosition) {
                try {
                    const params = new URLSearchParams({
                        book: this.currentBook,
                        chapter: this.currentChapter,
                        verse: verseNum,
                        word_position: wordPosition,
                        translation: this.translation
                    });
                    const response = await fetch(`/api/word-alignment?${params}`);
                    const data = await response.json();

                    if (data.found && data.alignment) {
                        const align = data.alignment;
                        this.selectedWord = {
                            text: word,
                            original: align.original_text,
                            transliteration: align.transliteration,
                            strong_number: align.strong_number,
                            parsing: align.parsing,
                            definition: align.definition || align.english_gloss,
                            extended_definition: align.extended_definition,
                            language: align.language,
                            occurrences: [],
                            count: 0
                        };

                        // Also highlight the corresponding interlinear word if visible
                        if (this.showInterlinear) {
                            const origPos = align.original_word_position;
                            const interlinearWords = verseBox?.querySelectorAll('.interlinear-word');
                            interlinearWords?.forEach((el, idx) => {
                                if (idx + 1 === origPos) {
                                    el.classList.add('selected');
                                }
                            });
                        }
                        return;
                    }
                } catch (err) {
                    console.error('Word alignment lookup failed:', err);
                }
            }

            // Fallback: show helpful message if no alignment found
            const isOT = OT_BOOKS.includes(this.currentBook);
            const language = isOT ? 'Hebrew' : 'Greek';

            this.selectedWord = {
                text: word,
                original: null,
                transliteration: null,
                strong_number: null,
                parsing: null,
                definition: this.showInterlinear
                    ? `Click on the ${language} word below to see Strong's definitions and word study details.`
                    : `Enable "Original Language" in the header to see ${language} words with Strong's numbers.`,
                occurrences: [],
                count: 0
            };
        },

        // Handle interlinear word click
        async handleInterlinearWordClick(word, event) {
            // Remove previous selection
            document.querySelectorAll('.word.selected, .interlinear-word.selected').forEach(el => {
                el.classList.remove('selected');
            });

            // Highlight this interlinear word
            const interlinearEl = event?.target?.closest('.interlinear-word');
            if (interlinearEl) {
                interlinearEl.classList.add('selected');
            }

            // Try to highlight the corresponding English word
            const verseBox = event?.target?.closest('.verse-box');
            if (verseBox) {
                const translation = (word.translation || '').toLowerCase().replace(/[.,;:!?'"()\[\]]/g, '');
                const englishWords = verseBox.querySelectorAll('.verse-text .word');

                // Skip common words that appear multiple times
                const skipWords = ['and', 'the', 'a', 'an', 'of', 'to', 'in', 'for', 'is', 'was', 'be', 'it', 'that', 'his', 'her', 'with', 'he', 'she', 'they', 'them', 'him', 'this', 'but', 'not', 'or', 'as', 'at', 'by', 'from', 'on', 'are', 'were', 'have', 'has', 'had', 'will', 'shall', 'who', 'which', 'their', 'you', 'your', 'my', 'me', 'i', 'we', 'us', 'our'];

                // Extract key words from translation (e.g., "in beginning" -> ["beginning"])
                const translationWords = translation.split(/\s+/).filter(w => w.length > 2 && !skipWords.includes(w));

                if (translationWords.length > 0) {
                    // Find best matching English word
                    let bestMatch = null;
                    let bestScore = 0;

                    englishWords.forEach(el => {
                        const englishWord = (el.dataset.word || el.textContent).toLowerCase()
                            .replace(/'s$/, '').replace(/s$/, '');
                        const englishBase = englishWord.replace(/ing$|ed$|ly$/, '');

                        // Skip common words
                        if (skipWords.includes(englishWord)) return;

                        let score = 0;
                        // Exact match with a translation word
                        if (translationWords.some(tw => tw === englishWord || tw === englishBase)) {
                            score = 100;
                        }
                        // Plural/singular match
                        else if (translationWords.some(tw => tw + 's' === englishWord || tw === englishWord + 's')) {
                            score = 90;
                        }

                        if (score > bestScore) {
                            bestScore = score;
                            bestMatch = el;
                        }
                    });

                    if (bestMatch && bestScore >= 90) {
                        bestMatch.classList.add('selected');
                    }
                }
            }

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
            this.showAllOccurrences = false;
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

        // Search - debounced live search
        handleSearchInput() {
            // Clear previous timer
            if (this.searchDebounceTimer) {
                clearTimeout(this.searchDebounceTimer);
            }

            // Reset selection when typing
            this.selectedResultIndex = -1;

            // Debounce search (300ms)
            this.searchDebounceTimer = setTimeout(() => {
                this.performSearch();
            }, 300);
        },

        async performSearch() {
            const query = this.searchQuery.trim();

            // Need at least 2 characters
            if (query.length < 2) {
                this.searchResults = [];
                this.searchPerformed = false;
                return;
            }

            this.searchLoading = true;
            this.searchPerformed = true;
            this.selectedResultIndex = -1;

            try {
                const response = await fetch(
                    `/api/search?q=${encodeURIComponent(query)}&scope=${this.searchScope}`
                );

                if (response.ok) {
                    const data = await response.json();
                    this.searchResults = data.results || [];
                    this.searchWordInfo = data.word_info || null;
                }
            } catch (err) {
                console.error('Search failed:', err);
                this.searchResults = [];
            } finally {
                this.searchLoading = false;
            }
        },

        // Handle keyboard navigation in search results
        handleSearchKeydown(event) {
            const resultCount = this.searchResults.length;

            switch (event.key) {
                case 'ArrowDown':
                    event.preventDefault();
                    if (resultCount > 0) {
                        this.selectedResultIndex = Math.min(
                            this.selectedResultIndex + 1,
                            resultCount - 1
                        );
                        this.scrollToSelectedResult();
                    }
                    break;
                case 'ArrowUp':
                    event.preventDefault();
                    if (resultCount > 0) {
                        this.selectedResultIndex = Math.max(
                            this.selectedResultIndex - 1,
                            0
                        );
                        this.scrollToSelectedResult();
                    }
                    break;
                case 'Enter':
                    if (this.selectedResultIndex >= 0 && this.selectedResultIndex < resultCount) {
                        event.preventDefault();
                        this.goToSearchResult(this.searchResults[this.selectedResultIndex]);
                    } else if (resultCount > 0) {
                        // If no selection, go to first result
                        event.preventDefault();
                        this.goToSearchResult(this.searchResults[0]);
                    }
                    break;
                case 'Escape':
                    this.showSearch = false;
                    break;
            }
        },

        scrollToSelectedResult() {
            this.$nextTick(() => {
                const selected = document.querySelector('.search-result.selected');
                if (selected) {
                    selected.scrollIntoView({ block: 'nearest' });
                }
            });
        },

        // Get grouped search results
        getGroupedResults() {
            const groups = {
                verse: [],
                commentary: []
            };
            for (const result of this.searchResults) {
                if (result.type === 'verse') {
                    groups.verse.push(result);
                } else if (result.type === 'commentary') {
                    groups.commentary.push(result);
                }
            }
            return groups;
        },

        // Go to search result
        goToSearchResult(result) {
            if (result.book && result.chapter) {
                const ref = result.verse
                    ? `${result.book} ${result.chapter}:${result.verse}`
                    : `${result.book} ${result.chapter}`;
                this.loadReference(ref);
                this.showSearch = false;
                this.searchQuery = '';
                this.searchResults = [];
                this.searchPerformed = false;
            }
        },

        // Reset search state when opening
        openSearch() {
            this.showSearch = true;
            this.searchResults = [];
            this.searchWordInfo = null;
            this.searchPerformed = false;
            this.selectedResultIndex = -1;
            this.$nextTick(() => this.$refs.searchInput?.focus());
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
