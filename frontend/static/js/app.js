/**
 * BibleMVP - Main Application
 * A free, open-source Bible study platform.
 */

// All Bible books for autocomplete
const BIBLE_BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
    "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles",
    "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
    "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah",
    "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
    "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans",
    "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews",
    "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John",
    "Jude", "Revelation"
];

function bibleApp() {
    return {
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

        // Initialize
        async init() {
            // Load dark mode preference
            this.darkMode = localStorage.getItem('darkMode') === 'true';

            // Load notes from IndexedDB
            await this.loadNotes();

            // Check URL for initial reference
            const urlParams = new URLSearchParams(window.location.search);
            const ref = urlParams.get('ref');
            if (ref) {
                this.referenceInput = ref;
                await this.loadPassage();
            }
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

                // Update URL
                window.history.replaceState({}, '', `?ref=${encodeURIComponent(this.referenceInput)}`);

                // Load commentary
                await this.loadCommentary();

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
            // If clicked on a word, handle word click instead
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
            window.history.replaceState({}, '', `?ref=${encodeURIComponent(this.referenceInput)}`);

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

        // Show verse preview on hover
        async previewVerse(ref, event) {
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

        // Format verse text with clickable words
        formatVerseText(text) {
            // For now, just wrap each word in a span
            // Later this will use interlinear data with Strong's numbers
            return text.split(/\s+/).map((word, i) => {
                const cleanWord = word.replace(/[.,;:!?'"()]/g, '');
                const punct = word.replace(cleanWord, '');
                return `<span class="word" data-word="${cleanWord}">${cleanWord}</span>${punct}`;
            }).join(' ');
        },

        // Handle word click
        async handleWordClick(event) {
            const wordEl = event.target.closest('.word');
            if (!wordEl) return;

            const word = wordEl.dataset.word;
            if (!word) return;

            // Remove previous selection
            document.querySelectorAll('.word.selected').forEach(el => {
                el.classList.remove('selected');
            });
            wordEl.classList.add('selected');

            // In a full implementation, this would look up Strong's number
            // For now, show a placeholder
            this.selectedWord = {
                text: word,
                original: '---',
                transliteration: '---',
                strong_number: '---',
                parsing: 'Word lookup not yet implemented',
                definition: 'Interlinear data will be loaded in a future update.',
                occurrences: [],
                count: 0
            };
        },

        // Load word details by Strong's number
        async loadWordDetails(strongNumber) {
            try {
                const response = await fetch(`/api/word/${strongNumber}`);
                if (response.ok) {
                    const data = await response.json();
                    this.selectedWord = {
                        ...data.word,
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

        async saveNote() {
            if (!this.currentNote.trim() || !this.currentReference) return;

            const note = {
                id: Date.now(),
                reference: this.currentReference,
                content: this.currentNote,
                created_at: new Date().toISOString()
            };

            this.notes.unshift(note);
            localStorage.setItem('bible-notes', JSON.stringify(this.notes));
            this.currentNote = '';
        },

        // Format date
        formatDate(isoString) {
            return new Date(isoString).toLocaleDateString();
        },

        // Check if a verse should be highlighted
        isVerseHighlighted(verseNum) {
            return this.highlightedVerses.includes(verseNum);
        }
    };
}
