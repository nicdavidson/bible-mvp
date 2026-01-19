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

// Book abbreviation mappings for linkifying Bible references
const BOOK_ABBREVS = {
    // Old Testament
    'Gen': 'Genesis', 'Ge': 'Genesis', 'Gn': 'Genesis',
    'Exod': 'Exodus', 'Exo': 'Exodus', 'Ex': 'Exodus',
    'Lev': 'Leviticus', 'Le': 'Leviticus', 'Lv': 'Leviticus',
    'Num': 'Numbers', 'Nu': 'Numbers', 'Nm': 'Numbers',
    'Deut': 'Deuteronomy', 'Deu': 'Deuteronomy', 'De': 'Deuteronomy', 'Dt': 'Deuteronomy',
    'Josh': 'Joshua', 'Jos': 'Joshua', 'Jsh': 'Joshua',
    'Judg': 'Judges', 'Jdg': 'Judges', 'Jg': 'Judges',
    'Rth': 'Ruth', 'Ru': 'Ruth',
    '1Sam': '1 Samuel', '1Sa': '1 Samuel', '1 Sam': '1 Samuel', '1 Sa': '1 Samuel',
    '2Sam': '2 Samuel', '2Sa': '2 Samuel', '2 Sam': '2 Samuel', '2 Sa': '2 Samuel',
    '1Kgs': '1 Kings', '1Ki': '1 Kings', '1 Kings': '1 Kings', '1 Ki': '1 Kings',
    '2Kgs': '2 Kings', '2Ki': '2 Kings', '2 Kings': '2 Kings', '2 Ki': '2 Kings',
    '1Chr': '1 Chronicles', '1Ch': '1 Chronicles', '1 Chr': '1 Chronicles', '1 Chron': '1 Chronicles',
    '2Chr': '2 Chronicles', '2Ch': '2 Chronicles', '2 Chr': '2 Chronicles', '2 Chron': '2 Chronicles',
    'Ezr': 'Ezra',
    'Neh': 'Nehemiah', 'Ne': 'Nehemiah',
    'Esth': 'Esther', 'Est': 'Esther', 'Es': 'Esther',
    'Psa': 'Psalms', 'Ps': 'Psalms', 'Psalm': 'Psalms',
    'Prov': 'Proverbs', 'Pro': 'Proverbs', 'Pr': 'Proverbs',
    'Eccl': 'Ecclesiastes', 'Ecc': 'Ecclesiastes', 'Ec': 'Ecclesiastes',
    'Song': 'Song of Solomon', 'Sol': 'Song of Solomon', 'So': 'Song of Solomon', 'SoS': 'Song of Solomon',
    'Isa': 'Isaiah', 'Is': 'Isaiah',
    'Jer': 'Jeremiah', 'Je': 'Jeremiah',
    'Lam': 'Lamentations', 'La': 'Lamentations',
    'Ezek': 'Ezekiel', 'Eze': 'Ezekiel', 'Ezk': 'Ezekiel',
    'Dan': 'Daniel', 'Da': 'Daniel', 'Dn': 'Daniel',
    'Hos': 'Hosea', 'Ho': 'Hosea',
    'Joe': 'Joel', 'Jl': 'Joel',
    'Am': 'Amos',
    'Obad': 'Obadiah', 'Oba': 'Obadiah', 'Ob': 'Obadiah',
    'Jon': 'Jonah', 'Jnh': 'Jonah',
    'Mic': 'Micah', 'Mi': 'Micah',
    'Nah': 'Nahum', 'Na': 'Nahum',
    'Hab': 'Habakkuk',
    'Zeph': 'Zephaniah', 'Zep': 'Zephaniah',
    'Hag': 'Haggai',
    'Zech': 'Zechariah', 'Zec': 'Zechariah',
    'Mal': 'Malachi',
    // New Testament
    'Mat': 'Matthew', 'Matt': 'Matthew', 'Mt': 'Matthew',
    'Mar': 'Mark', 'Mk': 'Mark', 'Mr': 'Mark',
    'Luk': 'Luke', 'Lk': 'Luke', 'Lu': 'Luke',
    'Joh': 'John', 'Jn': 'John',
    'Act': 'Acts', 'Ac': 'Acts',
    'Rom': 'Romans', 'Ro': 'Romans', 'Rm': 'Romans',
    '1Cor': '1 Corinthians', '1Co': '1 Corinthians', '1 Cor': '1 Corinthians',
    '2Cor': '2 Corinthians', '2Co': '2 Corinthians', '2 Cor': '2 Corinthians',
    'Gal': 'Galatians', 'Ga': 'Galatians',
    'Eph': 'Ephesians',
    'Phil': 'Philippians', 'Php': 'Philippians',
    'Col': 'Colossians',
    '1Thes': '1 Thessalonians', '1Th': '1 Thessalonians', '1 Thes': '1 Thessalonians', '1 Thess': '1 Thessalonians',
    '2Thes': '2 Thessalonians', '2Th': '2 Thessalonians', '2 Thes': '2 Thessalonians', '2 Thess': '2 Thessalonians',
    '1Tim': '1 Timothy', '1Ti': '1 Timothy', '1 Tim': '1 Timothy',
    '2Tim': '2 Timothy', '2Ti': '2 Timothy', '2 Tim': '2 Timothy',
    'Tit': 'Titus',
    'Phm': 'Philemon', 'Philem': 'Philemon', 'Phlm': 'Philemon',
    'Heb': 'Hebrews',
    'Jam': 'James', 'Jas': 'James',
    '1Pet': '1 Peter', '1Pe': '1 Peter', '1 Pet': '1 Peter', '1 Pt': '1 Peter',
    '2Pet': '2 Peter', '2Pe': '2 Peter', '2 Pet': '2 Peter', '2 Pt': '2 Peter',
    '1Joh': '1 John', '1Jn': '1 John', '1 Joh': '1 John', '1 Jn': '1 John',
    '2Joh': '2 John', '2Jn': '2 John', '2 Joh': '2 John', '2 Jn': '2 John',
    '3Joh': '3 John', '3Jn': '3 John', '3 Joh': '3 John', '3 Jn': '3 John',
    'Jud': 'Jude',
    'Rev': 'Revelation', 'Re': 'Revelation'
};

// Add full book names to BOOK_ABBREVS for matching
BIBLE_BOOKS.forEach(book => {
    BOOK_ABBREVS[book] = book;
});

// Book genre categories for color-coding
const BOOK_GENRES = {
    'law': ['Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy'],
    'history': ['Joshua', 'Judges', 'Ruth', '1 Samuel', '2 Samuel', '1 Kings', '2 Kings',
                '1 Chronicles', '2 Chronicles', 'Ezra', 'Nehemiah', 'Esther', 'Acts'],
    'wisdom': ['Job', 'Psalms', 'Proverbs', 'Ecclesiastes', 'Song of Solomon'],
    'major-prophets': ['Isaiah', 'Jeremiah', 'Lamentations', 'Ezekiel', 'Daniel'],
    'minor-prophets': ['Hosea', 'Joel', 'Amos', 'Obadiah', 'Jonah', 'Micah', 'Nahum',
                       'Habakkuk', 'Zephaniah', 'Haggai', 'Zechariah', 'Malachi'],
    'gospels': ['Matthew', 'Mark', 'Luke', 'John'],
    'pauline': ['Romans', '1 Corinthians', '2 Corinthians', 'Galatians', 'Ephesians',
                'Philippians', 'Colossians', '1 Thessalonians', '2 Thessalonians',
                '1 Timothy', '2 Timothy', 'Titus', 'Philemon'],
    'general-epistles': ['Hebrews', 'James', '1 Peter', '2 Peter', '1 John', '2 John', '3 John', 'Jude'],
    'apocalyptic': ['Revelation']
};

// Default genre colors
const DEFAULT_GENRE_COLORS = {
    'law': '#3b82f6',           // Blue
    'history': '#22c55e',        // Green
    'wisdom': '#eab308',         // Gold/Amber
    'major-prophets': '#8b5cf6', // Purple
    'minor-prophets': '#14b8a6', // Teal
    'gospels': '#ef4444',        // Red
    'pauline': '#f97316',        // Orange
    'general-epistles': '#f87171', // Coral
    'apocalyptic': '#7c3aed'     // Deep Purple
};

// Genre display names
const GENRE_NAMES = {
    'law': 'Law/Torah',
    'history': 'History',
    'wisdom': 'Wisdom/Poetry',
    'major-prophets': 'Major Prophets',
    'minor-prophets': 'Minor Prophets',
    'gospels': 'Gospels',
    'pauline': 'Pauline Epistles',
    'general-epistles': 'General Epistles',
    'apocalyptic': 'Apocalyptic'
};

// Helper to get genre for a book
function getBookGenre(book) {
    for (const [genre, books] of Object.entries(BOOK_GENRES)) {
        if (books.includes(book)) {
            return genre;
        }
    }
    return null;
}

// Build regex pattern for matching Bible references
const BOOK_PATTERN = Object.keys(BOOK_ABBREVS)
    .sort((a, b) => b.length - a.length)  // Longer matches first
    .map(k => k.replace(/\s/g, '\\s?'))   // Allow optional space in "1 Sam" etc.
    .join('|');

const BIBLE_REF_REGEX = new RegExp(
    `\\b(${BOOK_PATTERN})\\s*(\\d+):(\\d+)(?:-(\\d+))?\\b`,
    'gi'
);

// Function to linkify Bible references in text
function linkifyBibleReferences(text) {
    if (!text) return '';

    return text.replace(BIBLE_REF_REGEX, (match, bookPart, chapter, verseStart, verseEnd) => {
        // Normalize the book name
        const normalizedBook = bookPart.replace(/\s+/g, ' ').trim();
        const bookKey = Object.keys(BOOK_ABBREVS).find(
            k => k.toLowerCase().replace(/\s+/g, '') === normalizedBook.toLowerCase().replace(/\s+/g, '')
        );
        const fullBook = bookKey ? BOOK_ABBREVS[bookKey] : null;

        if (!fullBook) return match;  // Return unchanged if not a valid book

        // Build reference string
        const ref = verseEnd
            ? `${fullBook} ${chapter}:${verseStart}-${verseEnd}`
            : `${fullBook} ${chapter}:${verseStart}`;

        // Return clickable link
        return `<a href="#" class="note-ref" data-ref="${ref}">${match}</a>`;
    });
}

function bibleApp() {
    return {
        // Book lists for selector
        otBooks: OT_BOOKS,
        ntBooks: NT_BOOKS,

        // State
        referenceInput: '',
        translation: 'BSB',
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

        // Settings state
        showSettings: false,
        settingsTab: 'general',
        defaultTranslation: 'BSB',
        defaultShowInterlinear: false,
        showRedLetter: true,  // Red letter display for God/Jesus speech
        genreColors: { ...DEFAULT_GENRE_COLORS },  // User-customizable genre colors

        // Speaker verses for red letter display
        speakerVerses: [],  // Verse numbers with divine speech

        // Auth state
        authUser: null,
        authLoading: false,
        authError: null,
        authSuccess: null,
        authMode: 'signin',  // 'signin' or 'signup'
        authEmail: '',
        authPassword: '',
        authPasswordConfirm: '',

        // Tag state
        tags: [],  // User's tags: { id, name, color, sortOrder, synced }
        noteTags: {},  // Map of noteId -> [tagId, ...]
        editingTag: null,  // Tag being edited in settings
        newTagName: '',
        newTagColor: '#ef4444',
        tagColors: [
            '#ef4444', '#f97316', '#eab308', '#22c55e',
            '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899'
        ],

        // Multi-verse selection state
        noteEditMode: false,  // When true, taps select verses instead of word lookup
        selectedVerses: [],  // Verses selected for note (numbers)
        pendingNoteTags: [],  // Tag IDs to apply when creating a new note

        // Note editing state
        editingNoteId: null,  // ID of note being edited
        editingNoteContent: '',  // Content of note being edited

        // Scroll-based active verse tracking (for chapter-wide content display)
        scrollActiveVerse: null,  // Verse number most visible in viewport
        scrollObserver: null,  // IntersectionObserver instance

        // Devotional state (kept for offline downloads)
        devotional: { entries: [], month: 0, day: 0 },
        loadingDevotional: false,
        devotionalMonth: new Date().getMonth() + 1,
        devotionalDay: new Date().getDate(),

        // Reading Plan state
        showReadingPlan: false,
        readingPlans: [],  // Available plans
        currentPlan: null,  // Active plan with full data
        planProgress: {},  // { planId: { startDate, completedDays: [1,2,3...], userPlanId?: number } }
        planProgressSynced: false,  // Whether plan progress has been synced from Supabase
        planLoading: false,
        planDay: 1,  // Currently viewing day
        planReadingMode: false,  // True when reading a plan (shows all passages together)
        planReadings: [],  // Passages loaded for current plan day
        combinedPlanReading: false,  // True when showing plan readings in main reader format
        planReadingSections: [],  // Section info for combined reading: [{label, reference, startIndex}]
        planReadingChapters: [],  // Chapters being read in combined mode: [{book, chapter}]
        wasInPlanReading: false,  // True when user navigated away from plan reading (for "return" button)
        combinedCrossRefs: [],  // Store all cross-refs for combined reading (to restore after verse deselect)
        combinedCommentary: [],  // Store all commentary for combined reading (to restore after verse deselect)
        combinedNotes: [],  // Store notes for combined reading chapters

        // Commentary grouping state
        expandedCommentarySources: {},  // { source: boolean }
        expandedCommentaryChapters: {},  // { chapterRef: boolean } for combined plan reading

        // Offline state
        isOnline: navigator.onLine,
        forcedOffline: false,  // Manual offline mode for privacy/security
        autoCacheEnabled: true,
        offlineStats: {
            chapters: 0,
            verses: 0,
            lexicon: false,
            estimatedSize: 0
        },
        downloadOptions: {
            lexicon: false,
            currentBook: false
        },
        downloadSelections: {
            translations: {
                BSB: false,
                WEB: false,
                KJV: false
            },
            lexicon: false,
            commentaryMH: false,  // Matthew Henry
            commentaryJG: false,  // John Gill
            crossRefs: false,
            devotionalSpurgeon: false
        },
        downloadProgress: {
            active: false,
            label: '',
            percent: 0,
            status: ''
        },
        toasts: [],

        // Feedback/bug report state
        feedbackCategory: 'bug',  // 'bug', 'accuracy', 'feature'
        feedbackDescription: '',
        feedbackVerseRef: '',
        feedbackTranslation: '',
        feedbackAccuracyType: '',
        feedbackScreenshot: null,  // File object
        feedbackScreenshotPreview: '',  // Data URL for preview
        feedbackSubmitting: false,
        feedbackSuccess: false,
        feedbackError: null,

        // Initialize
        async init() {
            // Detect touch device
            this.isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

            // Load preferences from localStorage
            this.darkMode = localStorage.getItem('darkMode') === 'true';
            this.defaultTranslation = localStorage.getItem('defaultTranslation') || 'BSB';
            this.translation = this.defaultTranslation;
            this.defaultShowInterlinear = localStorage.getItem('defaultShowInterlinear') === 'true';
            this.showInterlinear = this.defaultShowInterlinear;
            this.autoCacheEnabled = localStorage.getItem('autoCacheEnabled') !== 'false';
            this.forcedOffline = localStorage.getItem('forcedOffline') === 'true';
            this.showRedLetter = localStorage.getItem('showRedLetter') !== 'false';  // Default true

            // Load genre colors from localStorage
            const savedGenreColors = localStorage.getItem('genreColors');
            if (savedGenreColors) {
                try {
                    this.genreColors = { ...DEFAULT_GENRE_COLORS, ...JSON.parse(savedGenreColors) };
                } catch (e) {
                    this.genreColors = { ...DEFAULT_GENRE_COLORS };
                }
            }
            this.applyGenreColors();

            // If forced offline, reflect that in isOnline
            if (this.forcedOffline) {
                this.isOnline = false;
            }

            // Setup online/offline listeners
            window.addEventListener('online', () => {
                if (!this.forcedOffline) {
                    this.isOnline = true;
                    this.showToast('Back online', 'success');
                }
            });
            window.addEventListener('offline', () => {
                this.isOnline = false;
                this.showToast('You are offline - cached content available', 'info');
            });

            // Load offline stats
            await this.updateOfflineStats();

            // Initialize auth and load notes/tags
            await this.initAuth();
            await this.loadNotes();
            await this.loadTags();

            // Check URL for initial reference - support plan URLs, path-based refs, and ?ref= formats
            const planURL = this.parsePlanURL();
            if (planURL) {
                // Restore reading plan state from URL
                await this.restorePlanFromURL(planURL.planId, planURL.day);
            } else {
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
            }

            // Handle browser back/forward
            window.addEventListener('popstate', () => {
                const planURL = this.parsePlanURL();
                if (planURL) {
                    this.restorePlanFromURL(planURL.planId, planURL.day);
                } else {
                    const pathRef = this.parsePathReference();
                    if (pathRef) {
                        // Exit plan reading mode if navigating to a regular passage
                        if (this.combinedPlanReading) {
                            this.combinedPlanReading = false;
                            this.planReadingMode = false;
                        }
                        this.referenceInput = pathRef;
                        this.loadPassage();
                    }
                }
            });

            // Setup keyboard shortcuts
            this.setupKeyboardShortcuts();

            // Setup scroll-based verse tracking (desktop only)
            this.setupScrollObserver();

            // Load reading plan progress from localStorage
            this.loadPlanProgress();
        },

        // Setup IntersectionObserver for scroll-based active verse tracking
        setupScrollObserver() {
            // Only on desktop - mobile uses tap to select
            if (this.isTouchDevice) return;

            this.scrollObserver = new IntersectionObserver(
                (entries) => {
                    // Find the verse with highest visibility
                    let bestEntry = null;
                    let bestRatio = 0;

                    for (const entry of entries) {
                        if (entry.isIntersecting && entry.intersectionRatio > bestRatio) {
                            bestRatio = entry.intersectionRatio;
                            bestEntry = entry;
                        }
                    }

                    if (bestEntry) {
                        const verseNum = parseInt(bestEntry.target.id.replace('verse-', ''), 10);
                        if (verseNum && verseNum !== this.scrollActiveVerse) {
                            this.scrollActiveVerse = verseNum;
                        }
                    }
                },
                {
                    root: null,  // viewport
                    rootMargin: '-20% 0px -60% 0px',  // Focus on upper-middle of viewport
                    threshold: [0, 0.25, 0.5, 0.75, 1]
                }
            );
        },

        // Observe verse elements after they're rendered
        observeVerses() {
            if (!this.scrollObserver) return;

            // Disconnect previous observations
            this.scrollObserver.disconnect();

            // Observe all verse boxes after a tick for DOM to update
            this.$nextTick(() => {
                const verseBoxes = document.querySelectorAll('.verse-box');
                verseBoxes.forEach(box => this.scrollObserver.observe(box));

                // Set initial active verse
                if (this.highlightedVerses.length > 0) {
                    this.scrollActiveVerse = this.highlightedVerses[0];
                } else if (this.verses.length > 0) {
                    this.scrollActiveVerse = this.verses[0].verse;
                }
            });
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
                        this.showSettings = false;
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
                        this.showSettings = false;
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
                        this.openSettings('shortcuts');
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

        // Parse plan URL (e.g., /plan/chronological/45)
        parsePlanURL() {
            const path = window.location.pathname;
            const match = path.match(/^\/plan\/([^\/]+)\/(\d+)$/);
            if (match) {
                return {
                    planId: decodeURIComponent(match[1]),
                    day: parseInt(match[2])
                };
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
            const ref = `${this.pickerSelectedBook} ${chapter}`;
            this.showBookPicker = false;
            this.pickerSelectedBook = null;
            // Use loadReference to properly handle plan reading state
            this.loadReference(ref);
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
                this.speakerVerses = data.speaker_verses || [];

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

                // Setup scroll-based verse tracking
                this.observeVerses();

            } catch (err) {
                this.error = err.message;
                this.verses = [];
            } finally {
                this.loading = false;
            }
        },

        // Load a reference (from cross-ref click, etc.)
        async loadReference(ref) {
            // Exit combined plan reading mode when navigating to a different reference
            // but remember we were in it so user can return
            if (this.combinedPlanReading) {
                this.wasInPlanReading = true;
                this.combinedPlanReading = false;
                this.planReadingSections = [];
                this.planReadingChapters = [];
            }
            this.referenceInput = ref;
            await this.loadPassage();
        },

        // Load commentary for current chapter (always full chapter for browsing)
        async loadCommentary() {
            if (!this.currentBook || !this.currentChapter) {
                this.commentary = [];
                return;
            }

            this.loadingCommentary = true;
            try {
                // Always request full chapter commentary for chapter-wide browsing
                const chapterRef = `${this.currentBook} ${this.currentChapter}`;
                const response = await fetch(
                    `/api/passage/${encodeURIComponent(chapterRef)}/commentary`
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

        // Check if a commentary entry applies to the active verse
        commentaryMatchesActiveVerse(entry) {
            const activeVerse = this.getActiveVerse();
            if (!activeVerse) return true;  // If no active verse, all match
            const start = entry.reference_start || 1;
            const end = entry.reference_end || start;
            return activeVerse >= start && activeVerse <= end;
        },

        // Select a verse from a verse reference (e.g., clicking "v. 3" in commentary)
        selectVerseFromRef(verseNum) {
            this.highlightedVerses = [verseNum];
            this.scrollActiveVerse = verseNum;

            // Scroll to the verse
            this.$nextTick(() => {
                const verseEl = document.getElementById(`verse-${verseNum}`);
                if (verseEl) {
                    verseEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            });
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
                // Go to previous chapter in same book
                this.referenceInput = `${this.currentBook} ${this.currentChapter - 1}`;
                this.loadPassage();
            } else {
                // At chapter 1, go to last chapter of previous book
                const bookIndex = BIBLE_BOOKS.indexOf(this.currentBook);
                if (bookIndex > 0) {
                    const prevBook = BIBLE_BOOKS[bookIndex - 1];
                    const lastChapter = BOOK_CHAPTERS[prevBook] || 1;
                    this.referenceInput = `${prevBook} ${lastChapter}`;
                    this.loadPassage();
                }
            }
        },

        // Navigate to next chapter
        nextChapter() {
            const maxChapter = BOOK_CHAPTERS[this.currentBook] || 1;
            if (this.currentChapter < maxChapter) {
                // Go to next chapter in same book
                this.referenceInput = `${this.currentBook} ${this.currentChapter + 1}`;
                this.loadPassage();
            } else {
                // At last chapter, go to first chapter of next book
                const bookIndex = BIBLE_BOOKS.indexOf(this.currentBook);
                if (bookIndex < BIBLE_BOOKS.length - 1) {
                    const nextBook = BIBLE_BOOKS[bookIndex + 1];
                    this.referenceInput = `${nextBook} 1`;
                    this.loadPassage();
                }
            }
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

            // Commentary already loaded for full chapter - just update active verse display
            // (no reload needed since we have all chapter commentary)

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
        async handleVerseBoxClick(event, verseNum, verseIdx) {
            // In note edit mode, handle verse selection for multi-verse notes
            if (this.noteEditMode) {
                this.handleVerseSelection(verseNum, event);
                return;
            }

            // On touch devices, always select the verse (don't trigger word lookup)
            // Word lookup is a power feature better suited for desktop
            if (this.isTouchDevice) {
                await this.selectVerse(verseNum, verseIdx);
                return;
            }

            // On desktop, if clicked on a word, handle word click instead
            const wordEl = event.target.closest('.word');
            if (wordEl) {
                this.handleWordClick(event);
                return;
            }

            // Otherwise select the verse
            await this.selectVerse(verseNum, verseIdx);
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

        // Group commentary entries by source
        getGroupedCommentary() {
            const grouped = {};
            for (const entry of this.commentary) {
                const source = entry.source || 'Unknown';
                if (!grouped[source]) {
                    grouped[source] = [];
                }
                grouped[source].push(entry);
            }
            return grouped;
        },

        // Group commentary by chapter first, then by source (for combined plan reading)
        getGroupedCommentaryByChapter() {
            const byChapter = {};
            for (const entry of this.commentary) {
                const chapterKey = entry._sourceRef || 'Unknown';
                if (!byChapter[chapterKey]) {
                    byChapter[chapterKey] = {};
                }
                const source = entry.source || 'Unknown';
                if (!byChapter[chapterKey][source]) {
                    byChapter[chapterKey][source] = [];
                }
                byChapter[chapterKey][source].push(entry);
            }
            return byChapter;
        },

        // Get list of chapter keys in order they appear in the reading
        getCommentaryChapterKeys() {
            const seen = new Set();
            const keys = [];
            for (const entry of this.commentary) {
                const key = entry._sourceRef || 'Unknown';
                if (!seen.has(key)) {
                    seen.add(key);
                    keys.push(key);
                }
            }
            return keys;
        },

        // Check if a commentary chapter is expanded (in combined mode)
        isCommentaryChapterExpanded(chapterKey) {
            // If explicitly set, use that value
            if (this.expandedCommentaryChapters && this.expandedCommentaryChapters[chapterKey] !== undefined) {
                return this.expandedCommentaryChapters[chapterKey];
            }
            // By default, only expand first chapter
            return this.getCommentaryChapterKeys()[0] === chapterKey;
        },

        // Toggle a commentary chapter's expanded state
        toggleCommentaryChapter(chapterKey) {
            if (!this.expandedCommentaryChapters) {
                this.expandedCommentaryChapters = {};
            }
            // If not set, get current default state and toggle
            const current = this.isCommentaryChapterExpanded(chapterKey);
            this.expandedCommentaryChapters[chapterKey] = !current;
        },

        // Check if a commentary source is expanded
        isCommentarySourceExpanded(source) {
            return this.expandedCommentarySources[source] === true;
        },

        // Toggle a commentary source's expanded state
        toggleCommentarySource(source) {
            this.expandedCommentarySources[source] = !this.expandedCommentarySources[source];
        },

        // Get a preview of the commentary (first 1-2 sentences)
        getCommentaryPreview(entries) {
            if (!entries || entries.length === 0) return '';
            // Get the first entry's content, strip HTML, and take first ~150 chars
            const firstContent = entries[0].content || '';
            const plainText = firstContent.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
            // Find a good break point (end of sentence or word boundary)
            if (plainText.length <= 150) return plainText;
            const truncated = plainText.substring(0, 150);
            const lastPeriod = truncated.lastIndexOf('.');
            const lastSpace = truncated.lastIndexOf(' ');
            const breakPoint = lastPeriod > 100 ? lastPeriod + 1 : lastSpace > 0 ? lastSpace : 150;
            return truncated.substring(0, breakPoint).trim() + '...';
        },

        // Select a specific verse (click on verse box) - toggles off if already selected
        // verseIdx is optional and used in combined mode to identify the exact verse
        async selectVerse(verseNum, verseIdx) {
            // If this verse is already the only highlighted verse, deselect it
            if (this.highlightedVerses.length === 1 && this.highlightedVerses[0] === verseNum) {
                this.highlightedVerses = [];
                this.selectedWord = null;

                // Remove previous word selections
                document.querySelectorAll('.word.selected').forEach(el => {
                    el.classList.remove('selected');
                });

                // In combined mode, restore the full combined data
                if (this.combinedPlanReading) {
                    this.currentBook = null;
                    this.currentChapter = null;
                    this.currentReference = null;
                    // Restore combined cross-refs and commentary
                    this.crossRefs = this.combinedCrossRefs;
                    this.commentary = this.combinedCommentary;
                } else if (this.currentBook && this.currentChapter) {
                    // Update reference display to chapter level
                    this.currentReference = `${this.currentBook} ${this.currentChapter}`;
                    this.referenceInput = this.currentReference;
                    this.updateURL();
                }
                return;
            }

            // Update highlighted verses without reloading the whole passage
            this.highlightedVerses = [verseNum];
            this.selectedWord = null; // Clear word selection

            // Remove previous word selections
            document.querySelectorAll('.word.selected').forEach(el => {
                el.classList.remove('selected');
            });

            // In combined plan reading mode, use the verse index to get book/chapter context
            if (this.combinedPlanReading && verseIdx !== undefined) {
                const verse = this.verses[verseIdx];
                if (verse && verse._book && verse._chapter) {
                    this.currentBook = verse._book;
                    this.currentChapter = verse._chapter;
                    this.currentReference = `${verse._book} ${verse._chapter}:${verseNum}`;
                    this.referenceInput = this.currentReference;

                    // Load cross-refs and commentary for just this verse
                    await this.loadCrossRefs();
                    await this.loadCommentary();
                }
                return;
            }

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
        hasInterlinear(verseNum, verseIdx) {
            if (this.combinedPlanReading && verseIdx !== undefined) {
                const verse = this.verses[verseIdx];
                if (verse && verse._book && verse._chapter) {
                    const key = `${verse._book}|${verse._chapter}|${verseNum}`;
                    return !!this.interlinearData[key];
                }
            }
            return !!this.interlinearData[verseNum];
        },

        // Get interlinear words for a verse
        getInterlinearWords(verseNum, verseIdx) {
            if (this.combinedPlanReading && verseIdx !== undefined) {
                const verse = this.verses[verseIdx];
                if (verse && verse._book && verse._chapter) {
                    const key = `${verse._book}|${verse._chapter}|${verseNum}`;
                    return this.interlinearData[key]?.words || [];
                }
            }
            return this.interlinearData[verseNum]?.words || [];
        },

        // Get language for interlinear display
        getInterlinearLanguage(verseNum, verseIdx) {
            if (this.combinedPlanReading && verseIdx !== undefined) {
                const verse = this.verses[verseIdx];
                if (verse && verse._book && verse._chapter) {
                    const key = `${verse._book}|${verse._chapter}|${verseNum}`;
                    return this.interlinearData[key]?.language || 'unknown';
                }
            }
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
                // Extract leading punctuation, the word, and trailing punctuation
                const match = word.match(/^([.,;:!?'"()—]*)([a-zA-Z'-]+)([.,;:!?'"()—]*)$/);
                if (!match) {
                    // Pure punctuation or other - return as-is
                    return word;
                }
                const [, leadingPunct, cleanWord, trailingPunct] = match;
                if (cleanWord) wordPosition++;
                return `${leadingPunct}<span class="word" data-word="${cleanWord}" data-position="${wordPosition}">${cleanWord}</span>${trailingPunct}`;
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

        // Save dark mode preference (from settings)
        saveDarkMode() {
            localStorage.setItem('darkMode', this.darkMode);
        },

        // Save default translation preference
        saveDefaultTranslation() {
            localStorage.setItem('defaultTranslation', this.defaultTranslation);
            // Also update current translation
            this.translation = this.defaultTranslation;
        },

        // Save interlinear preference
        saveInterlinearPref() {
            localStorage.setItem('defaultShowInterlinear', this.defaultShowInterlinear);
        },

        // Save red letter preference
        saveRedLetterPref() {
            localStorage.setItem('showRedLetter', this.showRedLetter);
        },

        // Check if verse has divine speech (for red letter display)
        isRedLetterVerse(verseNum) {
            return this.showRedLetter && this.speakerVerses.includes(verseNum);
        },

        // Save auto-cache preference
        saveAutoCachePref() {
            localStorage.setItem('autoCacheEnabled', this.autoCacheEnabled);
        },

        // Save genre color preference
        saveGenreColor(genre) {
            localStorage.setItem('genreColors', JSON.stringify(this.genreColors));
            this.applyGenreColors();
        },

        // Apply genre colors as CSS custom properties
        applyGenreColors() {
            const root = document.documentElement;
            for (const [genre, color] of Object.entries(this.genreColors)) {
                root.style.setProperty(`--genre-${genre}`, color);
            }
        },

        // Reset genre colors to defaults
        resetGenreColors() {
            this.genreColors = { ...DEFAULT_GENRE_COLORS };
            localStorage.setItem('genreColors', JSON.stringify(this.genreColors));
            this.applyGenreColors();
        },

        // Get book genre
        getBookGenre(book) {
            return getBookGenre(book);
        },

        // Open settings modal, optionally to a specific tab
        openSettings(tab = 'general') {
            this.settingsTab = tab;
            this.showSettings = true;
            // Refresh offline stats when opening settings
            if (tab === 'offline') {
                this.updateOfflineStats();
            }
        },

        // ========== Feedback/Bug Report Functions ==========

        // Handle screenshot file selection
        handleScreenshotSelect(event) {
            const file = event.target.files[0];
            if (file) {
                this.feedbackScreenshot = file;
                // Create preview URL
                const reader = new FileReader();
                reader.onload = (e) => {
                    this.feedbackScreenshotPreview = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        },

        // Clear screenshot
        clearScreenshot() {
            this.feedbackScreenshot = null;
            this.feedbackScreenshotPreview = '';
        },

        // Reset feedback form
        resetFeedbackForm() {
            this.feedbackCategory = 'bug';
            this.feedbackDescription = '';
            this.feedbackVerseRef = '';
            this.feedbackTranslation = '';
            this.feedbackAccuracyType = '';
            this.feedbackScreenshot = null;
            this.feedbackScreenshotPreview = '';
            this.feedbackSubmitting = false;
            this.feedbackSuccess = false;
            this.feedbackError = null;
        },

        // Submit feedback
        async submitFeedback() {
            if (!this.authUser) {
                this.feedbackError = 'Please sign in to submit feedback';
                return;
            }

            if (!this.feedbackDescription.trim()) {
                this.feedbackError = 'Please provide a description';
                return;
            }

            this.feedbackSubmitting = true;
            this.feedbackError = null;

            try {
                let screenshotPath = null;

                // Upload screenshot if present (for bugs)
                if (this.feedbackCategory === 'bug' && this.feedbackScreenshot) {
                    try {
                        screenshotPath = await SupabaseAuth.uploadBugScreenshot(this.feedbackScreenshot);
                    } catch (err) {
                        console.warn('Screenshot upload failed, continuing without:', err);
                        // Continue without screenshot - don't fail the whole submission
                    }
                }

                // Build report object
                const report = {
                    category: this.feedbackCategory,
                    description: this.feedbackDescription.trim(),
                    screenshotPath: screenshotPath,
                    currentUrl: window.location.href
                };

                // Add accuracy-specific fields if applicable
                if (this.feedbackCategory === 'accuracy') {
                    report.verseReference = this.feedbackVerseRef || null;
                    report.translation = this.feedbackTranslation || null;
                    report.accuracyType = this.feedbackAccuracyType || null;
                }

                // Submit to Supabase
                await SupabaseAuth.submitBugReport(report);

                this.feedbackSuccess = true;
                this.showToast('Feedback submitted. Thank you!', 'success');

            } catch (err) {
                console.error('Failed to submit feedback:', err);
                this.feedbackError = err.message || 'Failed to submit feedback. Please try again.';
            } finally {
                this.feedbackSubmitting = false;
            }
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

        // Auth methods
        async initAuth() {
            try {
                if (window.SupabaseAuth) {
                    // Check for existing session
                    const user = await window.SupabaseAuth.getUser();
                    this.authUser = user;

                    // If already signed in, load plan progress from Supabase
                    if (user) {
                        this.loadPlanProgressFromSupabase();
                    }

                    // Listen for auth changes
                    window.SupabaseAuth.onAuthStateChange((event, user) => {
                        this.authUser = user;
                        if (event === 'SIGNED_IN') {
                            this.loadNotes();
                            this.loadTags();
                            this.loadPlanProgressFromSupabase();
                            this.showToast('Signed in successfully', 'success');
                        } else if (event === 'SIGNED_OUT') {
                            this.loadNotes();
                            this.loadTags();
                            // Clear synced status when signed out
                            this.planProgressSynced = false;
                        }
                    });
                }
            } catch (err) {
                console.warn('Auth initialization failed:', err);
            }
        },

        async handleSignIn() {
            this.authError = null;
            this.authSuccess = null;
            this.authLoading = true;

            try {
                await window.SupabaseAuth.signIn(this.authEmail, this.authPassword);
                this.authEmail = '';
                this.authPassword = '';
            } catch (err) {
                this.authError = err.message || 'Failed to sign in';
            } finally {
                this.authLoading = false;
            }
        },

        async handleSignUp() {
            this.authError = null;
            this.authSuccess = null;

            if (this.authPassword !== this.authPasswordConfirm) {
                this.authError = 'Passwords do not match';
                return;
            }

            if (this.authPassword.length < 6) {
                this.authError = 'Password must be at least 6 characters';
                return;
            }

            this.authLoading = true;

            try {
                await window.SupabaseAuth.signUp(this.authEmail, this.authPassword);
                this.authSuccess = 'Check your email to confirm your account';
                this.authEmail = '';
                this.authPassword = '';
                this.authPasswordConfirm = '';
            } catch (err) {
                this.authError = err.message || 'Failed to create account';
            } finally {
                this.authLoading = false;
            }
        },

        async handleSignOut() {
            this.authLoading = true;
            try {
                await window.SupabaseAuth.signOut();
                this.authUser = null;
                await this.loadNotes();  // Reload local notes
                this.showToast('Signed out', 'info');
            } catch (err) {
                this.showToast('Failed to sign out', 'error');
            } finally {
                this.authLoading = false;
            }
        },

        async handleForgotPassword() {
            if (!this.authEmail) {
                this.authError = 'Enter your email address first';
                return;
            }

            this.authLoading = true;
            this.authError = null;

            try {
                await window.SupabaseAuth.resetPassword(this.authEmail);
                this.authSuccess = 'Check your email for password reset link';
            } catch (err) {
                this.authError = err.message || 'Failed to send reset email';
            } finally {
                this.authLoading = false;
            }
        },

        // Notes (Supabase for logged-in users, localStorage for guests)
        async loadNotes() {
            try {
                if (this.authUser && window.SupabaseAuth) {
                    // Load from Supabase
                    this.notes = await window.SupabaseAuth.fetchUserNotes();
                } else {
                    // Load from localStorage (guest mode)
                    const saved = localStorage.getItem('bible-notes');
                    this.notes = saved ? JSON.parse(saved) : [];
                }
            } catch (err) {
                console.error('Failed to load notes:', err);
                // Fall back to localStorage
                const saved = localStorage.getItem('bible-notes');
                this.notes = saved ? JSON.parse(saved) : [];
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

        // Format note content with clickable Bible references
        formatNoteContent(content) {
            return linkifyBibleReferences(content);
        },

        // Handle clicks on Bible reference links in notes
        handleNoteRefClick(event) {
            const link = event.target.closest('.note-ref');
            if (link) {
                event.preventDefault();
                const ref = link.dataset.ref;
                if (ref) {
                    this.loadReference(ref);
                }
            }
        },

        // Check if note is in current chapter (or any chapter in combined plan reading mode)
        noteInCurrentChapter(note) {
            // In combined plan reading mode, check against all chapters being read
            if (this.combinedPlanReading && this.planReadingChapters.length > 0) {
                return this.planReadingChapters.some(ch =>
                    ch.book === note.book && ch.chapter === note.chapter
                );
            }
            // Normal mode: check current book/chapter
            return note.book === this.currentBook && note.chapter === this.currentChapter;
        },

        // Check if note applies to active verse (from scroll or click)
        noteMatchesActiveVerse(note) {
            const activeVerse = this.getActiveVerse();
            if (!activeVerse) return true;  // If no active verse, all match
            const start = note.startVerse || 1;
            const end = note.endVerse || start;
            return activeVerse >= start && activeVerse <= end;
        },

        // Get the currently active verse (from click or scroll)
        getActiveVerse() {
            // Clicked verse takes priority
            if (this.highlightedVerses.length > 0) {
                return this.highlightedVerses[0];
            }
            // Otherwise use scroll-tracked verse
            return this.scrollActiveVerse;
        },

        // Get all notes for the current chapter, sorted with active verse notes first
        getRelevantNotes() {
            const chapterNotes = this.notes.filter(note => this.noteInCurrentChapter(note));

            // Sort: active verse notes first, then by verse number
            return chapterNotes.sort((a, b) => {
                const aActive = this.noteMatchesActiveVerse(a);
                const bActive = this.noteMatchesActiveVerse(b);

                if (aActive && !bActive) return -1;
                if (!aActive && bActive) return 1;

                // Same active status: sort by verse
                return (a.startVerse || 1) - (b.startVerse || 1);
            });
        },

        async saveNote() {
            if (!this.currentNote.trim() || !this.currentBook) return;

            // Use selected verses if in note edit mode, otherwise use highlighted verse
            const startVerse = this.noteEditMode && this.selectedVerses.length > 0
                ? this.getSelectedVerseStart()
                : this.getNoteStartVerse();
            const endVerse = this.noteEditMode && this.selectedVerses.length > 0
                ? this.getSelectedVerseEnd()
                : (this.showNoteRange && this.noteEndVerse ? parseInt(this.noteEndVerse) : startVerse);

            const noteData = {
                book: this.currentBook,
                chapter: this.currentChapter,
                startVerse: startVerse,
                endVerse: endVerse,
                content: this.currentNote
            };

            try {
                let savedNoteId;
                if (this.authUser && window.SupabaseAuth) {
                    // Save to Supabase
                    const savedNote = await window.SupabaseAuth.saveUserNote(noteData);
                    this.notes.unshift(savedNote);
                    savedNoteId = savedNote.id;
                } else {
                    // Save to localStorage (guest mode)
                    const note = {
                        id: Date.now(),
                        ...noteData,
                        created_at: new Date().toISOString(),
                        synced: false
                    };
                    this.notes.unshift(note);
                    localStorage.setItem('bible-notes', JSON.stringify(this.notes));
                    savedNoteId = note.id;
                }

                // Apply pending tags to the new note
                if (this.pendingNoteTags.length > 0 && savedNoteId) {
                    for (const tagId of this.pendingNoteTags) {
                        await this.toggleNoteTag(savedNoteId, tagId);
                    }
                }

                this.currentNote = '';
                this.noteEndVerse = null;
                this.showNoteRange = false;
                this.noteEditMode = false;
                this.selectedVerses = [];
                this.pendingNoteTags = [];
            } catch (err) {
                console.error('Failed to save note:', err);
                this.showToast('Failed to save note', 'error');
            }
        },

        // Delete a note
        async deleteNote(noteId) {
            try {
                if (this.authUser && window.SupabaseAuth) {
                    // Delete from Supabase
                    await window.SupabaseAuth.deleteUserNote(noteId);
                }
                // Always remove from local state
                this.notes = this.notes.filter(n => n.id !== noteId);

                // Update localStorage for guests
                if (!this.authUser) {
                    localStorage.setItem('bible-notes', JSON.stringify(this.notes));
                }
            } catch (err) {
                console.error('Failed to delete note:', err);
                this.showToast('Failed to delete note', 'error');
            }
        },

        // Start editing a note
        startEditNote(note) {
            this.editingNoteId = note.id;
            this.editingNoteContent = note.content;
        },

        // Cancel editing a note
        cancelEditNote() {
            this.editingNoteId = null;
            this.editingNoteContent = '';
        },

        // Save edited note
        async saveEditNote(note) {
            if (!this.editingNoteContent.trim()) return;

            try {
                const updatedContent = this.editingNoteContent.trim();

                if (this.authUser && window.SupabaseAuth) {
                    // Update in Supabase
                    await window.SupabaseAuth.updateUserNote(note.id, { content: updatedContent });
                }

                // Update local state
                const noteIndex = this.notes.findIndex(n => n.id === note.id);
                if (noteIndex !== -1) {
                    this.notes[noteIndex].content = updatedContent;
                }

                // Update localStorage for guests
                if (!this.authUser) {
                    localStorage.setItem('bible-notes', JSON.stringify(this.notes));
                }

                // Clear editing state
                this.editingNoteId = null;
                this.editingNoteContent = '';
            } catch (err) {
                console.error('Failed to update note:', err);
                this.showToast('Failed to update note', 'error');
            }
        },

        // Format date
        formatDate(isoString) {
            return new Date(isoString).toLocaleDateString();
        },

        // ========== TAG METHODS ==========

        // Load user tags
        async loadTags() {
            try {
                if (this.authUser && window.SupabaseAuth) {
                    // Load from Supabase
                    this.tags = await window.SupabaseAuth.fetchUserTags();
                    this.noteTags = await window.SupabaseAuth.fetchAllNoteTags();
                } else {
                    // Load from localStorage (guest mode)
                    const savedTags = localStorage.getItem('bible-tags');
                    this.tags = savedTags ? JSON.parse(savedTags) : [];
                    const savedNoteTags = localStorage.getItem('bible-note-tags');
                    this.noteTags = savedNoteTags ? JSON.parse(savedNoteTags) : {};
                }
            } catch (err) {
                console.error('Failed to load tags:', err);
                // Fall back to localStorage
                const savedTags = localStorage.getItem('bible-tags');
                this.tags = savedTags ? JSON.parse(savedTags) : [];
            }
        },

        // Create a new tag
        async createTag() {
            if (!this.newTagName.trim()) return;

            const tagData = {
                name: this.newTagName.trim(),
                color: this.newTagColor
            };

            try {
                if (this.authUser && window.SupabaseAuth) {
                    const savedTag = await window.SupabaseAuth.createUserTag(tagData.name, tagData.color);
                    this.tags.push(savedTag);
                } else {
                    // Guest mode - save to localStorage
                    const tag = {
                        id: Date.now(),
                        ...tagData,
                        sortOrder: this.tags.length,
                        synced: false
                    };
                    this.tags.push(tag);
                    localStorage.setItem('bible-tags', JSON.stringify(this.tags));
                }

                this.newTagName = '';
                this.newTagColor = '#ef4444';
            } catch (err) {
                console.error('Failed to create tag:', err);
                this.showToast('Failed to create tag', 'error');
            }
        },

        // Update a tag
        async updateTag(tag) {
            try {
                if (this.authUser && window.SupabaseAuth) {
                    await window.SupabaseAuth.updateUserTag(tag.id, {
                        name: tag.name,
                        color: tag.color,
                        sortOrder: tag.sortOrder
                    });
                } else {
                    localStorage.setItem('bible-tags', JSON.stringify(this.tags));
                }
                this.editingTag = null;
            } catch (err) {
                console.error('Failed to update tag:', err);
                this.showToast('Failed to update tag', 'error');
            }
        },

        // Delete a tag
        async deleteTag(tagId) {
            if (!confirm('Delete this tag? It will be removed from all notes.')) return;

            try {
                if (this.authUser && window.SupabaseAuth) {
                    await window.SupabaseAuth.deleteUserTag(tagId);
                }
                this.tags = this.tags.filter(t => t.id !== tagId);

                // Remove from note tags
                for (const noteId of Object.keys(this.noteTags)) {
                    this.noteTags[noteId] = this.noteTags[noteId].filter(tid => tid !== tagId);
                }

                if (!this.authUser) {
                    localStorage.setItem('bible-tags', JSON.stringify(this.tags));
                    localStorage.setItem('bible-note-tags', JSON.stringify(this.noteTags));
                }
            } catch (err) {
                console.error('Failed to delete tag:', err);
                this.showToast('Failed to delete tag', 'error');
            }
        },

        // Get tags for a note
        getNoteTagObjects(noteId) {
            const tagIds = this.noteTags[noteId] || [];
            return this.tags.filter(t => tagIds.includes(t.id));
        },

        // Toggle a tag on a note
        async toggleNoteTag(noteId, tagId) {
            const currentTags = this.noteTags[noteId] || [];
            const hasTag = currentTags.includes(tagId);

            try {
                if (hasTag) {
                    // Remove tag
                    if (this.authUser && window.SupabaseAuth) {
                        await window.SupabaseAuth.removeTagFromNote(noteId, tagId);
                    }
                    this.noteTags[noteId] = currentTags.filter(tid => tid !== tagId);
                } else {
                    // Add tag
                    if (this.authUser && window.SupabaseAuth) {
                        await window.SupabaseAuth.addTagToNote(noteId, tagId);
                    }
                    if (!this.noteTags[noteId]) this.noteTags[noteId] = [];
                    this.noteTags[noteId].push(tagId);
                }

                if (!this.authUser) {
                    localStorage.setItem('bible-note-tags', JSON.stringify(this.noteTags));
                }
            } catch (err) {
                console.error('Failed to toggle note tag:', err);
                this.showToast('Failed to update tags', 'error');
            }
        },

        // Check if a note has a specific tag
        noteHasTag(noteId, tagId) {
            return (this.noteTags[noteId] || []).includes(tagId);
        },

        // Toggle a pending tag for new note creation
        togglePendingTag(tagId) {
            const idx = this.pendingNoteTags.indexOf(tagId);
            if (idx >= 0) {
                this.pendingNoteTags.splice(idx, 1);
            } else {
                this.pendingNoteTags.push(tagId);
            }
        },

        // Check if a tag is pending for new note
        isPendingTag(tagId) {
            return this.pendingNoteTags.includes(tagId);
        },

        // Get tag colors for a verse (from notes on that verse)
        getVerseTagColors(verseNum) {
            const colors = [];
            for (const note of this.notes) {
                if (note.book !== this.currentBook || note.chapter !== this.currentChapter) continue;
                const start = note.startVerse || 1;
                const end = note.endVerse || start;
                if (verseNum >= start && verseNum <= end) {
                    const noteTags = this.getNoteTagObjects(note.id);
                    for (const tag of noteTags) {
                        if (!colors.includes(tag.color)) {
                            colors.push(tag.color);
                        }
                    }
                }
            }
            return colors.slice(0, 3); // Max 3 dots
        },

        // ========== MULTI-VERSE SELECTION METHODS ==========

        // Toggle note edit mode
        toggleNoteEditMode() {
            this.noteEditMode = !this.noteEditMode;
            if (this.noteEditMode) {
                // Start with currently highlighted verse
                this.selectedVerses = this.highlightedVerses.length > 0
                    ? [...this.highlightedVerses]
                    : [];
            } else {
                this.selectedVerses = [];
            }
        },

        // Handle verse selection in note edit mode
        handleVerseSelection(verseNum, event) {
            if (!this.noteEditMode) return;

            // Shift+click for range selection
            if (event.shiftKey && this.selectedVerses.length > 0) {
                const lastSelected = this.selectedVerses[this.selectedVerses.length - 1];
                const start = Math.min(lastSelected, verseNum);
                const end = Math.max(lastSelected, verseNum);
                // Select all verses in range
                for (let v = start; v <= end; v++) {
                    if (!this.selectedVerses.includes(v)) {
                        this.selectedVerses.push(v);
                    }
                }
            } else {
                // Toggle single verse
                const idx = this.selectedVerses.indexOf(verseNum);
                if (idx >= 0) {
                    this.selectedVerses.splice(idx, 1);
                } else {
                    this.selectedVerses.push(verseNum);
                }
            }

            // Sort selection
            this.selectedVerses.sort((a, b) => a - b);
        },

        // Check if verse is selected for note
        isVerseSelectedForNote(verseNum) {
            return this.selectedVerses.includes(verseNum);
        },

        // Get selected verse range as string
        getSelectedVerseRange() {
            if (this.selectedVerses.length === 0) return '';
            const sorted = [...this.selectedVerses].sort((a, b) => a - b);
            if (sorted.length === 1) return `${sorted[0]}`;

            // Find contiguous ranges
            const ranges = [];
            let start = sorted[0];
            let end = sorted[0];

            for (let i = 1; i < sorted.length; i++) {
                if (sorted[i] === end + 1) {
                    end = sorted[i];
                } else {
                    ranges.push(start === end ? `${start}` : `${start}-${end}`);
                    start = end = sorted[i];
                }
            }
            ranges.push(start === end ? `${start}` : `${start}-${end}`);

            return ranges.join(', ');
        },

        // Get first and last selected verses
        getSelectedVerseStart() {
            if (this.selectedVerses.length === 0) return this.highlightedVerses[0] || 1;
            return Math.min(...this.selectedVerses);
        },

        getSelectedVerseEnd() {
            if (this.selectedVerses.length === 0) return this.highlightedVerses[0] || 1;
            return Math.max(...this.selectedVerses);
        },

        // Check if a verse should be highlighted
        isVerseHighlighted(verseNum) {
            return this.highlightedVerses.includes(verseNum);
        },

        // Update URL with clean path format (/Book/Chapter/Verse or /plan/PlanId/Day)
        updateURL() {
            // If in combined plan reading mode, use plan URL format
            if (this.combinedPlanReading && this.currentPlan) {
                const path = `/plan/${this.currentPlan.id}/${this.planDay}`;
                window.history.pushState({}, '', path);
                return;
            }

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
        },

        // ========== OFFLINE METHODS ==========

        // Update offline storage stats
        async updateOfflineStats() {
            if (!window.offlineStorage) return;

            try {
                const stats = await window.offlineStorage.getStorageStats();
                let totalChapters = 0;
                let totalVerses = 0;

                // Count verses across all translations
                for (const translation of Object.values(stats.verses.translations)) {
                    totalChapters += translation.chapters;
                    totalVerses += translation.verses;
                }

                this.offlineStats = {
                    chapters: totalChapters,
                    verses: totalVerses,
                    lexicon: stats.lexicon.cached,
                    estimatedSize: this.estimateStorageSize(totalVerses, stats.lexicon.count, stats.interlinear.chapters)
                };
            } catch (err) {
                console.error('Failed to update offline stats:', err);
            }
        },

        // Estimate storage size in bytes
        estimateStorageSize(verses, lexiconEntries, interlinearChapters) {
            // Rough estimates: ~500 bytes per verse, ~1KB per lexicon entry, ~50KB per interlinear chapter
            return (verses * 500) + (lexiconEntries * 1024) + (interlinearChapters * 50000);
        },

        // Format storage size for display
        formatStorageSize(bytes) {
            if (bytes === 0) return '0 B';
            const units = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(1024));
            return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i];
        },

        // Show a toast notification
        showToast(message, type = 'info') {
            const id = Date.now();
            this.toasts.push({ id, message, type });

            // Auto-remove after 4 seconds
            setTimeout(() => {
                this.toasts = this.toasts.filter(t => t.id !== id);
            }, 4000);
        },

        // Toggle auto-cache and persist preference
        toggleAutoCache() {
            this.autoCacheEnabled = !this.autoCacheEnabled;
            localStorage.setItem('autoCacheEnabled', this.autoCacheEnabled);
        },

        // Start downloading selected offline content
        async startDownload() {
            if (this.downloadProgress.active) return;

            this.downloadProgress.active = true;
            this.downloadProgress.percent = 0;

            try {
                // Download lexicon if selected
                if (this.downloadOptions.lexicon && !this.offlineStats.lexicon) {
                    await this.downloadLexicon();
                }

                // Download current book if selected
                if (this.downloadOptions.currentBook && this.currentBook) {
                    await this.downloadBook(this.currentBook);
                }

                this.showToast('Download complete!', 'success');
                await this.updateOfflineStats();

            } catch (err) {
                console.error('Download failed:', err);
                this.showToast('Download failed: ' + err.message, 'error');
            } finally {
                this.downloadProgress.active = false;
                this.downloadOptions.lexicon = false;
                this.downloadOptions.currentBook = false;
            }
        },

        // Download the Strong's lexicon
        async downloadLexicon() {
            this.downloadProgress.label = 'Downloading lexicon...';
            this.downloadProgress.status = 'Fetching Hebrew & Greek definitions';

            try {
                const response = await fetch('/api/offline/lexicon');
                if (!response.ok) throw new Error('Failed to fetch lexicon');

                const data = await response.json();
                this.downloadProgress.percent = 50;

                if (data.entries && window.offlineStorage) {
                    this.downloadProgress.status = `Saving ${data.entries.length} entries...`;
                    await window.offlineStorage.saveLexiconEntries(data.entries);
                    this.downloadProgress.percent = 100;
                }
            } catch (err) {
                console.error('Lexicon download failed:', err);
                throw err;
            }
        },

        // Download an entire book
        async downloadBook(book) {
            const chapterCount = BOOK_CHAPTERS[book] || 1;
            this.downloadProgress.label = `Downloading ${book}...`;

            for (let ch = 1; ch <= chapterCount; ch++) {
                this.downloadProgress.status = `Chapter ${ch} of ${chapterCount}`;
                this.downloadProgress.percent = Math.round((ch / chapterCount) * 100);

                try {
                    // Use the bulk chapter endpoint
                    const response = await fetch(
                        `/api/offline/chapter?book=${encodeURIComponent(book)}&chapter=${ch}&translation=${this.translation}`
                    );

                    if (!response.ok) continue;

                    const data = await response.json();

                    if (window.offlineStorage) {
                        // Save verses
                        if (data.verses?.length > 0) {
                            await window.offlineStorage.saveChapterVerses(this.translation, book, ch, data.verses);
                        }

                        // Save alignments
                        if (data.alignments?.length > 0) {
                            await window.offlineStorage.saveChapterAlignments(this.translation, book, ch, data.alignments);
                        }

                        // Save interlinear
                        if (data.interlinear?.length > 0) {
                            await window.offlineStorage.saveChapterInterlinear(book, ch, data.interlinear);
                        }

                        // Save cross-refs
                        if (data.cross_refs?.length > 0) {
                            await window.offlineStorage.saveChapterCrossRefs(book, ch, data.cross_refs);
                        }

                        // Save commentary
                        if (data.commentary?.length > 0) {
                            await window.offlineStorage.saveChapterCommentary(book, ch, data.commentary);
                        }
                    }
                } catch (err) {
                    console.warn(`Failed to download ${book} ${ch}:`, err);
                }

                // Small delay to avoid hammering the server
                await new Promise(r => setTimeout(r, 100));
            }
        },

        // Clear all offline data
        async clearOfflineData() {
            if (!confirm('Clear all cached offline data?')) return;

            try {
                if (window.offlineStorage) {
                    await window.offlineStorage.clearAll();
                }

                // Also clear service worker cache
                if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
                    const channel = new MessageChannel();
                    navigator.serviceWorker.controller.postMessage(
                        { type: 'CLEAR_CACHE' },
                        [channel.port2]
                    );
                }

                await this.updateOfflineStats();
                this.showToast('Offline data cleared', 'success');
            } catch (err) {
                console.error('Failed to clear offline data:', err);
                this.showToast('Failed to clear data', 'error');
            }
        },

        // Check if any download options are selected
        hasDownloadSelections() {
            const t = this.downloadSelections.translations;
            return t.BSB || t.WEB || t.KJV ||
                   this.downloadSelections.lexicon ||
                   this.downloadSelections.commentaryMH ||
                   this.downloadSelections.commentaryJG ||
                   this.downloadSelections.crossRefs ||
                   this.downloadSelections.devotionalSpurgeon;
        },

        // Start downloading selected offline content
        async startOfflineDownload() {
            if (this.downloadProgress.active) return;
            if (!this.hasDownloadSelections()) return;

            this.downloadProgress.active = true;
            this.downloadProgress.percent = 0;

            const tasks = [];
            const t = this.downloadSelections.translations;

            // Gather tasks
            if (t.BSB) tasks.push({ type: 'translation', name: 'BSB' });
            if (t.WEB) tasks.push({ type: 'translation', name: 'WEB' });
            if (t.KJV) tasks.push({ type: 'translation', name: 'KJV' });
            if (this.downloadSelections.lexicon) tasks.push({ type: 'lexicon' });
            if (this.downloadSelections.commentaryMH) tasks.push({ type: 'commentary', source: 'Matthew Henry' });
            if (this.downloadSelections.commentaryJG) tasks.push({ type: 'commentary', source: 'John Gill' });
            if (this.downloadSelections.crossRefs) tasks.push({ type: 'crossRefs' });
            if (this.downloadSelections.devotionalSpurgeon) tasks.push({ type: 'devotional', source: 'Spurgeon' });

            try {
                for (let i = 0; i < tasks.length; i++) {
                    const task = tasks[i];
                    const basePercent = Math.round((i / tasks.length) * 100);

                    if (task.type === 'translation') {
                        await this.downloadFullTranslation(task.name, basePercent, tasks.length);
                    } else if (task.type === 'lexicon') {
                        this.downloadProgress.label = 'Downloading lexicon...';
                        this.downloadProgress.status = 'Fetching Hebrew & Greek definitions';
                        await this.downloadLexicon();
                    } else if (task.type === 'commentary') {
                        await this.downloadAllCommentary(basePercent, tasks.length, task.source);
                    } else if (task.type === 'crossRefs') {
                        await this.downloadAllCrossRefs(basePercent, tasks.length);
                    } else if (task.type === 'devotional') {
                        await this.downloadDevotionals(basePercent, tasks.length, task.source);
                    }
                }

                this.showToast('Download complete!', 'success');
                await this.updateOfflineStats();

                // Reset selections
                this.downloadSelections.translations = { BSB: false, WEB: false, KJV: false };
                this.downloadSelections.lexicon = false;
                this.downloadSelections.commentaryMH = false;
                this.downloadSelections.commentaryJG = false;
                this.downloadSelections.crossRefs = false;
                this.downloadSelections.devotionalSpurgeon = false;

            } catch (err) {
                console.error('Download failed:', err);
                this.showToast('Download failed: ' + err.message, 'error');
            } finally {
                this.downloadProgress.active = false;
            }
        },

        // Download full translation (all 66 books)
        async downloadFullTranslation(translation, basePercent, totalTasks) {
            const books = Object.keys(BOOK_CHAPTERS);
            const totalChapters = Object.values(BOOK_CHAPTERS).reduce((a, b) => a + b, 0);
            let chaptersDownloaded = 0;

            this.downloadProgress.label = `Downloading ${translation}...`;

            for (const book of books) {
                const chapterCount = BOOK_CHAPTERS[book];
                for (let ch = 1; ch <= chapterCount; ch++) {
                    this.downloadProgress.status = `${book} ${ch}`;

                    try {
                        const response = await fetch(
                            `/api/offline/chapter?book=${encodeURIComponent(book)}&chapter=${ch}&translation=${translation}`
                        );
                        if (response.ok) {
                            const data = await response.json();
                            if (window.offlineStorage && data.verses?.length > 0) {
                                await window.offlineStorage.saveChapterVerses(translation, book, ch, data.verses);
                                if (data.alignments?.length > 0) {
                                    await window.offlineStorage.saveChapterAlignments(translation, book, ch, data.alignments);
                                }
                                if (data.interlinear?.length > 0) {
                                    await window.offlineStorage.saveChapterInterlinear(book, ch, data.interlinear);
                                }
                            }
                        }
                    } catch (err) {
                        console.warn(`Failed to download ${book} ${ch}:`, err);
                    }

                    chaptersDownloaded++;
                    const taskProgress = (chaptersDownloaded / totalChapters) * (100 / totalTasks);
                    this.downloadProgress.percent = Math.round(basePercent + taskProgress);

                    // Small delay
                    await new Promise(r => setTimeout(r, 50));
                }
            }
        },

        // Download all commentary (optionally filtered by source)
        async downloadAllCommentary(basePercent, totalTasks, source = null) {
            this.downloadProgress.label = `Downloading ${source || 'commentary'}...`;
            const books = Object.keys(BOOK_CHAPTERS);
            let booksDownloaded = 0;

            for (const book of books) {
                this.downloadProgress.status = book;

                try {
                    const response = await fetch(`/api/offline/commentary?book=${encodeURIComponent(book)}`);
                    if (response.ok) {
                        const data = await response.json();
                        if (window.offlineStorage && data.entries?.length > 0) {
                            // Filter by source if specified
                            const entries = source
                                ? data.entries.filter(e => e.source === source)
                                : data.entries;
                            for (const entry of entries) {
                                await window.offlineStorage.saveCommentary(entry.book, entry.chapter, [entry]);
                            }
                        }
                    }
                } catch (err) {
                    console.warn(`Failed to download commentary for ${book}:`, err);
                }

                booksDownloaded++;
                const taskProgress = (booksDownloaded / books.length) * (100 / totalTasks);
                this.downloadProgress.percent = Math.round(basePercent + taskProgress);

                await new Promise(r => setTimeout(r, 50));
            }
        },

        // Download all devotionals
        async downloadDevotionals(basePercent, totalTasks, source) {
            this.downloadProgress.label = `Downloading ${source} devotionals...`;
            this.downloadProgress.status = 'Fetching all entries...';

            try {
                const response = await fetch(`/api/offline/devotionals?source=${encodeURIComponent(source)}`);
                if (response.ok) {
                    const data = await response.json();
                    if (window.offlineStorage && data.entries?.length > 0) {
                        // Store devotionals in IndexedDB
                        // For now, store in localStorage as a simple approach
                        localStorage.setItem(`devotional_${source}`, JSON.stringify(data.entries));
                        this.downloadProgress.status = `Saved ${data.count} entries`;
                    }
                }
            } catch (err) {
                console.warn(`Failed to download devotionals for ${source}:`, err);
            }

            this.downloadProgress.percent = Math.round(basePercent + (100 / totalTasks));
        },

        // Download all cross-references
        async downloadAllCrossRefs(basePercent, totalTasks) {
            this.downloadProgress.label = 'Downloading cross-references...';
            const books = Object.keys(BOOK_CHAPTERS);
            let booksDownloaded = 0;

            for (const book of books) {
                this.downloadProgress.status = book;

                try {
                    const response = await fetch(`/api/offline/crossrefs?book=${encodeURIComponent(book)}`);
                    if (response.ok) {
                        const data = await response.json();
                        if (window.offlineStorage && data.entries?.length > 0) {
                            // Group by chapter and save
                            const byChapter = {};
                            for (const ref of data.entries) {
                                const ch = ref.chapter || 1;
                                if (!byChapter[ch]) byChapter[ch] = [];
                                byChapter[ch].push(ref);
                            }
                            for (const [ch, refs] of Object.entries(byChapter)) {
                                await window.offlineStorage.saveChapterCrossRefs(book, parseInt(ch), refs);
                            }
                        }
                    }
                } catch (err) {
                    console.warn(`Failed to download cross-refs for ${book}:`, err);
                }

                booksDownloaded++;
                const taskProgress = (booksDownloaded / books.length) * (100 / totalTasks);
                this.downloadProgress.percent = Math.round(basePercent + taskProgress);

                await new Promise(r => setTimeout(r, 50));
            }
        },

        // Refresh (re-download) all cached content
        async refreshOfflineData() {
            if (!confirm('Re-download all cached content? This will refresh existing data.')) return;

            // Get what's currently cached and re-download it
            this.downloadProgress.active = true;
            this.downloadProgress.label = 'Refreshing cache...';
            this.downloadProgress.percent = 0;

            try {
                // Clear and re-download lexicon if it was cached
                if (this.offlineStats.lexicon) {
                    this.downloadProgress.status = 'Refreshing lexicon...';
                    await this.downloadLexicon();
                }

                // Re-download cached chapters
                if (window.offlineStorage && this.offlineStats.chapters > 0) {
                    this.downloadProgress.status = 'Refreshing chapters...';
                    // We'll need to iterate through what we have cached
                    // For now, just clear and let auto-cache rebuild
                    await window.offlineStorage.clearAll();
                }

                await this.updateOfflineStats();
                this.showToast('Cache refreshed', 'success');
            } catch (err) {
                console.error('Refresh failed:', err);
                this.showToast('Refresh failed', 'error');
            } finally {
                this.downloadProgress.active = false;
            }
        },

        // Toggle forced offline mode - blocks ALL network requests
        toggleForcedOffline() {
            this.forcedOffline = !this.forcedOffline;
            localStorage.setItem('forcedOffline', this.forcedOffline);

            if (this.forcedOffline) {
                this.isOnline = false;
                this.showToast('Offline mode enabled - no network requests will be made', 'info');
            } else {
                this.isOnline = navigator.onLine;
                this.showToast('Online mode restored', 'success');
            }
        },

        // Check if we should allow network requests
        canUseNetwork() {
            return !this.forcedOffline && navigator.onLine;
        },

        // ========== DEVOTIONAL METHODS ==========

        async loadDevotional(date = null) {
            if (this.loadingDevotional) return;

            this.loadingDevotional = true;
            try {
                let url = '/api/devotional';
                if (date) {
                    url += `?date=${date}`;
                } else {
                    // Use current devotional date state
                    const dateStr = `${String(this.devotionalMonth).padStart(2, '0')}-${String(this.devotionalDay).padStart(2, '0')}`;
                    url += `?date=${dateStr}`;
                }

                const response = await fetch(url);
                if (response.ok) {
                    this.devotional = await response.json();
                } else {
                    this.devotional = { entries: [], month: this.devotionalMonth, day: this.devotionalDay };
                }
            } catch (err) {
                console.error('Failed to load devotional:', err);
                this.devotional = { entries: [], month: this.devotionalMonth, day: this.devotionalDay };
            } finally {
                this.loadingDevotional = false;
            }
        },

        changeDevotionalDate(delta) {
            // Create a date object to handle month/day rollover
            const date = new Date(2024, this.devotionalMonth - 1, this.devotionalDay);
            date.setDate(date.getDate() + delta);

            this.devotionalMonth = date.getMonth() + 1;
            this.devotionalDay = date.getDate();
            this.loadDevotional();
        },

        formatDevotionalDate(month, day) {
            const months = ['January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December'];
            return `${months[month - 1]} ${day}`;
        },

        formatDevotionalText(text) {
            if (!text) return '';
            // Convert newlines to paragraphs and clean up
            return text.split(/\n\n+/).map(p => `<p>${p.trim()}</p>`).join('');
        },

        // ========== READING PLAN METHODS ==========

        loadPlanProgress() {
            try {
                const saved = localStorage.getItem('readingPlanProgress');
                if (saved) {
                    this.planProgress = JSON.parse(saved);
                }
            } catch (err) {
                console.warn('Failed to load plan progress:', err);
            }
        },

        // Load plan progress from Supabase (called after auth is initialized)
        async loadPlanProgressFromSupabase() {
            if (!this.authUser || !window.SupabaseAuth?.fetchUserReadingPlans) return;

            try {
                // First, sync any local-only progress to Supabase
                await this.syncLocalPlanProgressToSupabase();

                // Fetch plans and progress from Supabase
                const plans = await window.SupabaseAuth.fetchUserReadingPlans();
                const progressData = await window.SupabaseAuth.fetchAllPlanProgress();

                // Merge with local data (Supabase takes precedence)
                for (const plan of plans) {
                    const progress = progressData[plan.planId];
                    this.planProgress[plan.planId] = {
                        startDate: plan.startDate,
                        completedDays: progress?.completedDays || [],
                        userPlanId: plan.id,
                        synced: true
                    };
                }

                this.planProgressSynced = true;
                this.savePlanProgress();
            } catch (err) {
                console.warn('Failed to load plan progress from Supabase:', err);
            }
        },

        // Sync local-only plan progress to Supabase
        async syncLocalPlanProgressToSupabase() {
            if (!this.authUser || !window.SupabaseAuth?.syncLocalPlanProgress) return;

            for (const [planId, data] of Object.entries(this.planProgress)) {
                // Skip if already synced
                if (data.userPlanId || data.synced) continue;

                if (data.startDate) {
                    try {
                        const result = await window.SupabaseAuth.syncLocalPlanProgress(
                            planId,
                            data.startDate,
                            data.completedDays || []
                        );
                        if (result.synced) {
                            this.planProgress[planId].userPlanId = result.userPlanId;
                            this.planProgress[planId].synced = true;
                        }
                    } catch (err) {
                        console.warn(`Failed to sync plan ${planId}:`, err);
                    }
                }
            }
        },

        savePlanProgress() {
            try {
                localStorage.setItem('readingPlanProgress', JSON.stringify(this.planProgress));
            } catch (err) {
                console.warn('Failed to save plan progress:', err);
            }
        },

        async openReadingPlan() {
            this.showReadingPlan = true;
            this.planLoading = true;

            try {
                // Load available plans
                const response = await fetch('/api/reading-plans');
                if (response.ok) {
                    const data = await response.json();
                    this.readingPlans = data.plans;

                    // If user has an active plan, load it
                    const activePlanId = Object.keys(this.planProgress).find(
                        id => this.planProgress[id].startDate
                    );

                    if (activePlanId) {
                        await this.loadPlan(activePlanId);
                    }
                }
            } catch (err) {
                console.error('Failed to load reading plans:', err);
                this.showToast('Failed to load reading plans', 'error');
            } finally {
                this.planLoading = false;
            }
        },

        async loadPlan(planId) {
            this.planLoading = true;
            try {
                const response = await fetch(`/api/reading-plans/${planId}`);
                if (response.ok) {
                    this.currentPlan = await response.json();

                    // Calculate current day based on start date
                    if (this.planProgress[planId]?.startDate) {
                        const startDate = new Date(this.planProgress[planId].startDate);
                        const today = new Date();
                        startDate.setHours(0, 0, 0, 0);
                        today.setHours(0, 0, 0, 0);
                        const daysDiff = Math.floor((today - startDate) / (1000 * 60 * 60 * 24)) + 1;
                        this.planDay = Math.max(1, Math.min(daysDiff, this.currentPlan.duration_days));
                    } else {
                        this.planDay = 1;
                    }
                }
            } catch (err) {
                console.error('Failed to load plan:', err);
            } finally {
                this.planLoading = false;
            }
        },

        // Restore reading plan state from URL (used on page load and popstate)
        async restorePlanFromURL(planId, day) {
            try {
                // Load the plan data
                const response = await fetch(`/api/reading-plans/${planId}`);
                if (response.ok) {
                    this.currentPlan = await response.json();
                    this.planDay = Math.max(1, Math.min(day, this.currentPlan.duration_days));
                    // Start reading the plan
                    await this.startPlanReading();
                } else {
                    console.error('Plan not found:', planId);
                    // Fallback to home
                    window.history.replaceState({}, '', '/');
                }
            } catch (err) {
                console.error('Failed to restore plan from URL:', err);
                window.history.replaceState({}, '', '/');
            }
        },

        // Show start date picker before starting plan
        planStartDate: '',  // For the date picker input
        showPlanStartPicker: false,
        showCatchUpPrompt: false,  // For the catch-up confirmation
        pendingPlanId: null,

        promptStartPlan(planId) {
            // Default to Jan 1 of current year for annual plans
            const year = new Date().getFullYear();
            this.planStartDate = `${year}-01-01`;
            this.pendingPlanId = planId;
            this.showPlanStartPicker = true;
        },

        async confirmStartPlan() {
            if (!this.pendingPlanId || !this.planStartDate) return;

            this.planProgress[this.pendingPlanId] = {
                startDate: this.planStartDate,
                completedDays: []
            };

            // Sync to Supabase if logged in
            if (this.authUser && window.SupabaseAuth?.subscribeToReadingPlan) {
                try {
                    const result = await window.SupabaseAuth.subscribeToReadingPlan(
                        this.pendingPlanId,
                        this.planStartDate
                    );
                    this.planProgress[this.pendingPlanId].userPlanId = result.id;
                    this.planProgress[this.pendingPlanId].synced = true;
                } catch (err) {
                    console.warn('Failed to sync plan to Supabase:', err);
                }
            }

            this.savePlanProgress();
            this.loadPlan(this.pendingPlanId);
            this.showPlanStartPicker = false;
            this.pendingPlanId = null;
        },

        cancelStartPlan() {
            this.showPlanStartPicker = false;
            this.showCatchUpPrompt = false;
            this.pendingPlanId = null;
        },

        selectJanuaryFirst() {
            this.planStartDate = new Date().getFullYear() + '-01-01';
            this.checkForCatchUp();
        },

        checkForCatchUp() {
            if (!this.planStartDate) return;

            const startDate = new Date(this.planStartDate + 'T00:00:00');
            const today = new Date();
            today.setHours(0, 0, 0, 0);

            const daysDiff = Math.floor((today - startDate) / (1000 * 60 * 60 * 24));

            // If the start date is in the past (more than 0 days ago), show catch-up prompt
            if (daysDiff > 0) {
                this.showCatchUpPrompt = true;
            } else {
                // Start date is today or in the future, just proceed
                this.confirmStartPlan();
            }
        },

        getDaysElapsed() {
            if (!this.planStartDate) return 0;
            const startDate = new Date(this.planStartDate + 'T00:00:00');
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            return Math.floor((today - startDate) / (1000 * 60 * 60 * 24));
        },

        formatStartDate(dateStr) {
            if (!dateStr) return '';
            const date = new Date(dateStr + 'T00:00:00');
            return date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
        },

        async confirmStartPlanWithCatchUp(shouldCatchUp) {
            if (!this.pendingPlanId || !this.planStartDate) return;

            const daysElapsed = this.getDaysElapsed();

            // Create initial progress
            this.planProgress[this.pendingPlanId] = {
                startDate: this.planStartDate,
                completedDays: []
            };

            // Sync to Supabase if logged in
            if (this.authUser && window.SupabaseAuth?.subscribeToReadingPlan) {
                try {
                    const result = await window.SupabaseAuth.subscribeToReadingPlan(
                        this.pendingPlanId,
                        this.planStartDate
                    );
                    this.planProgress[this.pendingPlanId].userPlanId = result.id;
                    this.planProgress[this.pendingPlanId].synced = true;
                } catch (err) {
                    console.warn('Failed to sync plan to Supabase:', err);
                }
            }

            // If catching up, mark all past days as complete
            if (shouldCatchUp && daysElapsed > 0) {
                const completedDays = [];
                for (let i = 1; i <= daysElapsed; i++) {
                    completedDays.push(i);
                }
                this.planProgress[this.pendingPlanId].completedDays = completedDays;

                // Bulk sync to Supabase if logged in
                if (this.authUser && window.SupabaseAuth?.bulkMarkDaysComplete) {
                    try {
                        const userPlanId = this.planProgress[this.pendingPlanId].userPlanId;
                        if (userPlanId) {
                            await window.SupabaseAuth.bulkMarkDaysComplete(userPlanId, completedDays);
                        }
                    } catch (err) {
                        console.warn('Failed to bulk sync catch-up days to Supabase:', err);
                    }
                }
            }

            this.savePlanProgress();
            this.loadPlan(this.pendingPlanId);
            this.showPlanStartPicker = false;
            this.showCatchUpPrompt = false;
            this.pendingPlanId = null;
        },

        async startPlan(planId) {
            // For backwards compatibility, start with today
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const startDate = today.toISOString().split('T')[0];

            this.planProgress[planId] = {
                startDate: startDate,
                completedDays: []
            };

            // Sync to Supabase if logged in
            if (this.authUser && window.SupabaseAuth?.subscribeToReadingPlan) {
                try {
                    const result = await window.SupabaseAuth.subscribeToReadingPlan(planId, startDate);
                    this.planProgress[planId].userPlanId = result.id;
                    this.planProgress[planId].synced = true;
                } catch (err) {
                    console.warn('Failed to sync plan to Supabase:', err);
                }
            }

            this.savePlanProgress();
            this.loadPlan(planId);
        },

        async resetPlan(planId) {
            if (confirm('Reset this plan? All progress will be lost.')) {
                // Unsubscribe from Supabase if logged in
                if (this.authUser && window.SupabaseAuth?.unsubscribeFromReadingPlan) {
                    try {
                        await window.SupabaseAuth.unsubscribeFromReadingPlan(planId);
                    } catch (err) {
                        console.warn('Failed to unsubscribe from plan in Supabase:', err);
                    }
                }

                delete this.planProgress[planId];
                this.savePlanProgress();
                this.currentPlan = null;
                this.planDay = 1;
            }
        },

        getTodaysPlanDay(planId) {
            if (!this.planProgress[planId]?.startDate) return null;

            const startDate = new Date(this.planProgress[planId].startDate);
            const today = new Date();
            startDate.setHours(0, 0, 0, 0);
            today.setHours(0, 0, 0, 0);
            const daysDiff = Math.floor((today - startDate) / (1000 * 60 * 60 * 24)) + 1;
            return Math.max(1, Math.min(daysDiff, 365));
        },

        getPlanDayReadings(day) {
            if (!this.currentPlan) return null;
            return this.currentPlan.days.find(d => d.day === day);
        },

        isDayCompleted(day) {
            if (!this.currentPlan) return false;
            const planId = this.currentPlan.id;
            return this.planProgress[planId]?.completedDays?.includes(day) || false;
        },

        async toggleDayComplete(day) {
            if (!this.currentPlan) return;
            const planId = this.currentPlan.id;

            if (!this.planProgress[planId]) {
                this.planProgress[planId] = { completedDays: [] };
            }
            if (!this.planProgress[planId].completedDays) {
                this.planProgress[planId].completedDays = [];
            }

            const idx = this.planProgress[planId].completedDays.indexOf(day);
            const isCompleting = idx === -1;

            if (isCompleting) {
                this.planProgress[planId].completedDays.push(day);
            } else {
                this.planProgress[planId].completedDays.splice(idx, 1);
            }
            this.savePlanProgress();

            // Sync to Supabase if logged in
            const userPlanId = this.planProgress[planId].userPlanId;
            if (this.authUser && userPlanId && window.SupabaseAuth) {
                try {
                    if (isCompleting) {
                        await window.SupabaseAuth.markDayComplete(userPlanId, day);
                    } else {
                        await window.SupabaseAuth.unmarkDayComplete(userPlanId, day);
                    }
                } catch (err) {
                    console.warn('Failed to sync day completion to Supabase:', err);
                }
            }
        },

        getCompletedDaysCount() {
            if (!this.currentPlan) return 0;
            const planId = this.currentPlan.id;
            return this.planProgress[planId]?.completedDays?.length || 0;
        },

        getPlanProgressPercent() {
            if (!this.currentPlan) return 0;
            const completed = this.getCompletedDaysCount();
            return Math.round((completed / this.currentPlan.duration_days) * 100);
        },

        isPlanComplete() {
            if (!this.currentPlan) return false;
            return this.getCompletedDaysCount() >= this.currentPlan.duration_days;
        },

        goToPlanDay(day) {
            this.planDay = Math.max(1, Math.min(day, this.currentPlan?.duration_days || 365));
        },

        goToTodaysPlanDay() {
            if (!this.currentPlan) return;
            const today = this.getTodaysPlanDay(this.currentPlan.id);
            if (today) {
                this.planDay = today;
            }
        },

        // Normalize book names (e.g., "Psalm" -> "Psalms")
        normalizeBookName(book) {
            // Handle common abbreviations and variations
            const normalizations = {
                'Psalm': 'Psalms',
                'Song of Solomon': 'Song of Songs',
                // Chronicles abbreviations
                '1 Chron': '1 Chronicles',
                '1 Chron.': '1 Chronicles',
                '1 Chr': '1 Chronicles',
                '1 Chr.': '1 Chronicles',
                '2 Chron': '2 Chronicles',
                '2 Chron.': '2 Chronicles',
                '2 Chr': '2 Chronicles',
                '2 Chr.': '2 Chronicles',
                // Samuel abbreviations
                '1 Sam': '1 Samuel',
                '1 Sam.': '1 Samuel',
                '2 Sam': '2 Samuel',
                '2 Sam.': '2 Samuel',
                // Kings abbreviations
                '1 Kgs': '1 Kings',
                '1 Kgs.': '1 Kings',
                '2 Kgs': '2 Kings',
                '2 Kgs.': '2 Kings',
                // Other common abbreviations
                'Gen': 'Genesis',
                'Gen.': 'Genesis',
                'Exod': 'Exodus',
                'Exod.': 'Exodus',
                'Ex': 'Exodus',
                'Ex.': 'Exodus',
                'Lev': 'Leviticus',
                'Lev.': 'Leviticus',
                'Num': 'Numbers',
                'Num.': 'Numbers',
                'Deut': 'Deuteronomy',
                'Deut.': 'Deuteronomy',
                'Josh': 'Joshua',
                'Josh.': 'Joshua',
                'Judg': 'Judges',
                'Judg.': 'Judges',
                'Neh': 'Nehemiah',
                'Neh.': 'Nehemiah',
                'Esth': 'Esther',
                'Esth.': 'Esther',
                'Prov': 'Proverbs',
                'Prov.': 'Proverbs',
                'Eccl': 'Ecclesiastes',
                'Eccl.': 'Ecclesiastes',
                'Isa': 'Isaiah',
                'Isa.': 'Isaiah',
                'Jer': 'Jeremiah',
                'Jer.': 'Jeremiah',
                'Lam': 'Lamentations',
                'Lam.': 'Lamentations',
                'Ezek': 'Ezekiel',
                'Ezek.': 'Ezekiel',
                'Dan': 'Daniel',
                'Dan.': 'Daniel',
                'Hos': 'Hosea',
                'Hos.': 'Hosea',
                'Obad': 'Obadiah',
                'Obad.': 'Obadiah',
                'Mic': 'Micah',
                'Mic.': 'Micah',
                'Nah': 'Nahum',
                'Nah.': 'Nahum',
                'Hab': 'Habakkuk',
                'Hab.': 'Habakkuk',
                'Zeph': 'Zephaniah',
                'Zeph.': 'Zephaniah',
                'Hag': 'Haggai',
                'Hag.': 'Haggai',
                'Zech': 'Zechariah',
                'Zech.': 'Zechariah',
                'Mal': 'Malachi',
                'Mal.': 'Malachi',
                'Matt': 'Matthew',
                'Matt.': 'Matthew',
                'Rom': 'Romans',
                'Rom.': 'Romans',
                '1 Cor': '1 Corinthians',
                '1 Cor.': '1 Corinthians',
                '2 Cor': '2 Corinthians',
                '2 Cor.': '2 Corinthians',
                'Gal': 'Galatians',
                'Gal.': 'Galatians',
                'Eph': 'Ephesians',
                'Eph.': 'Ephesians',
                'Phil': 'Philippians',
                'Phil.': 'Philippians',
                'Col': 'Colossians',
                'Col.': 'Colossians',
                '1 Thess': '1 Thessalonians',
                '1 Thess.': '1 Thessalonians',
                '2 Thess': '2 Thessalonians',
                '2 Thess.': '2 Thessalonians',
                '1 Tim': '1 Timothy',
                '1 Tim.': '1 Timothy',
                '2 Tim': '2 Timothy',
                '2 Tim.': '2 Timothy',
                'Tit': 'Titus',
                'Tit.': 'Titus',
                'Phlm': 'Philemon',
                'Phlm.': 'Philemon',
                'Heb': 'Hebrews',
                'Heb.': 'Hebrews',
                'Jas': 'James',
                'Jas.': 'James',
                '1 Pet': '1 Peter',
                '1 Pet.': '1 Peter',
                '2 Pet': '2 Peter',
                '2 Pet.': '2 Peter',
                '1 John': '1 John',
                '2 John': '2 John',
                '3 John': '3 John',
                'Rev': 'Revelation',
                'Rev.': 'Revelation'
            };
            return normalizations[book] || book;
        },

        // Normalize a full reference (book + chapter/verse)
        normalizeReference(ref) {
            // Match book name at the start
            const match = ref.match(/^([A-Za-z\s]+?)(\s+\d.*)$/);
            if (match) {
                const book = this.normalizeBookName(match[1].trim());
                return book + match[2];
            }
            return ref;
        },

        // Parse a reading reference that might be a chapter range (e.g., "Genesis 1-3")
        // or semicolon-separated references (e.g., "2 Samuel 5; 1 Chron. 11-12")
        parseReadingReference(ref) {
            // First, split on semicolons for multiple separate references
            if (ref.includes(';')) {
                const parts = ref.split(';').map(p => p.trim()).filter(p => p);
                let allRefs = [];
                for (const part of parts) {
                    allRefs = allRefs.concat(this.parseReadingReference(part));
                }
                return allRefs;
            }

            // Normalize the reference (handles abbreviations like "1 Chron." -> "1 Chronicles")
            ref = this.normalizeReference(ref);

            // Match chapter ranges like "Genesis 1-3" or "Job 1-3"
            // Must NOT have a colon (which would indicate verse range like "Psalm 17:1-15")
            const chapterRangeMatch = ref.match(/^([A-Za-z0-9\s]+?)\s+(\d+)-(\d+)$/);
            if (chapterRangeMatch && !ref.includes(':')) {
                const book = chapterRangeMatch[1].trim();
                const startChapter = parseInt(chapterRangeMatch[2]);
                const endChapter = parseInt(chapterRangeMatch[3]);
                const chapters = [];
                for (let ch = startChapter; ch <= endChapter; ch++) {
                    chapters.push(`${book} ${ch}`);
                }
                return chapters;
            }
            // Single chapter, verse reference, or verse range - pass through as-is
            return [ref];
        },

        // Load all passages for the day into the main reader view
        async startPlanReading() {
            if (!this.currentPlan) return;

            const readings = this.getPlanDayReadings(this.planDay);
            if (!readings) return;

            this.showReadingPlan = false;
            this.loading = true;
            this.combinedPlanReading = true;
            this.planReadingSections = [];
            this.planReadingChapters = [];

            // We'll load verses into the main this.verses array
            let allVerses = [];
            let allCrossRefs = [];
            let allCommentary = [];
            let chaptersToLoadCommentary = [];

            // Parse and load each reading
            const readingTypes = ['chronological', 'psalms', 'proverbs'];

            for (const type of readingTypes) {
                const ref = readings[type];
                if (!ref) continue;

                // Parse the reference - might be multiple chapters
                const refs = this.parseReadingReference(ref);
                const label = type === 'chronological' ? 'Main Reading' : type.charAt(0).toUpperCase() + type.slice(1);

                // Track the section start
                const sectionStartIndex = allVerses.length;

                try {
                    let isFirstChapterInSection = true;
                    for (const singleRef of refs) {
                        const response = await fetch(`/api/passage/${encodeURIComponent(singleRef)}?translation=${this.translation}`);
                        if (response.ok) {
                            const data = await response.json();

                            // Collect cross-references with book/chapter context
                            if (data.cross_references && data.cross_references.length > 0) {
                                const crossRefsWithContext = data.cross_references.map(cr => ({
                                    ...cr,
                                    _sourceRef: singleRef,
                                    _sourceBook: data.reference.replace(/\s+\d+.*$/, ''),
                                    _sourceChapter: parseInt(data.reference.match(/\s+(\d+)/)?.[1] || 1)
                                }));
                                allCrossRefs = allCrossRefs.concat(crossRefsWithContext);
                            }

                            // Track chapters for commentary loading and notes filtering
                            const bookMatch = data.reference.match(/^(.+?)\s+(\d+)/);
                            if (bookMatch) {
                                const chapterInfo = {
                                    book: bookMatch[1],
                                    chapter: parseInt(bookMatch[2]),
                                    ref: `${bookMatch[1]} ${bookMatch[2]}`
                                };
                                chaptersToLoadCommentary.push(chapterInfo);
                                // Also track for notes panel (deduplicated later)
                                this.planReadingChapters.push({
                                    book: chapterInfo.book,
                                    chapter: chapterInfo.chapter
                                });
                            }

                            // Filter verses to only highlighted ones if a verse range was requested
                            let verses = data.verses;
                            if (data.highlighted_verses && data.highlighted_verses.length > 0 &&
                                data.highlighted_verses.length < data.verses.length) {
                                // Filter to only the highlighted/requested verses
                                const highlightedSet = new Set(data.highlighted_verses);
                                verses = data.verses.filter(v => highlightedSet.has(v.verse));
                            }

                            // Add book/chapter context to ALL verses for note-taking
                            // bookMatch already declared above at line 3005
                            const verseBook = bookMatch ? bookMatch[1] : 'Unknown';
                            const verseChapter = bookMatch ? parseInt(bookMatch[2]) : 1;

                            verses = verses.map((v, idx) => ({
                                ...v,
                                _book: verseBook,
                                _chapter: verseChapter,
                                // Mark first verse of each chapter for section headers
                                _chapterStart: idx === 0,
                                _chapterRef: idx === 0 ? singleRef : null,
                                _sectionType: idx === 0 ? type : null,
                                _sectionLabel: idx === 0 && isFirstChapterInSection ? label : null
                            }));
                            if (verses.length > 0) {
                                isFirstChapterInSection = false;
                            }
                            allVerses = allVerses.concat(verses);
                        }
                    }

                    // Add section info for the header bar
                    this.planReadingSections.push({
                        type,
                        label,
                        reference: ref,
                        startIndex: sectionStartIndex
                    });
                } catch (err) {
                    console.error(`Failed to load ${type}:`, err);
                }
            }

            // Set combined verses in the main reader
            this.verses = allVerses;
            this.currentReference = `${this.currentPlan.name} - Day ${this.planDay}`;
            this.highlightedVerses = [];
            this.crossRefs = allCrossRefs;
            this.combinedCrossRefs = allCrossRefs;  // Store for restoration after verse deselect
            this.commentary = [];
            this.loading = false;

            // Clear book/chapter since we're in combined mode
            this.currentBook = null;
            this.currentChapter = null;

            // Load commentary for all chapters (deduplicated)
            const uniqueChapters = [...new Map(chaptersToLoadCommentary.map(c => [c.ref, c])).values()];
            for (const chapterInfo of uniqueChapters) {
                try {
                    const commentaryResponse = await fetch(
                        `/api/passage/${encodeURIComponent(chapterInfo.ref)}/commentary`
                    );
                    if (commentaryResponse.ok) {
                        const commentaryData = await commentaryResponse.json();
                        if (commentaryData.entries && commentaryData.entries.length > 0) {
                            // Add book/chapter context to each entry
                            const entriesWithContext = commentaryData.entries.map(entry => ({
                                ...entry,
                                _sourceBook: chapterInfo.book,
                                _sourceChapter: chapterInfo.chapter,
                                _sourceRef: chapterInfo.ref
                            }));
                            allCommentary = allCommentary.concat(entriesWithContext);
                        }
                    }
                } catch (err) {
                    console.error(`Failed to load commentary for ${chapterInfo.ref}:`, err);
                }
            }
            this.commentary = allCommentary;
            this.combinedCommentary = allCommentary;  // Store for restoration after verse deselect

            // Load interlinear data for all chapters
            this.interlinearData = {};
            for (const chapterInfo of uniqueChapters) {
                try {
                    const interlinearResponse = await fetch(
                        `/api/passage/${encodeURIComponent(chapterInfo.ref)}/interlinear?translation=${this.translation}`
                    );
                    if (interlinearResponse.ok) {
                        const interlinearData = await interlinearResponse.json();
                        if (interlinearData.has_interlinear && interlinearData.verses) {
                            // Store with compound key: book|chapter|verse
                            for (const [verseNum, words] of Object.entries(interlinearData.verses)) {
                                const key = `${chapterInfo.book}|${chapterInfo.chapter}|${verseNum}`;
                                this.interlinearData[key] = {
                                    language: interlinearData.language,
                                    words: words
                                };
                            }
                        }
                    }
                } catch (err) {
                    console.error(`Failed to load interlinear for ${chapterInfo.ref}:`, err);
                }
            }

            // Setup scroll-based verse tracking
            this.$nextTick(() => {
                this.observeVerses();
            });

            // Update URL to reflect plan reading state
            this.updateURL();
        },

        exitPlanReadingMode() {
            this.planReadingMode = false;
            this.combinedPlanReading = false;
            this.wasInPlanReading = false;
            this.planReadings = [];
            this.planReadingSections = [];
            this.planReadingChapters = [];
            // Go back to plan view if a plan is active, otherwise load Genesis 1
            if (this.currentPlan) {
                this.showReadingPlan = true;
            } else {
                this.referenceInput = 'Genesis 1';
                this.loadPassage();
            }
        },

        // Return to plan reading after navigating away (e.g., clicking a cross-ref)
        returnToPlanReading() {
            this.wasInPlanReading = false;
            this.startPlanReading();
        },

        markPlanDayAndContinue() {
            if (!this.isDayCompleted(this.planDay)) {
                this.toggleDayComplete(this.planDay);
            }

            // Move to next day or show completion
            if (this.planDay < (this.currentPlan?.duration_days || 365)) {
                this.planDay++;
                this.startPlanReading();
            } else {
                this.exitPlanReadingMode();
                this.showToast('Plan complete! Congratulations!', 'success');
            }
        },

        // Navigate to a specific passage from the plan (opens in reader)
        goToPlanPassage(ref) {
            this.showReadingPlan = false;
            this.planReadingMode = false;
            this.referenceInput = ref;
            this.loadPassage();
        },

        formatPlanDate(planId) {
            if (!this.planProgress[planId]?.startDate) return '';
            const date = new Date(this.planProgress[planId].startDate);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        }
    };
}
