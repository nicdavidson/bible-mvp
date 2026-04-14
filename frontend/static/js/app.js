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
function escapeHtml(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}

function linkifyBibleReferences(text) {
    if (!text) return '';

    // Escape HTML first to prevent XSS from user-provided content
    text = escapeHtml(text);

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
        crossRefSort: 'biblical',  // 'biblical' or 'relevance'
        crossRefFilter: '',        // book name filter
        // Nave's Topical Index
        verseTopics: [],           // topics for current verse
        topicSearchQuery: '',
        topicSearchResults: [],
        topicDetail: null,         // currently viewed topic
        topicBrowseSection: null,  // A-Z filter
        topicBrowseList: [],
        topicSections: {},         // { A: 123, B: 45, ... }
        topicLoading: false,
        notes: [],
        currentNote: '',
        selectedWord: null,
        showAllOccurrences: false,
        loading: false,
        loadingCommentary: false,
        error: null,
        darkMode: false,
        currentTheme: 'light',
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

        // Sidebar collapse state (tablet/desktop)
        sidebarCollapsed: localStorage.getItem('sidebarCollapsed') === 'true',

        // Interlinear data
        interlinearData: {},  // verse number -> words array
        showInterlinear: false,
        interlinearLanguage: '',  // 'hebrew' or 'greek'
        interlinearSourceText: '',  // Source text label (e.g., "Westminster Leningrad Codex")
        sourceTextWarningDismissed: localStorage.getItem('sourceTextWarningDismissed') === 'true',

        // Verse sharing state
        shareMode: false,
        shareSelectedVerses: [],
        showShareModal: false,
        shareBackgroundIndex: 0,
        shareImagePreview: null,

        // Side menu state
        showSideMenu: false,
        currentView: 'reader',  // 'reader', 'plans'

        // Modal states
        showSettings: false,
        showGuide: false,
        showAbout: false,
        showFeedback: false,
        showShareJesus: false,
        settingsTab: 'general',

        // Path to Christ modal
        showPathToChrist: false,
        pathToChrist: [],
        pathToChristLoading: false,
        pathToChristError: null,
        pathToChristHops: 0,

        // Immersive reading mode
        immersiveMode: false,
        immersiveControlsVisible: false,
        immersiveControlsTimeout: null,
        immersiveTouchStartX: 0,
        immersiveHintShown: false,
        // Swipe navigation in normal reading mode
        _swipeStartX: 0,
        _swipeStartY: 0,

        // Single Verse View (reusable component)
        singleVerseMode: false,
        singleVerseList: [],  // Array of { ref: 'John 3:16' }
        singleVerseIndex: 1,
        singleVerseText: '',
        singleVerseLoading: false,
        singleVersePrompt: '',  // Optional prompt text shown above verse
        singleVerseOnFinish: null,  // Callback when done
        singleVerseFullPassage: false,  // When viewing full passage from single verse mode

        // Share Jesus verses
        shareJesusVerses: [
            { ref: 'Romans 3:23' },
            { ref: 'Romans 6:23' },
            { ref: 'John 3:3' },
            { ref: 'John 14:6' },
            { ref: 'Romans 10:9-11' },
            { ref: '2 Corinthians 5:15' },
            { ref: 'Revelation 3:20' }
        ],
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

        // Highlight picker state (uses tag system for storage)
        showHighlightPicker: null,  // verse number showing color picker
        highlightColors: ['#fef08a', '#bbf7d0', '#bfdbfe', '#fbcfe8', '#fed7aa', '#e9d5ff'],

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
        activeCommentarySource: null,  // Currently selected source tab
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

        // Reading history state
        readingHistory: JSON.parse(localStorage.getItem('readingHistory') || '[]'),

        // Bookmarks state
        bookmarks: JSON.parse(localStorage.getItem('bible-bookmarks') || '[]'),

        // Scripture Memory state
        showMemoryTool: false,
        memoryVerses: JSON.parse(localStorage.getItem('memoryVerses') || '[]'),
        memoryActiveCard: null,  // index in memoryDueCards
        memoryStage: 'prompt',   // 'prompt', 'firstLetters', 'blanks', 'reveal'
        memoryDueCards: [],      // computed subset of memoryVerses that are due for review
        memoryShowAnswer: false,

        // Parallel translation state
        parallelMode: false,
        parallelDiffMode: false,
        parallelTranslations: ['BSB', 'KJV', 'WEB'],
        parallelData: {},

        // Text-to-Speech state
        ttsPlaying: false,
        ttsPaused: false,
        ttsCurrentVerse: null,  // Verse number currently being spoken
        ttsRate: parseFloat(localStorage.getItem('ttsRate') || '1.0'),
        ttsVoice: localStorage.getItem('ttsVoice') || '',
        ttsAvailableVoices: [],
        _ttsUtterance: null,
        _ttsVerseQueue: [],
        _ttsQueueIndex: 0,

        // Initialize
        async init() {
            // Detect touch device
            this.isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

            // Load preferences from localStorage
            // Load theme (supports legacy darkMode boolean and new theme system)
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme) {
                this.currentTheme = savedTheme;
                this.darkMode = savedTheme === 'dark';
            } else {
                // Legacy migration: convert old darkMode boolean to new theme system
                this.darkMode = localStorage.getItem('darkMode') === 'true';
                this.currentTheme = this.darkMode ? 'dark' : 'light';
                localStorage.setItem('theme', this.currentTheme);
            }
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

            // Initialize TTS voices
            this.initTTS();

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
                            // Auto-scroll commentary when freely scrolling (no verse explicitly selected)
                            clearTimeout(this._commentaryScrollTimeout);
                            this._commentaryScrollTimeout = setTimeout(() => {
                                if (this.activeTab === 'commentary' && this.highlightedVerses.length === 0) {
                                    this.scrollCommentaryToVerse(verseNum);
                                }
                            }, 300);
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
                        if (this.immersiveMode) {
                            this.exitImmersiveMode();
                        } else {
                            this.showSearch = false;
                            this.showSettings = false;
                            this.selectedWord = null;
                        }
                        break;
                    case 'f':
                        if (this.currentReference && !this.immersiveMode) {
                            this.enterImmersiveMode();
                        }
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
                    case ' ':
                        // Space = play/pause TTS
                        if (this.ttsPlaying) {
                            e.preventDefault();
                            this.ttsPaused ? this.ttsPlay() : this.ttsPause();
                        } else if (this.currentReference) {
                            e.preventDefault();
                            this.ttsPlay();
                        }
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

            // Dismiss mobile keyboard
            this.$refs.referenceInput?.blur();

            // Stop TTS when navigating to new passage
            if (this.ttsPlaying) this.ttsStop();

            this.loading = true;
            this.error = null;
            this.selectedWord = null;

            // Parse book/chapter from input BEFORE fetch so offline fallback has correct values
            const refMatch = this.referenceInput.match(/^(.+?)\s+(\d+)/);
            const inputBook = refMatch ? refMatch[1] : this.referenceInput;
            const inputChapter = refMatch ? parseInt(refMatch[2]) : 1;

            // If forced offline, skip fetch entirely and go straight to IndexedDB
            if (this.forcedOffline) {
                await this._loadFromCache(inputBook, inputChapter);
                return;
            }

            // Cache-first: if auto-cache is on and we have cached data, show it instantly
            // then refresh from API in the background
            if (this.autoCacheEnabled && window.offlineStorage) {
                try {
                    const cached = await window.offlineStorage.getChapterVerses(
                        this.translation, inputBook, inputChapter
                    );
                    if (cached && cached.length > 0) {
                        // Show cached data immediately
                        this.verses = cached.map(v => ({ verse: v.verse, text: v.text }));
                        this.currentReference = `${inputBook} ${inputChapter}`;
                        this.parseCurrentReference();
                        this.crossRefs = [];
                        this.highlightedVerses = [];
                        this.speakerVerses = [];
                        this.updateURL(true);
                        this.observeVerses();
                        this.loading = false;

                        // Load cached commentary/interlinear/cross-refs
                        await this.loadCommentary();
                        await this.loadInterlinearData();
                        try {
                            const cachedRefs = await window.offlineStorage.getChapterCrossRefs(inputBook, inputChapter);
                            if (cachedRefs?.length > 0) this.crossRefs = cachedRefs;
                        } catch (e) { /* silent */ }

                        // Background refresh from API (fire-and-forget)
                        this._backgroundRefresh(inputBook, inputChapter);
                        return;
                    }
                } catch (e) {
                    // Cache check failed, fall through to normal fetch
                }
            }

            try {
                const response = await fetch(
                    `/api/passage/${encodeURIComponent(this.referenceInput)}?translation=${this.translation}`
                );

                if (!response.ok) {
                    let detail = 'Failed to load passage';
                    try { const data = await response.json(); detail = data.detail || detail; } catch {}
                    throw new Error(detail);
                }

                const data = await response.json();
                this.currentReference = data.reference;
                this.verses = data.verses;
                this.crossRefs = data.cross_references || [];
                this.highlightedVerses = data.highlighted_verses || [];
                this.speakerVerses = data.speaker_verses || [];

                // Parse reference for navigation
                this.parseCurrentReference();

                // Track in reading history
                this.addToHistory(this.currentReference, this.translation);

                // Update URL with clean path format (new chapter = new history entry)
                this.updateURL(true);

                // Load commentary
                await this.loadCommentary();

                // Load interlinear data if available
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

                // Load parallel data if parallel mode is active
                if (this.parallelMode) {
                    this.loadParallelPassage();
                }

                // Auto-cache: save to IndexedDB for offline use
                if (this.autoCacheEnabled && window.offlineStorage && this.currentBook && this.currentChapter) {
                    this._autoCacheCurrentChapter();
                }

            } catch (err) {
                // Network failed — try IndexedDB fallback
                await this._loadFromCache(inputBook, inputChapter, err.message);
            } finally {
                this.loading = false;
            }
        },

        // Load passage from IndexedDB cache (used by offline fallback and forced offline mode)
        async _loadFromCache(book, chapter, errorMsg = null) {
            if (!window.offlineStorage) {
                this.error = errorMsg || 'Offline storage not available';
                this.verses = [];
                this.loading = false;
                return;
            }
            try {
                const cached = await window.offlineStorage.getChapterVerses(
                    this.translation, book, chapter
                );
                if (cached && cached.length > 0) {
                    this.verses = cached.map(v => ({ verse: v.verse, text: v.text }));
                    this.currentReference = `${book} ${chapter}`;
                    this.parseCurrentReference();
                    this.crossRefs = [];
                    this.highlightedVerses = [];
                    this.speakerVerses = [];
                    this.updateURL(true);
                    this.observeVerses();

                    // Load cached cross-refs
                    try {
                        const cachedRefs = await window.offlineStorage.getChapterCrossRefs(book, chapter);
                        if (cachedRefs?.length > 0) this.crossRefs = cachedRefs;
                    } catch (e) { /* silent */ }

                    // Load cached commentary and interlinear
                    await this.loadCommentary();
                    await this.loadInterlinearData();

                    this.error = null;
                    this.showToast('Loaded from offline cache', 'info');
                } else {
                    this.error = `${book} ${chapter} is not cached for offline use. Read it while online first, or download from Settings.`;
                    this.verses = [];
                }
            } catch (cacheErr) {
                console.error('IndexedDB fallback failed:', cacheErr);
                this.error = errorMsg || 'Failed to load from cache';
                this.verses = [];
            } finally {
                this.loading = false;
            }
        },

        // Background refresh: fetch fresh data from API and update cache (does not update UI unless data changed significantly)
        async _backgroundRefresh(book, chapter) {
            try {
                const ref = `${book} ${chapter}`;
                const response = await fetch(
                    `/api/passage/${encodeURIComponent(ref)}?translation=${this.translation}`
                );
                if (!response.ok) return;
                const data = await response.json();

                // Update cross-refs and speaker data silently (these aren't cached initially)
                if (data.cross_references?.length > 0) {
                    this.crossRefs = data.cross_references;
                }
                if (data.speaker_verses?.length > 0) {
                    this.speakerVerses = data.speaker_verses;
                }

                // Re-cache the fresh data
                if (window.offlineStorage) {
                    this._autoCacheCurrentChapter();
                }
            } catch (err) {
                // Silent — background refresh is best-effort
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

        // Toggle parallel translation mode
        toggleParallelMode() {
            this.parallelMode = !this.parallelMode;
            if (this.parallelMode) {
                this.loadParallelPassage();
            }
        },

        // Load parallel passage data for all selected translations
        async loadParallelPassage() {
            if (!this.currentBook || !this.currentChapter) return;
            const ref = `${this.currentBook} ${this.currentChapter}`;
            try {
                const response = await fetch(
                    `/api/passage/${encodeURIComponent(ref)}/parallel?translations=${this.parallelTranslations.join(',')}`
                );
                if (response.ok) {
                    const data = await response.json();
                    this.parallelData = data.translations;
                }
            } catch (err) {
                console.error('Failed to load parallel passage:', err);
            }
        },

        // Toggle a translation in parallel view
        toggleParallelTranslation(translationId) {
            const idx = this.parallelTranslations.indexOf(translationId);
            if (idx > -1) {
                if (this.parallelTranslations.length > 1) {
                    this.parallelTranslations.splice(idx, 1);
                }
            } else {
                this.parallelTranslations.push(translationId);
            }
            this.loadParallelPassage();
        },

        // Simple word-level diff between two texts (set-based)
        diffWords(textA, textB) {
            const wordsA = (textA || '').split(/\s+/).filter(Boolean);
            const wordsB = (textB || '').split(/\s+/).filter(Boolean);
            const normalize = w => w.toLowerCase().replace(/[.,;:!?'")\]]+$/, '').replace(/^['"(\[]+/, '');
            const setB = new Set(wordsB.map(normalize));
            const setA = new Set(wordsA.map(normalize));
            const markedA = wordsA.map(w => ({ word: w, diff: !setB.has(normalize(w)) }));
            const markedB = wordsB.map(w => ({ word: w, diff: !setA.has(normalize(w)) }));
            return { a: markedA, b: markedB };
        },

        // Get diff-highlighted HTML for a verse in a given translation
        getParallelDiffHtml(verseNum, translationId) {
            const translations = this.parallelTranslations;
            const currentVerse = (this.parallelData[translationId] || []).find(v => v.verse === verseNum);
            if (!currentVerse) return '\u2014';
            if (translations.length < 2) return currentVerse.text;

            // Compare against primary (first) translation; if this IS primary, compare against second
            const compareId = translationId === translations[0] ? translations[1] : translations[0];
            const compareVerse = (this.parallelData[compareId] || []).find(v => v.verse === verseNum);
            if (!compareVerse) return currentVerse.text;

            const result = this.diffWords(currentVerse.text, compareVerse.text);
            return result.a.map(item =>
                item.diff
                    ? `<span class="diff-word">${item.word}</span>`
                    : item.word
            ).join(' ');
        },

        // Load commentary for current chapter (always full chapter for browsing)
        async loadCommentary() {
            if (!this.currentBook || !this.currentChapter) {
                this.commentary = [];
                return;
            }

            this.loadingCommentary = true;
            try {
                // When forced offline, go straight to cache
                if (this.forcedOffline) {
                    throw new Error('offline');
                }

                const chapterRef = `${this.currentBook} ${this.currentChapter}`;
                const response = await fetch(
                    `/api/passage/${encodeURIComponent(chapterRef)}/commentary`
                );

                if (response.ok) {
                    const data = await response.json();
                    this.commentary = data.entries || [];
                } else {
                    this.commentary = [];
                }
            } catch (err) {
                // Network failed or forced offline — try IndexedDB cache
                if (window.offlineStorage && this.currentBook && this.currentChapter) {
                    try {
                        const cached = await window.offlineStorage.getChapterCommentary(
                            this.currentBook, this.currentChapter
                        );
                        if (cached && cached.length > 0) {
                            this.commentary = cached;
                            return;
                        }
                    } catch (cacheErr) {
                        console.debug('Commentary cache fallback failed:', cacheErr);
                    }
                }
                this.commentary = [];
            } finally {
                this.loadingCommentary = false;
            }
        },

        // Get sorted and filtered cross-references
        getFilteredCrossRefs() {
            let refs = [...this.crossRefs];

            // Filter by book name
            if (this.crossRefFilter) {
                const filter = this.crossRefFilter.toLowerCase();
                refs = refs.filter(r => r.target_book.toLowerCase().includes(filter));
            }

            // Sort
            if (this.crossRefSort === 'relevance') {
                refs.sort((a, b) => (b.votes || 0) - (a.votes || 0));
            }
            // 'biblical' is the default order from API (target_book_order, chapter, verse)

            return refs;
        },

        // Get unique book names from current cross-refs (for filter suggestions)
        getCrossRefBooks() {
            const books = new Set(this.crossRefs.map(r => r.target_book));
            return [...books].sort();
        },

        // === Nave's Topical Index ===

        async loadTopicsForVerse(verseNum) {
            if (!this.currentBook || !this.currentChapter) return;
            try {
                const resp = await fetch(`/api/topics/for-verse?book=${encodeURIComponent(this.currentBook)}&chapter=${this.currentChapter}&verse=${verseNum}`);
                if (resp.ok) {
                    const data = await resp.json();
                    this.verseTopics = data.topics || [];
                }
            } catch (e) {
                console.error('Failed to load topics for verse:', e);
            }
        },

        async searchTopics() {
            const q = this.topicSearchQuery.trim();
            if (!q) { this.topicSearchResults = []; return; }
            this.topicLoading = true;
            try {
                const resp = await fetch(`/api/topics/search?q=${encodeURIComponent(q)}&limit=30`);
                if (resp.ok) {
                    const data = await resp.json();
                    this.topicSearchResults = data.results || [];
                    this.topicDetail = null;
                } else {
                    this.topicSearchResults = [];
                }
            } catch (e) {
                console.error('Failed to search topics:', e);
                this.topicSearchResults = [];
            } finally {
                this.topicLoading = false;
            }
        },

        async viewTopic(topicId) {
            this.topicLoading = true;
            try {
                const resp = await fetch(`/api/topics/${topicId}`);
                if (resp.ok) {
                    this.topicDetail = await resp.json();
                } else {
                    this.topicDetail = null;
                }
            } catch (e) {
                console.error('Failed to load topic:', e);
                this.topicDetail = null;
            } finally {
                this.topicLoading = false;
            }
        },

        async browseTopics(section) {
            this.topicBrowseSection = section;
            this.topicLoading = true;
            this.topicDetail = null;
            this.topicSearchQuery = '';
            this.topicSearchResults = [];
            try {
                const resp = await fetch(`/api/topics/browse?section=${section}&per_page=200`);
                if (resp.ok) {
                    const data = await resp.json();
                    this.topicBrowseList = data.topics || [];
                    this.topicSections = data.sections || {};
                } else {
                    this.topicBrowseList = [];
                }
            } catch (e) {
                console.error('Failed to browse topics:', e);
                this.topicBrowseList = [];
            } finally {
                this.topicLoading = false;
            }
        },

        async initTopicSections() {
            if (Object.keys(this.topicSections).length > 0) return;
            try {
                const resp = await fetch('/api/topics/browse?per_page=1');
                if (resp.ok) {
                    const data = await resp.json();
                    this.topicSections = data.sections || {};
                }
            } catch (e) { /* silent */ }
        },

        topicBackToList() {
            this.topicDetail = null;
        },

        formatTopicEntry(text) {
            if (!text) return '';
            const bookMap = {
                'GEN':'Genesis','EXO':'Exodus','LEV':'Leviticus','NUM':'Numbers',
                'DEU':'Deuteronomy','JOS':'Joshua','JDG':'Judges','RUT':'Ruth',
                '1SA':'1 Samuel','2SA':'2 Samuel','1KI':'1 Kings','2KI':'2 Kings',
                '1CH':'1 Chronicles','2CH':'2 Chronicles','EZR':'Ezra','NEH':'Nehemiah',
                'EST':'Esther','JOB':'Job','PSA':'Psalms','PRO':'Proverbs',
                'ECC':'Ecclesiastes','ISA':'Isaiah','JER':'Jeremiah','LAM':'Lamentations',
                'EZK':'Ezekiel','DAN':'Daniel','HOS':'Hosea','JOL':'Joel','AMO':'Amos',
                'OBA':'Obadiah','JON':'Jonah','MIC':'Micah','NAM':'Nahum','NAH':'Nahum',
                'HAB':'Habakkuk','ZEP':'Zephaniah','HAG':'Haggai','ZEC':'Zechariah',
                'MAL':'Malachi','MAT':'Matthew','MRK':'Mark','LUK':'Luke','JHN':'John',
                'ACT':'Acts','ROM':'Romans','1CO':'1 Corinthians','2CO':'2 Corinthians',
                'GAL':'Galatians','EPH':'Ephesians','PHP':'Philippians','COL':'Colossians',
                '1TH':'1 Thessalonians','2TH':'2 Thessalonians','1TI':'1 Timothy',
                '2TI':'2 Timothy','TIT':'Titus','PHM':'Philemon','HEB':'Hebrews',
                'JAS':'James','1PE':'1 Peter','2PE':'2 Peter','1JN':'1 John',
                '2JN':'2 John','3JN':'3 John','JDE':'Jude','REV':'Revelation'
            };
            // Convert -SubTopic headings to styled lines
            let html = text.replace(/^-/gm, '<br>&#x2022; ')
                          .replace(/\n/g, '<br>')
                          .replace(/\s{5,}/g, '<br>&nbsp;&nbsp;&nbsp;');
            // Make verse references clickable using data-ref (same pattern as commentary)
            html = html.replace(
                /([A-Z1-3][A-Z]{1,4})\s+(\d+):(\d+)/g,
                (match, abbr, ch, vs) => {
                    const book = bookMap[abbr];
                    if (!book) return match;
                    return `<a href="#" class="topic-ref-link" data-ref="${book} ${ch}:${vs}">${match}</a>`;
                }
            );
            return html;
        },

        // Handle clicks on Bible reference links in topic entries (event delegation)
        handleTopicClick(event) {
            const link = event.target.closest('.topic-ref-link');
            if (link) {
                event.preventDefault();
                const ref = link.dataset.ref;
                if (ref) this.loadReference(ref);
            }
        },

        goToTopicRef(ref) {
            if (!ref || !ref.book || !ref.chapter || !ref.verse_start) return;
            const vs = ref.verse_start;
            const ve = ref.verse_end && ref.verse_end !== vs ? ref.verse_end : null;
            const refStr = ve ? `${ref.book} ${ref.chapter}:${vs}-${ve}` : `${ref.book} ${ref.chapter}:${vs}`;
            this.loadReference(refStr);
        },

        // Check if a commentary entry applies to the active verse
        commentaryMatchesActiveVerse(entry) {
            const activeVerse = this.getActiveVerse();
            if (!activeVerse) return true;  // If no active verse, all match
            const start = entry.reference_start || 1;
            const end = entry.reference_end || start;
            return activeVerse >= start && activeVerse <= end;
        },

        // Auto-scroll commentary panel to the entry matching a verse number
        scrollCommentaryToVerse(verseNum) {
            if (!verseNum) return;
            const entries = document.querySelectorAll('.commentary-entry[data-verse-start]');
            let targetEntry = null;
            let bestPreceding = null;
            for (const el of entries) {
                const start = parseInt(el.dataset.verseStart) || 0;
                const end = parseInt(el.dataset.verseEnd) || start;
                if (verseNum >= start && verseNum <= end) {
                    targetEntry = el;
                    break;
                }
                // Track closest preceding entry as fallback
                if (start <= verseNum) {
                    bestPreceding = el;
                }
            }
            const scrollTarget = targetEntry || bestPreceding;
            if (scrollTarget) {
                const panelBody = scrollTarget.closest('.panel-body');
                if (panelBody) {
                    const entryTop = scrollTarget.offsetTop - panelBody.offsetTop;
                    panelBody.scrollTo({ top: entryTop - 10, behavior: 'smooth' });
                }
            }
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
            if (this.loading) return;
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
            if (this.loading) return;
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
            this.loadCrossRefsForVerse(verseNum);

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
        async loadCrossRefsForVerse(verseNum) {
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
                // Network failed — try IndexedDB cache
                if (window.offlineStorage && this.currentBook && this.currentChapter) {
                    try {
                        const cached = await window.offlineStorage.getChapterCrossRefs(
                            this.currentBook, this.currentChapter, verseNum, verseNum
                        );
                        if (cached && cached.length > 0) {
                            this.crossRefs = cached;
                            return;
                        }
                    } catch (cacheErr) {
                        console.error('Cross-refs cache fallback failed:', cacheErr);
                    }
                }
                console.error('Failed to load cross-refs:', err);
            }
        },

        // Handle click on verse box - select verse unless clicking a word
        async handleVerseBoxClick(event, verseNum, verseIdx) {
            // Skip if long-press just fired (prevents double-action)
            if (this._longPressTriggered) {
                this._longPressTriggered = false;
                return;
            }

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

        // Get ordered list of unique commentary sources
        getCommentarySources() {
            const sources = [];
            const seen = new Set();
            for (const entry of this.commentary) {
                const source = entry.source || 'Unknown';
                if (!seen.has(source)) {
                    seen.add(source);
                    sources.push(source);
                }
            }
            return sources;
        },

        // Get the currently active commentary source (defaults to first)
        getActiveCommentarySource() {
            const sources = this.getCommentarySources();
            if (sources.length === 0) return null;
            if (this.activeCommentarySource && sources.includes(this.activeCommentarySource)) {
                return this.activeCommentarySource;
            }
            return sources[0];
        },

        // Get commentary entries for the active source tab
        getActiveSourceEntries() {
            const activeSource = this.getActiveCommentarySource();
            if (!activeSource) return [];
            return this.commentary.filter(e => (e.source || 'Unknown') === activeSource);
        },

        // Switch active commentary source tab
        switchCommentarySource(source) {
            this.activeCommentarySource = source;
            const activeVerse = this.getActiveVerse();
            if (activeVerse) {
                this.$nextTick(() => this.scrollCommentaryToVerse(activeVerse));
            }
        },

        // Group commentary entries by source (kept for combined plan reading mode)
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

        // Check if a commentary entry is expanded (active entries auto-expand)
        isCommentaryEntryExpanded(entry, idx) {
            // Active verse entries are always expanded
            if (this.commentaryMatchesActiveVerse(entry)) return true;
            // Check manual expansion state
            const key = (entry.source || '') + '-' + idx;
            return this._expandedCommentaryEntries?.[key] === true;
        },

        // Toggle a commentary entry's expanded state
        toggleCommentaryEntry(entry, idx) {
            if (!this._expandedCommentaryEntries) this._expandedCommentaryEntries = {};
            const key = (entry.source || '') + '-' + idx;
            // If it's the active verse, clicking should navigate to that verse
            if (this.commentaryMatchesActiveVerse(entry)) {
                if (entry.reference_start) this.selectVerseFromRef(entry.reference_start);
                return;
            }
            this._expandedCommentaryEntries[key] = !this._expandedCommentaryEntries[key];
        },

        // Get preview text for a single commentary entry
        getCommentaryEntryPreview(entry) {
            const content = entry.content || '';
            const plainText = content.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
            if (plainText.length <= 100) return plainText;
            const truncated = plainText.substring(0, 100);
            const lastSpace = truncated.lastIndexOf(' ');
            return truncated.substring(0, lastSpace > 60 ? lastSpace : 100).trim() + '...';
        },

        // Clear verse selection (dismiss action bar)
        clearVerseSelection() {
            if (this.highlightedVerses.length === 0) return;
            this.highlightedVerses = [];
            this.selectedWord = null;
            this.showHighlightPicker = null;
            document.querySelectorAll('.word.selected').forEach(el => el.classList.remove('selected'));

            if (this.combinedPlanReading) {
                this.currentBook = null;
                this.currentChapter = null;
                this.currentReference = null;
                this.crossRefs = this.combinedCrossRefs;
                this.commentary = this.combinedCommentary;
            } else if (this.currentBook && this.currentChapter) {
                this.currentReference = `${this.currentBook} ${this.currentChapter}`;
                this.referenceInput = this.currentReference;
                this.updateURL();
            }
        },

        // Get label for the floating action bar (e.g. "v3" or "v3-5" or "v1, v4")
        getSelectionLabel() {
            const vv = [...this.highlightedVerses].sort((a, b) => a - b);
            if (vv.length === 0) return '';
            if (vv.length === 1) return `v${vv[0]}`;
            // Check if contiguous range
            const isContiguous = vv.every((v, i) => i === 0 || v === vv[i - 1] + 1);
            if (isContiguous) return `v${vv[0]}-${vv[vv.length - 1]}`;
            return vv.map(v => `v${v}`).join(', ');
        },

        // Open the notes panel with selected verses pre-filled
        openNoteForSelected() {
            const vv = [...this.highlightedVerses].sort((a, b) => a - b);
            if (vv.length === 0) return;

            // Switch to notes tab and expand the resources panel
            this.activeTab = 'notes';
            this.resourcesPanelExpanded = true;

            // Pre-fill the verse selection for the note
            this.noteEditMode = true;
            this.selectedVerses = vv;

            // Focus the textarea after panel animates open
            this.$nextTick(() => {
                const ta = document.querySelector('.note-textarea');
                if (ta) ta.focus();
            });
        },

        // Add all selected verses to memory
        memorizeSelected() {
            this.highlightedVerses.forEach(v => {
                if (!this.isInMemory(v)) this.addToMemory(v);
            });
        },

        // Copy all selected verses as a block
        copySelected() {
            const vv = [...this.highlightedVerses].sort((a, b) => a - b);
            const lines = vv.map(vNum => {
                const verse = this.verses.find(v => v.verse === vNum);
                if (!verse) return '';
                const text = verse.text.replace(/<[^>]*>/g, '');
                return `${vNum} ${text}`;
            }).filter(Boolean);
            const ref = vv.length === 1
                ? `${this.currentBook} ${this.currentChapter}:${vv[0]}`
                : `${this.currentBook} ${this.currentChapter}:${vv[0]}-${vv[vv.length - 1]}`;
            const fullText = `${ref}\n${lines.join('\n')}`;
            navigator.clipboard.writeText(fullText).then(() => {
                this.copyFeedback = true;
                setTimeout(() => { this.copyFeedback = false; }, 2000);
            });
        },

        // Highlight all selected verses with a color
        async highlightSelectedVerses(color) {
            for (const v of this.highlightedVerses) {
                await this.quickHighlight(v, color);
            }
            this.showHighlightPicker = null;
        },

        // Remove highlight from all selected verses
        async removeHighlightSelected() {
            for (const v of this.highlightedVerses) {
                await this.removeVerseHighlight(v);
            }
            this.showHighlightPicker = null;
        },

        // Select a specific verse (click on verse box) - supports multi-select
        // verseIdx is optional and used in combined mode to identify the exact verse
        async selectVerse(verseNum, verseIdx) {
            // If this verse is already the only highlighted verse, deselect it
            if (this.highlightedVerses.length === 1 && this.highlightedVerses[0] === verseNum) {
                this.clearVerseSelection();
                return;
            }

            // Multi-select: if already have selection, add/remove this verse
            if (this.highlightedVerses.length > 0 && this.highlightedVerses.includes(verseNum)) {
                // Remove from selection
                this.highlightedVerses = this.highlightedVerses.filter(v => v !== verseNum);
                return;
            }

            if (this.highlightedVerses.length > 0) {
                // Add to selection
                this.highlightedVerses = [...this.highlightedVerses, verseNum];
                return;
            }

            // New single selection
            this.highlightedVerses = [verseNum];
            this.selectedWord = null;
            this.showHighlightPicker = null;

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

                    // Load cross-refs, commentary, and topics for just this verse
                    await this.loadCrossRefs();
                    await this.loadCommentary();
                    this.loadTopicsForVerse(verseNum);
                    this.$nextTick(() => this.scrollCommentaryToVerse(verseNum));
                }
                return;
            }

            // Update reference display
            this.currentReference = `${this.currentBook} ${this.currentChapter}:${verseNum}`;
            this.referenceInput = this.currentReference;

            // Update URL
            this.updateURL();

            // Reload cross-references, commentary, and topics for the selected verse
            await this.loadCrossRefs();
            await this.loadCommentary();
            this.loadTopicsForVerse(verseNum);
            this.$nextTick(() => this.scrollCommentaryToVerse(verseNum));
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
                } else {
                    this.crossRefs = [];
                }
            } catch (err) {
                // Network failed — try IndexedDB cache
                if (window.offlineStorage && this.currentBook && this.currentChapter) {
                    try {
                        const cached = await window.offlineStorage.getChapterCrossRefs(
                            this.currentBook, this.currentChapter
                        );
                        if (cached && cached.length > 0) {
                            this.crossRefs = cached;
                            return;
                        }
                    } catch (cacheErr) {
                        console.error('Cross-refs cache fallback failed:', cacheErr);
                    }
                }
                console.error('Failed to load cross-refs:', err);
                this.crossRefs = [];
            }
        },

        async findPathToChrist() {
            if (!this.currentBook || !this.highlightedVerses.length) return;
            const verseNum = this.highlightedVerses[0];
            const ref = `${this.currentBook} ${this.currentChapter}:${verseNum}`;

            this.pathToChristLoading = true;
            this.pathToChristError = null;
            this.pathToChrist = [];
            this.showPathToChrist = true;

            try {
                const resp = await fetch(
                    `/api/path-to-christ/${encodeURIComponent(ref)}?translation=${this.translation}`
                );
                if (!resp.ok) {
                    const body = await resp.json().catch(() => ({}));
                    throw new Error(body.detail || 'Failed to find path');
                }
                const data = await resp.json();
                if (data.found) {
                    this.pathToChrist = data.path;
                    this.pathToChristHops = data.hops;
                } else {
                    this.pathToChristError = `No cross-reference path found from ${ref} to Christ within 6 hops.`;
                }
            } catch (err) {
                console.error('Path to Christ error:', err);
                this.pathToChristError = err.message || 'Could not find a path. Please try again.';
            } finally {
                this.pathToChristLoading = false;
            }
        },

        navigateFromPath(reference) {
            this.showPathToChrist = false;
            this.loadReference(reference);
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
                // When forced offline, go straight to cache
                if (this.forcedOffline) {
                    throw new Error('offline');
                }

                const ref = `${this.currentBook} ${this.currentChapter}`;
                const response = await fetch(
                    `/api/passage/${encodeURIComponent(ref)}/interlinear?translation=${this.translation}`
                );

                if (response.ok) {
                    const data = await response.json();
                    if (data.has_interlinear && data.verses) {
                        this.interlinearLanguage = data.language;
                        this.interlinearSourceText = data.source_text || '';
                        for (const [verseNum, words] of Object.entries(data.verses)) {
                            this.interlinearData[parseInt(verseNum)] = {
                                language: data.language,
                                words: words
                            };
                        }
                    } else {
                        this.interlinearSourceText = '';
                    }
                }
            } catch (err) {
                // Network failed or forced offline — try IndexedDB cache
                if (window.offlineStorage && this.currentBook && this.currentChapter) {
                    try {
                        const cached = await window.offlineStorage.getChapterInterlinear(
                            this.currentBook, this.currentChapter
                        );
                        if (cached && cached.length > 0) {
                            const lang = OT_BOOKS.includes(this.currentBook) ? 'hebrew' : 'greek';
                            this.interlinearLanguage = lang;
                            const byVerse = {};
                            for (const word of cached) {
                                if (!byVerse[word.verse]) byVerse[word.verse] = [];
                                byVerse[word.verse].push(word);
                            }
                            for (const [verseNum, words] of Object.entries(byVerse)) {
                                this.interlinearData[parseInt(verseNum)] = {
                                    language: lang,
                                    words: words
                                };
                            }
                            return;
                        }
                    } catch (cacheErr) {
                        console.debug('Interlinear cache fallback failed:', cacheErr);
                    }
                }
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
                    if (!response.ok) throw new Error('Word alignment not available');
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
                await this.loadWordDetails(word.strong_number, word);
            } else {
                this.selectedWord = {
                    text: word.original_text,
                    original: word.lexeme || word.original_text,
                    transliteration: word.transliteration || '---',
                    strong_number: null,
                    parsing: word.parsing || 'N/A',
                    definition: word.definition || 'No definition available',
                    editions: word.editions || null,
                    word_type: word.word_type || null,
                    occurrences: [],
                    count: 0
                };
            }
        },

        // Load word details by Strong's number
        async loadWordDetails(strongNumber, interlinearWord) {
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
                        editions: interlinearWord?.editions || null,
                        word_type: interlinearWord?.word_type || null,
                        occurrences: data.occurrences,
                        count: data.count,
                        glosses: data.glosses || [],
                        book_frequency: data.book_frequency || []
                    };
                }
            } catch (err) {
                console.error('Failed to load word details:', err);
            }
        },

        // Toggle sidebar collapsed state (tablet/desktop)
        toggleSidebar() {
            this.sidebarCollapsed = !this.sidebarCollapsed;
            localStorage.setItem('sidebarCollapsed', this.sidebarCollapsed);
        },

        // Toggle dark mode (keyboard shortcut 'D' cycles through themes)
        toggleDarkMode() {
            const themes = ['light', 'dark', 'parchment'];
            const currentIdx = themes.indexOf(this.currentTheme);
            const nextIdx = (currentIdx + 1) % themes.length;
            this.setTheme(themes[nextIdx]);
        },

        // Set theme ('light', 'dark', or 'parchment')
        setTheme(theme) {
            this.currentTheme = theme;
            this.darkMode = theme === 'dark';
            localStorage.setItem('theme', theme);
            localStorage.setItem('darkMode', this.darkMode);
        },

        // Save dark mode preference (legacy, kept for compatibility)
        saveDarkMode() {
            this.currentTheme = this.darkMode ? 'dark' : 'light';
            localStorage.setItem('darkMode', this.darkMode);
            localStorage.setItem('theme', this.currentTheme);
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

        // Immersive reading mode
        enterImmersiveMode() {
            if (!this.currentReference) return;
            this.immersiveMode = true;
            this.immersiveControlsVisible = false;
            if (document.documentElement.requestFullscreen) {
                document.documentElement.requestFullscreen().catch(() => {});
            }
            // Show hint briefly on first entry
            if (!this.immersiveHintShown) {
                this.immersiveHintShown = true;
                setTimeout(() => {
                    const hint = document.querySelector('.immersive-swipe-hint');
                    if (hint) hint.classList.add('fade-out');
                }, 3000);
            }
        },

        exitImmersiveMode() {
            this.immersiveMode = false;
            clearTimeout(this.immersiveControlsTimeout);
            if (document.fullscreenElement) {
                document.exitFullscreen().catch(() => {});
            }
        },

        toggleImmersiveControls() {
            this.immersiveControlsVisible = !this.immersiveControlsVisible;
            clearTimeout(this.immersiveControlsTimeout);
            if (this.immersiveControlsVisible) {
                this.immersiveControlsTimeout = setTimeout(() => {
                    this.immersiveControlsVisible = false;
                }, 4000);
            }
        },

        immersiveTouchStart(e) {
            this.immersiveTouchStartX = e.changedTouches[0].screenX;
        },

        immersiveTouchEnd(e) {
            const diff = e.changedTouches[0].screenX - this.immersiveTouchStartX;
            if (Math.abs(diff) > 80) {
                if (diff > 0) this.previousChapter();
                else this.nextChapter();
            }
        },

        // Swipe navigation for normal reading mode
        readingTouchStart(e) {
            this._swipeStartX = e.changedTouches[0].screenX;
            this._swipeStartY = e.changedTouches[0].screenY;
        },

        readingTouchEnd(e) {
            if (!this.currentReference || this.highlightedVerses.length > 0) return;
            const dx = e.changedTouches[0].screenX - this._swipeStartX;
            const dy = e.changedTouches[0].screenY - this._swipeStartY;
            // Only trigger on horizontal swipes (dx > dy) with enough distance
            if (Math.abs(dx) > 80 && Math.abs(dx) > Math.abs(dy) * 1.5) {
                if (dx > 0) this.previousChapter();
                else this.nextChapter();
            }
        },

        // Long-press on verse — selects verse and shows action bar
        _longPressTimer: null,
        _longPressTriggered: false,

        startLongPress(verseNum, verseIdx) {
            this._longPressTriggered = false;
            this._longPressTimer = setTimeout(() => {
                this._longPressTriggered = true;
                // Vibrate if available
                if (navigator.vibrate) navigator.vibrate(30);
                // Select the verse (shows action bar)
                this.selectVerse(verseNum, verseIdx);
            }, 500);
        },

        cancelLongPress() {
            if (this._longPressTimer) {
                clearTimeout(this._longPressTimer);
                this._longPressTimer = null;
            }
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

        // ========== Text-to-Speech (Audio Read-Along) ==========

        initTTS() {
            if (!('speechSynthesis' in window)) return;

            const loadVoices = () => {
                const voices = speechSynthesis.getVoices();
                // Prefer English voices
                this.ttsAvailableVoices = voices.filter(v => v.lang.startsWith('en'));
                if (this.ttsAvailableVoices.length === 0) this.ttsAvailableVoices = voices;

                // Restore saved voice preference
                if (this.ttsVoice) {
                    const match = this.ttsAvailableVoices.find(v => v.name === this.ttsVoice);
                    if (!match) this.ttsVoice = '';
                }
            };

            loadVoices();
            if (speechSynthesis.onvoiceschanged !== undefined) {
                speechSynthesis.onvoiceschanged = loadVoices;
            }
        },

        ttsGetVerseTexts() {
            // Build ordered array of {verseNum, text} from current passage
            if (!this.verses || this.verses.length === 0) return [];
            return this.verses.map(v => ({
                verseNum: v.verse,
                text: v.text.replace(/<[^>]*>/g, '') // strip any HTML
            }));
        },

        ttsPlay(startVerse = null) {
            if (!('speechSynthesis' in window)) {
                this.showToast('Text-to-speech not supported in this browser', 'error');
                return;
            }

            // If paused, resume from current verse
            if (this.ttsPaused) {
                this.ttsPaused = false;
                this.ttsPlaying = true;
                this._ttsNextVerse();
                return;
            }

            // Stop any existing speech
            speechSynthesis.cancel();

            // Build queue
            this._ttsVerseQueue = this.ttsGetVerseTexts();
            if (this._ttsVerseQueue.length === 0) return;

            // Find start index
            if (startVerse) {
                this._ttsQueueIndex = this._ttsVerseQueue.findIndex(v => v.verseNum === startVerse);
                if (this._ttsQueueIndex < 0) this._ttsQueueIndex = 0;
            } else {
                this._ttsQueueIndex = 0;
            }

            this.ttsPlaying = true;
            this.ttsPaused = false;
            this._ttsNextVerse();
        },

        _ttsNextVerse() {
            if (this._ttsQueueIndex >= this._ttsVerseQueue.length) {
                this.ttsStop();
                return;
            }

            const verse = this._ttsVerseQueue[this._ttsQueueIndex];
            this.ttsCurrentVerse = verse.verseNum;

            // Scroll the verse into view
            const verseEl = document.getElementById(`verse-${verse.verseNum}`);
            if (verseEl) {
                verseEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }

            const utterance = new SpeechSynthesisUtterance(verse.text);
            utterance.rate = this.ttsRate;

            // Set voice
            if (this.ttsVoice) {
                const voice = this.ttsAvailableVoices.find(v => v.name === this.ttsVoice);
                if (voice) utterance.voice = voice;
            }

            utterance.onend = () => {
                // Don't advance if we were paused (cancel triggers onend in some browsers)
                if (this.ttsPaused) return;
                this._ttsQueueIndex++;
                if (this.ttsPlaying) {
                    this._ttsNextVerse();
                }
            };

            utterance.onerror = (e) => {
                if (e.error !== 'canceled') {
                    console.warn('TTS error:', e.error);
                    this._ttsQueueIndex++;
                    if (this.ttsPlaying) this._ttsNextVerse();
                }
            };

            this._ttsUtterance = utterance;
            speechSynthesis.speak(utterance);
        },

        ttsPause() {
            if (this.ttsPlaying && !this.ttsPaused) {
                // speechSynthesis.pause() is unreliable in Chrome/Chromium
                // Instead, cancel and track position so we can resume from same verse
                // Set ttsPaused BEFORE cancel() to prevent the onend handler from
                // advancing to the next verse (onend can fire synchronously in some browsers)
                this.ttsPaused = true;
                this.ttsPlaying = true;  // still "playing" (paused state)
                speechSynthesis.cancel();
            }
        },

        ttsStop() {
            speechSynthesis.cancel();
            this.ttsPlaying = false;
            this.ttsPaused = false;
            this.ttsCurrentVerse = null;
            this._ttsUtterance = null;
            this._ttsVerseQueue = [];
            this._ttsQueueIndex = 0;
        },

        ttsSetRate(rate) {
            this.ttsRate = parseFloat(rate);
            localStorage.setItem('ttsRate', this.ttsRate);

            // If currently playing, restart current verse with new rate
            if (this.ttsPlaying) {
                const currentVerse = this.ttsCurrentVerse;
                speechSynthesis.cancel();
                this.ttsPaused = false;
                // Find current verse index and restart from there
                this._ttsQueueIndex = this._ttsVerseQueue.findIndex(v => v.verseNum === currentVerse);
                if (this._ttsQueueIndex < 0) this._ttsQueueIndex = 0;
                this._ttsNextVerse();
            }
        },

        ttsSetVoice(voiceName) {
            this.ttsVoice = voiceName;
            localStorage.setItem('ttsVoice', voiceName);

            // If currently playing, restart with new voice
            if (this.ttsPlaying) {
                const currentVerse = this.ttsCurrentVerse;
                speechSynthesis.cancel();
                this.ttsPaused = false;
                this._ttsQueueIndex = this._ttsVerseQueue.findIndex(v => v.verseNum === currentVerse);
                if (this._ttsQueueIndex < 0) this._ttsQueueIndex = 0;
                this._ttsNextVerse();
            }
        },

        ttsSkipForward() {
            if (!this.ttsPlaying) return;
            speechSynthesis.cancel();
            this.ttsPaused = false;
            this._ttsQueueIndex++;
            this._ttsNextVerse();
        },

        ttsSkipBack() {
            if (!this.ttsPlaying) return;
            speechSynthesis.cancel();
            this.ttsPaused = false;
            this._ttsQueueIndex = Math.max(0, this._ttsQueueIndex - 1);
            this._ttsNextVerse();
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

        // ========== Side Menu Navigation ==========

        // Navigate to a view from side menu
        navigateTo(view) {
            this.currentView = view;
            this.showSideMenu = false;

            if (view === 'reader') {
                // Exit plan reading mode and go back to normal Bible view
                this.exitPlanReading();
            } else if (view === 'plans') {
                this.openReadingPlan();
            }
        },

        // Exit plan reading mode and return to normal Bible view
        exitPlanReading() {
            this.combinedPlanReading = false;
            this.planReadingMode = false;
            this.wasInPlanReading = false;
            // Clear the combined reading data
            this.planReadingSections = [];
            this.planReadingChapters = [];
            this.combinedCrossRefs = [];
            this.combinedCommentary = [];
            this.combinedNotes = [];
            // Keep the current reference if we have one, otherwise go to welcome view
            if (!this.currentBook) {
                this.verses = [];
            }
        },

        // Open settings from side menu
        openSettingsFromMenu(tab = 'general') {
            this.showSideMenu = false;
            this.openSettings(tab);
        },

        // Open Guide modal
        openGuide() {
            this.showSideMenu = false;
            this.showGuide = true;
        },

        // Open About modal
        openAbout() {
            this.showSideMenu = false;
            this.showAbout = true;
        },

        // Open Feedback modal from About
        openFeedbackFromAbout() {
            this.showAbout = false;
            this.showFeedback = true;
        },

        // Open Share Jesus modal
        openShareJesus() {
            this.showSideMenu = false;
            this.showShareJesus = true;
        },

        // Go to verse from Share Jesus modal
        goToVerseFromModal(ref) {
            this.showShareJesus = false;
            this.exitPlanReading();
            this.referenceInput = ref;
            this.loadPassage();
        },

        // ========== Single Verse View (Reusable) ==========

        // Open single verse view with a list of verses
        async openSingleVerseView(verses, options = {}) {
            this.singleVerseList = verses;
            this.singleVerseIndex = 1;
            this.singleVersePrompt = options.prompt || '';
            this.singleVerseOnFinish = options.onFinish || null;
            this.singleVerseMode = true;
            await this.loadSingleVerse(1);
        },

        // Get current verse info
        getCurrentSingleVerse() {
            return this.singleVerseList[this.singleVerseIndex - 1] || { ref: '' };
        },

        // Load verse text from API
        async loadSingleVerse(index) {
            const verse = this.singleVerseList[index - 1];
            if (!verse) return;

            this.singleVerseLoading = true;
            this.singleVerseText = '';

            try {
                const response = await fetch(`/api/passage/${encodeURIComponent(verse.ref)}?translation=${this.translation}`);
                if (response.ok) {
                    const data = await response.json();
                    // Filter to only the highlighted (requested) verses, not the full chapter
                    const highlightedVerses = data.highlighted_verses || [];
                    const filteredVerses = highlightedVerses.length > 0
                        ? data.verses.filter(v => highlightedVerses.includes(v.verse))
                        : data.verses;
                    this.singleVerseText = filteredVerses.map(v => v.text).join(' ');
                }
            } catch (err) {
                console.error('Failed to load verse:', err);
                this.singleVerseText = 'Failed to load verse. Please try again.';
            } finally {
                this.singleVerseLoading = false;
            }
        },

        // Navigate to next verse
        async nextSingleVerse() {
            if (this.singleVerseIndex < this.singleVerseList.length) {
                this.singleVerseIndex++;
                await this.loadSingleVerse(this.singleVerseIndex);
            }
        },

        // Navigate to previous verse
        async prevSingleVerse() {
            if (this.singleVerseIndex > 1) {
                this.singleVerseIndex--;
                await this.loadSingleVerse(this.singleVerseIndex);
            }
        },

        // Go to specific verse
        async goToSingleVerse(index) {
            this.singleVerseIndex = index;
            await this.loadSingleVerse(index);
        },

        // Exit single verse mode
        exitSingleVerseMode() {
            this.singleVerseMode = false;
            if (this.singleVerseOnFinish) {
                this.singleVerseOnFinish();
            }
        },

        // Finish viewing all verses
        finishSingleVerseMode() {
            this.singleVerseMode = false;
            this.singleVerseFullPassage = false;
            if (this.singleVerseOnFinish) {
                this.singleVerseOnFinish();
            }
        },

        // View full passage from single verse mode
        async viewFullPassageFromSingleVerse() {
            const verse = this.getCurrentSingleVerse();
            if (!verse) return;

            // Hide single verse overlay and show full passage bar
            this.singleVerseMode = false;
            this.singleVerseFullPassage = true;

            // Navigate to the passage with the verse highlighted
            this.referenceInput = verse.ref;
            await this.loadPassage();
        },

        // Return to single verse mode from full passage view
        returnToSingleVerseMode() {
            this.singleVerseFullPassage = false;
            this.singleVerseMode = true;
        },

        // ========== Share Jesus Functions ==========

        // Start Share Jesus verse presentation
        startShareJesusVerses() {
            this.showShareJesus = false;
            this.openSingleVerseView(this.shareJesusVerses, {
                prompt: 'Have them read aloud, then ask: "What does this say to you?"',
                onFinish: () => { this.showShareJesus = true; }
            });
        },

        // Open Today's Reading
        openTodaysReading() {
            this.showSideMenu = false;
            // If we have an active plan, go directly to today's reading
            if (this.currentPlan) {
                const today = this.getTodaysPlanDay();
                if (today) {
                    this.planDay = today;
                    this.startPlanReading();
                } else {
                    // Fallback to opening the reading plan modal
                    this.openReadingPlan();
                }
            } else {
                // No active plan - open the reading plan picker
                this.openReadingPlan();
            }
        },

        // Get today's day number in the current plan (wrapper for side menu)
        getTodaysPlanDay() {
            if (!this.currentPlan) return null;
            // Use the existing function that takes planId
            return this.getTodaysPlanDayForPlan(this.currentPlan.id);
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
            if (this.searchDebounceTimer) {
                clearTimeout(this.searchDebounceTimer);
                this.searchDebounceTimer = null;
            }
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
            // Filter to current chapter, exclude highlight-only notes (no content)
            const chapterNotes = this.notes.filter(note =>
                this.noteInCurrentChapter(note) && (note.content?.trim())
            );

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
        // usePush=true creates a new history entry (for chapter navigation);
        // usePush=false uses replaceState (for verse selection within same chapter)
        updateURL(usePush = false) {
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

            if (usePush) {
                window.history.pushState({}, '', path);
            } else {
                window.history.replaceState({}, '', path);
            }
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

        // Dismiss source text warning
        dismissSourceTextWarning() {
            this.sourceTextWarningDismissed = true;
            localStorage.setItem('sourceTextWarningDismissed', 'true');
        },

        // Get reading progress percentage
        getReadingProgress() {
            if (!this.verses.length || !this.highlightedVerses.length) return 0;
            const currentVerse = this.highlightedVerses[0];
            const maxVerse = Math.max(...this.verses.map(v => v.verse));
            return Math.round((currentVerse / maxVerse) * 100);
        },

        // ========== VERSE SHARING METHODS ==========

        shareBackgrounds: [
            { name: 'Sunset', colors: ['#667eea', '#764ba2'] },
            { name: 'Ocean', colors: ['#2193b0', '#6dd5ed'] },
            { name: 'Dark', colors: ['#1a1a2e', '#16213e'] },
            { name: 'Light', colors: ['#f5f7fa', '#c3cfe2'] },
        ],

        toggleShareMode() {
            this.shareMode = !this.shareMode;
            this.shareSelectedVerses = [];
        },

        toggleShareVerse(verseNum) {
            const idx = this.shareSelectedVerses.indexOf(verseNum);
            if (idx > -1) this.shareSelectedVerses.splice(idx, 1);
            else this.shareSelectedVerses.push(verseNum);
            this.shareSelectedVerses.sort((a, b) => a - b);
        },

        getShareVerseText() {
            if (this.shareSelectedVerses.length === 0) return '';
            return this.shareSelectedVerses.map(vn => {
                const verse = this.verses.find(v => v.verse === vn);
                return verse ? verse.text : '';
            }).filter(Boolean).join(' ');
        },

        getShareReference() {
            if (this.shareSelectedVerses.length === 0) return '';
            const first = this.shareSelectedVerses[0];
            const last = this.shareSelectedVerses[this.shareSelectedVerses.length - 1];
            if (first === last) {
                return `${this.currentBook} ${this.currentChapter}:${first}`;
            }
            return `${this.currentBook} ${this.currentChapter}:${first}-${last}`;
        },

        getShareLink() {
            if (this.shareSelectedVerses.length === 0) return '';
            const first = this.shareSelectedVerses[0];
            const last = this.shareSelectedVerses[this.shareSelectedVerses.length - 1];
            const bookPath = this.currentBook.replace(/\s+/g, '-');
            if (first === last) {
                return `${window.location.origin}/${bookPath}/${this.currentChapter}/${first}`;
            }
            return `${window.location.origin}/${bookPath}/${this.currentChapter}/${first}-${last}`;
        },

        openShareModal() {
            if (this.shareSelectedVerses.length === 0) return;
            this.showShareModal = true;
            this.shareImagePreview = null;
            this.$nextTick(() => this.generateVerseImagePreview());
        },

        async copyShareText() {
            const text = `"${this.getShareVerseText()}" — ${this.getShareReference()} (${this.translation})`;
            try {
                await navigator.clipboard.writeText(text);
                this.showToast('Verse text copied', 'success');
            } catch (err) {
                console.error('Failed to copy:', err);
            }
        },

        async copyShareLink() {
            try {
                await navigator.clipboard.writeText(this.getShareLink());
                this.showToast('Link copied', 'success');
            } catch (err) {
                console.error('Failed to copy link:', err);
            }
        },

        async nativeShare() {
            if (!navigator.share) return;
            try {
                await navigator.share({
                    title: this.getShareReference(),
                    text: `"${this.getShareVerseText()}" — ${this.getShareReference()}`,
                    url: this.getShareLink()
                });
            } catch (err) {
                if (err.name !== 'AbortError') {
                    console.error('Share failed:', err);
                }
            }
        },

        generateVerseImagePreview() {
            const canvas = document.getElementById('share-canvas');
            if (!canvas) return;

            const ctx = canvas.getContext('2d');
            const bg = this.shareBackgrounds[this.shareBackgroundIndex];
            const isDark = this.shareBackgroundIndex >= 2; // Dark and Light (Light uses dark text)
            const isLight = this.shareBackgroundIndex === 3;

            canvas.width = 1080;
            canvas.height = 1080;

            // Draw gradient background
            const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
            gradient.addColorStop(0, bg.colors[0]);
            gradient.addColorStop(1, bg.colors[1]);
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // Text color
            const textColor = isLight ? '#1a1a2e' : '#ffffff';
            const subtextColor = isLight ? '#4a5568' : 'rgba(255,255,255,0.8)';
            const brandColor = isLight ? '#6b7280' : 'rgba(255,255,255,0.5)';

            // Word wrap helper
            function wrapText(ctx, text, maxWidth) {
                const words = text.split(' ');
                const lines = [];
                let currentLine = '';
                for (const word of words) {
                    const testLine = currentLine ? currentLine + ' ' + word : word;
                    if (ctx.measureText(testLine).width > maxWidth && currentLine) {
                        lines.push(currentLine);
                        currentLine = word;
                    } else {
                        currentLine = testLine;
                    }
                }
                if (currentLine) lines.push(currentLine);
                return lines;
            }

            const verseText = this.getShareVerseText();
            const reference = this.getShareReference() + ' (' + this.translation + ')';
            const padding = 80;
            const maxWidth = canvas.width - padding * 2;

            // Determine font size based on text length
            let fontSize = 42;
            if (verseText.length > 400) fontSize = 30;
            else if (verseText.length > 250) fontSize = 34;
            else if (verseText.length > 150) fontSize = 38;

            // Draw verse text
            ctx.font = `${fontSize}px Georgia, "Times New Roman", serif`;
            ctx.fillStyle = textColor;
            ctx.textAlign = 'center';

            const lines = wrapText(ctx, `"${verseText}"`, maxWidth);
            const lineHeight = fontSize * 1.5;
            const totalTextHeight = lines.length * lineHeight;
            const startY = (canvas.height - totalTextHeight) / 2 - 30;

            lines.forEach((line, i) => {
                ctx.fillText(line, canvas.width / 2, startY + i * lineHeight);
            });

            // Draw reference
            ctx.font = `28px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
            ctx.fillStyle = subtextColor;
            ctx.fillText(reference, canvas.width / 2, startY + totalTextHeight + 40);

            // Draw branding
            ctx.font = `18px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
            ctx.fillStyle = brandColor;
            ctx.fillText('In the Word', canvas.width / 2, canvas.height - 40);

            this.shareImagePreview = canvas.toDataURL('image/png');
        },

        selectShareBackground(index) {
            this.shareBackgroundIndex = index;
            this.generateVerseImagePreview();
        },

        async downloadShareImage() {
            const canvas = document.getElementById('share-canvas');
            if (!canvas) return;

            canvas.toBlob((blob) => {
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${this.getShareReference().replace(/[\s:]/g, '-')}.png`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                this.showToast('Image downloaded', 'success');
            }, 'image/png');
        },

        async shareImage() {
            if (!navigator.share || !navigator.canShare) return;
            const canvas = document.getElementById('share-canvas');
            if (!canvas) return;

            canvas.toBlob(async (blob) => {
                const file = new File([blob], 'verse.png', { type: 'image/png' });
                if (navigator.canShare({ files: [file] })) {
                    try {
                        await navigator.share({
                            files: [file],
                            title: this.getShareReference(),
                            text: this.getShareReference()
                        });
                    } catch (err) {
                        if (err.name !== 'AbortError') {
                            console.error('Share image failed:', err);
                        }
                    }
                }
            }, 'image/png');
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

        // Auto-cache the current chapter data to IndexedDB (fire-and-forget)
        async _autoCacheCurrentChapter() {
            const os = window.offlineStorage;
            const book = this.currentBook;
            const ch = this.currentChapter;
            const trans = this.translation;
            try {
                // Save verses
                if (this.verses?.length > 0) {
                    await os.saveChapterVerses(trans, book, ch, this.verses);
                }
                // Save cross-refs
                if (this.crossRefs?.length > 0) {
                    await os.saveChapterCrossRefs(book, ch, this.crossRefs);
                }
                // Save commentary
                if (this.commentary?.length > 0) {
                    await os.saveChapterCommentary(book, ch, this.commentary);
                }
                // Save interlinear
                if (Object.keys(this.interlinearData).length > 0) {
                    const words = [];
                    for (const [verseNum, data] of Object.entries(this.interlinearData)) {
                        for (const w of data.words || []) {
                            words.push({ ...w, verse: parseInt(verseNum) });
                        }
                    }
                    if (words.length > 0) {
                        await os.saveChapterInterlinear(book, ch, words);
                    }
                }
            } catch (err) {
                // Silent failure — auto-cache is best-effort
                console.debug('Auto-cache failed:', err);
            }
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

                        // Save cross-refs (API returns camelCase "crossRefs")
                        if (data.crossRefs?.length > 0) {
                            await window.offlineStorage.saveChapterCrossRefs(book, ch, data.crossRefs);
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

                // Update stats after each book so the UI shows progress
                await this.updateOfflineStats();
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
                            // Group entries by chapter for efficient saving
                            const byChapter = {};
                            for (const entry of entries) {
                                const ch = entry.chapter || 1;
                                if (!byChapter[ch]) byChapter[ch] = [];
                                byChapter[ch].push(entry);
                            }
                            for (const [ch, chEntries] of Object.entries(byChapter)) {
                                await window.offlineStorage.saveChapterCommentary(book, parseInt(ch), chEntries);
                            }
                        }
                    }
                } catch (err) {
                    console.warn(`Failed to download commentary for ${book}:`, err);
                }

                booksDownloaded++;
                const taskProgress = (booksDownloaded / books.length) * (100 / totalTasks);
                this.downloadProgress.percent = Math.round(basePercent + taskProgress);

                // Update stats every 5 books so the UI shows progress
                if (booksDownloaded % 5 === 0) await this.updateOfflineStats();

                await new Promise(r => setTimeout(r, 50));
            }
            await this.updateOfflineStats();
        },

        // Download all devotionals
        async downloadDevotionals(basePercent, totalTasks, source) {
            this.downloadProgress.label = `Downloading ${source} devotionals...`;
            this.downloadProgress.status = 'Fetching all entries...';

            try {
                const response = await fetch(`/api/offline/devotionals?source=${encodeURIComponent(source)}`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.entries?.length > 0) {
                        // Store devotionals in localStorage — devotional entries are small
                        // enough that localStorage is appropriate, and IndexedDB doesn't
                        // have a dedicated devotionals store
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

                // Update stats every 5 books so the UI shows progress
                if (booksDownloaded % 5 === 0) await this.updateOfflineStats();

                await new Promise(r => setTimeout(r, 50));
            }
            await this.updateOfflineStats();
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
                        const today = this.getTodaysPlanDayForPlan(planId);
                        this.planDay = Math.max(1, Math.min(today || 1, this.currentPlan.duration_days));
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

        getTodaysPlanDayForPlan(planId) {
            if (!this.planProgress[planId]?.startDate) return null;

            // Append T00:00:00 to ensure local timezone parsing (not UTC)
            const dateStr = this.planProgress[planId].startDate;
            const startDate = new Date(dateStr.includes('T') ? dateStr : dateStr + 'T00:00:00');
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
            const today = this.getTodaysPlanDayForPlan(this.currentPlan.id);
            if (today) {
                this.planDay = today;
            }
        },

        // Normalize book names (e.g., "Psalm" -> "Psalms")
        normalizeBookName(book) {
            // Handle common abbreviations and variations
            const normalizations = {
                'Psalm': 'Psalms',
                'Song of Songs': 'Song of Solomon',
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
            // Match book name at the start (including numbered books like "1 Chron.")
            const match = ref.match(/^(\d?\s*[A-Za-z][A-Za-z.\s]*?)(\s+\d.*)$/);
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
            const dateStr = this.planProgress[planId].startDate;
            const date = new Date(dateStr.includes('T') ? dateStr : dateStr + 'T00:00:00');
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        },

        // ========== VERSE HIGHLIGHTING (via tags) ==========

        getVerseHighlightColor(verseNum) {
            // Returns the first tag color on this verse (used for background)
            const colors = this.getVerseTagColors(verseNum);
            return colors.length > 0 ? colors[0] : null;
        },

        toggleHighlightPicker(verseNum) {
            this.showHighlightPicker = this.showHighlightPicker === verseNum ? null : verseNum;
        },

        async quickHighlight(verseNum, color) {
            if (!this.currentBook || !this.currentChapter) return;
            this.showHighlightPicker = null;

            // Find or create a tag with this color
            let tag = this.tags.find(t => t.color === color);
            if (!tag) {
                // Auto-create a highlight tag for this color
                const colorNames = {
                    '#fef08a': 'Yellow', '#bbf7d0': 'Green', '#bfdbfe': 'Blue',
                    '#fbcfe8': 'Pink', '#fed7aa': 'Orange', '#e9d5ff': 'Purple'
                };
                const name = colorNames[color] || 'Highlight';
                const tagData = { name, color };
                try {
                    if (this.authUser && window.SupabaseAuth) {
                        tag = await window.SupabaseAuth.createUserTag(name, color);
                        this.tags.push(tag);
                    } else {
                        tag = { id: Date.now(), ...tagData, sortOrder: this.tags.length, synced: false };
                        this.tags.push(tag);
                        localStorage.setItem('bible-tags', JSON.stringify(this.tags));
                    }
                } catch (err) {
                    console.error('Failed to create tag:', err);
                    return;
                }
            }

            // Check if verse already has a note with this tag — if so, remove it (toggle off)
            const existingNote = this.notes.find(n =>
                n.book === this.currentBook &&
                n.chapter === this.currentChapter &&
                n.startVerse === verseNum &&
                (n.endVerse || n.startVerse) === verseNum &&
                (this.noteTags[n.id] || []).includes(tag.id)
            );
            if (existingNote) {
                await this.toggleNoteTag(existingNote.id, tag.id);
                // If the note has no content and no tags left, delete it
                const remainingTags = this.noteTags[existingNote.id] || [];
                if (!existingNote.content?.trim() && remainingTags.length === 0) {
                    await this.deleteNote(existingNote.id);
                }
                return;
            }

            // Check if verse already has a highlight note (no content) — add tag to it
            const emptyNote = this.notes.find(n =>
                n.book === this.currentBook &&
                n.chapter === this.currentChapter &&
                n.startVerse === verseNum &&
                (n.endVerse || n.startVerse) === verseNum &&
                !n.content?.trim()
            );
            if (emptyNote) {
                // Clear existing tags on this empty note, apply new color
                const currentTagIds = this.noteTags[emptyNote.id] || [];
                for (const tid of currentTagIds) {
                    await this.toggleNoteTag(emptyNote.id, tid);
                }
                await this.toggleNoteTag(emptyNote.id, tag.id);
                return;
            }

            // Create a minimal note (empty content) with the tag
            const noteData = {
                book: this.currentBook,
                chapter: this.currentChapter,
                startVerse: verseNum,
                endVerse: verseNum,
                content: ''
            };
            try {
                let savedNoteId;
                if (this.authUser && window.SupabaseAuth) {
                    const savedNote = await window.SupabaseAuth.saveUserNote(noteData);
                    this.notes.unshift(savedNote);
                    savedNoteId = savedNote.id;
                } else {
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
                await this.toggleNoteTag(savedNoteId, tag.id);
            } catch (err) {
                console.error('Failed to create highlight:', err);
            }
        },

        async removeVerseHighlight(verseNum) {
            // Remove all tag-only (empty content) notes on this verse
            const toRemove = this.notes.filter(n =>
                n.book === this.currentBook &&
                n.chapter === this.currentChapter &&
                n.startVerse === verseNum &&
                (n.endVerse || n.startVerse) === verseNum &&
                !n.content?.trim()
            );
            for (const note of toRemove) {
                await this.deleteNote(note.id);
            }
            this.showHighlightPicker = null;
        },

        // ========== EXPORT NOTES ==========

        exportNotes() {
            const relevant = this.getRelevantNotes();
            if (relevant.length === 0) {
                this.showToast('No notes to export', 'info');
                return;
            }
            const header = this.combinedPlanReading
                ? `Study Notes — ${this.currentPlan?.name || 'Reading Plan'} Day ${this.planDay}`
                : `Study Notes — ${this.currentBook} ${this.currentChapter}`;

            let text = header + '\n' + '='.repeat(header.length) + '\n\n';
            for (const note of relevant) {
                const ref = this.formatNoteReference(note);
                text += `[${ref}]\n`;
                text += note.content + '\n';
                const tags = this.getNoteTagObjects(note.id);
                if (tags.length > 0) {
                    text += 'Tags: ' + tags.map(t => t.name).join(', ') + '\n';
                }
                text += '\n';
            }
            text += `Exported from In the Word — ${new Date().toLocaleDateString()}\n`;

            // Copy to clipboard
            navigator.clipboard.writeText(text).then(() => {
                this.showToast('Notes copied to clipboard', 'success');
            }).catch(() => {
                // Fallback: download as file
                const blob = new Blob([text], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `notes-${this.currentBook || 'study'}-${this.currentChapter || ''}.txt`;
                a.click();
                URL.revokeObjectURL(url);
                this.showToast('Notes downloaded', 'success');
            });
        },

        // ========== SCRIPTURE MEMORY ==========

        addToMemory(verseNum) {
            if (!this.currentBook || !this.currentChapter) return;
            const ref = `${this.currentBook} ${this.currentChapter}:${verseNum}`;
            if (this.memoryVerses.some(m => m.reference === ref)) {
                this.showToast('Already in memory verses', 'info');
                return;
            }
            const verseObj = this.verses.find(v => v.verse === verseNum);
            if (!verseObj) return;
            this.memoryVerses.push({
                reference: ref,
                text: verseObj.text,
                translation: this.translation,
                addedAt: Date.now(),
                // SM-2 spaced repetition fields
                interval: 1,      // days until next review
                ease: 2.5,        // easiness factor
                nextReview: Date.now(),  // due now
                reviewCount: 0
            });
            this.saveMemoryVerses();
            this.showToast('Added to memory verses', 'success');
        },

        isInMemory(verseNum) {
            if (!this.currentBook || !this.currentChapter) return false;
            const ref = `${this.currentBook} ${this.currentChapter}:${verseNum}`;
            return this.memoryVerses.some(m => m.reference === ref);
        },

        removeFromMemory(reference) {
            this.memoryVerses = this.memoryVerses.filter(m => m.reference !== reference);
            this.saveMemoryVerses();
        },

        saveMemoryVerses() {
            localStorage.setItem('memoryVerses', JSON.stringify(this.memoryVerses));
        },

        openMemoryTool() {
            this.showMemoryTool = true;
            this.showSideMenu = false;
            this.computeDueCards();
            this.memoryActiveCard = null;
            this.memoryStage = 'prompt';
            this.memoryShowAnswer = false;
        },

        computeDueCards() {
            const now = Date.now();
            this.memoryDueCards = this.memoryVerses.filter(m => m.nextReview <= now);
        },

        startMemoryReview() {
            this.computeDueCards();
            if (this.memoryDueCards.length === 0) {
                this.showToast('No verses due for review!', 'info');
                return;
            }
            this.memoryActiveCard = 0;
            this.memoryStage = 'prompt';
            this.memoryShowAnswer = false;
        },

        getCurrentMemoryCard() {
            if (this.memoryActiveCard === null || !this.memoryDueCards.length) return null;
            return this.memoryDueCards[this.memoryActiveCard];
        },

        getMemoryDisplay() {
            const card = this.getCurrentMemoryCard();
            if (!card) return '';
            const text = card.text;
            switch (this.memoryStage) {
                case 'prompt':
                    return '';  // show nothing — just the reference
                case 'firstLetters':
                    return text.split(/\s+/).map(w => {
                        if (!w) return '';
                        const first = w[0];
                        return first + w.slice(1).replace(/[a-zA-Z]/g, '_');
                    }).join(' ');
                case 'blanks':
                    return text.split(/\s+/).map(w => {
                        return w.replace(/[a-zA-Z]/g, '_');
                    }).join(' ');
                case 'reveal':
                    return text;
                default:
                    return '';
            }
        },

        advanceMemoryStage() {
            const stages = ['prompt', 'firstLetters', 'blanks', 'reveal'];
            const idx = stages.indexOf(this.memoryStage);
            if (idx < stages.length - 1) {
                this.memoryStage = stages[idx + 1];
            }
        },

        // SM-2 rating: 0 = forgot, 1 = hard, 2 = good, 3 = easy
        rateMemoryCard(quality) {
            const card = this.getCurrentMemoryCard();
            if (!card) return;
            // Find in main array
            const mainCard = this.memoryVerses.find(m => m.reference === card.reference);
            if (!mainCard) return;

            mainCard.reviewCount++;
            if (quality < 1) {
                // Failed — reset
                mainCard.interval = 1;
                mainCard.ease = Math.max(1.3, mainCard.ease - 0.2);
            } else {
                if (mainCard.reviewCount === 1) {
                    mainCard.interval = 1;
                } else if (mainCard.reviewCount === 2) {
                    mainCard.interval = 3;
                } else {
                    mainCard.interval = Math.round(mainCard.interval * mainCard.ease);
                }
                // Adjust ease
                mainCard.ease = Math.max(1.3, mainCard.ease + (quality === 3 ? 0.15 : quality === 2 ? 0 : -0.15));
            }
            mainCard.nextReview = Date.now() + (mainCard.interval * 86400000);
            this.saveMemoryVerses();

            // Advance to next card
            if (this.memoryActiveCard < this.memoryDueCards.length - 1) {
                this.memoryActiveCard++;
                this.memoryStage = 'prompt';
                this.memoryShowAnswer = false;
            } else {
                // Done with review
                this.memoryActiveCard = null;
                this.memoryStage = 'prompt';
                this.computeDueCards();
                this.showToast('Review complete!', 'success');
            }
        },

        getMemoryStats() {
            const now = Date.now();
            const due = this.memoryVerses.filter(m => m.nextReview <= now).length;
            const total = this.memoryVerses.length;
            const mastered = this.memoryVerses.filter(m => m.interval >= 21).length;
            return { due, total, mastered };
        },

        // ========== READING HISTORY ==========

        addToHistory(reference, translation) {
            if (!reference) return;
            const entry = {
                reference,
                translation: translation || this.translation,
                timestamp: Date.now()
            };
            // Remove duplicate if exists
            this.readingHistory = this.readingHistory.filter(h => h.reference !== reference);
            // Add to front
            this.readingHistory.unshift(entry);
            // Keep max 50 entries
            if (this.readingHistory.length > 50) this.readingHistory = this.readingHistory.slice(0, 50);
            localStorage.setItem('readingHistory', JSON.stringify(this.readingHistory));
        },

        clearHistory() {
            this.readingHistory = [];
            localStorage.setItem('readingHistory', JSON.stringify([]));
        },

        getRecentHistory(limit = 10) {
            return this.readingHistory.slice(0, limit);
        },

        formatHistoryTime(timestamp) {
            const diff = Date.now() - timestamp;
            const mins = Math.floor(diff / 60000);
            if (mins < 1) return 'Just now';
            if (mins < 60) return mins + 'm ago';
            const hours = Math.floor(mins / 60);
            if (hours < 24) return hours + 'h ago';
            const days = Math.floor(hours / 24);
            if (days < 7) return days + 'd ago';
            return new Date(timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        },

        // ========== BOOKMARKS ==========

        toggleBookmark(verseNum) {
            if (!this.currentBook || !this.currentChapter) return;
            const ref = `${this.currentBook} ${this.currentChapter}:${verseNum}`;
            const existing = this.bookmarks.findIndex(b => b.reference === ref);
            if (existing !== -1) {
                this.bookmarks.splice(existing, 1);
                this.showToast('Bookmark removed', 'info');
            } else {
                const verseObj = this.verses.find(v => v.verse === verseNum);
                this.bookmarks.unshift({
                    reference: ref,
                    book: this.currentBook,
                    chapter: this.currentChapter,
                    verse: verseNum,
                    preview: (verseObj?.text || '').substring(0, 80),
                    translation: this.translation,
                    timestamp: Date.now()
                });
                this.showToast('Verse bookmarked', 'success');
            }
            localStorage.setItem('bible-bookmarks', JSON.stringify(this.bookmarks));
        },

        isBookmarked(verseNum) {
            if (!this.currentBook || !this.currentChapter) return false;
            const ref = `${this.currentBook} ${this.currentChapter}:${verseNum}`;
            return this.bookmarks.some(b => b.reference === ref);
        },

        removeBookmark(reference) {
            this.bookmarks = this.bookmarks.filter(b => b.reference !== reference);
            localStorage.setItem('bible-bookmarks', JSON.stringify(this.bookmarks));
        },

        goToBookmark(bookmark) {
            this.loadReference(bookmark.reference);
        }
    };
}
