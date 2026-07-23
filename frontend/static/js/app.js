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

// Shared empty result for getVerseTagColors — avoids allocating a new array
// per call (it's hit several times per verse per render).
const EMPTY_COLORS = [];

// getRelevantNotes memo. Module scope (not Alpine state) so cache writes
// inside render effects don't register as reactive dependencies.
let _relevantNotesKey = null;
let _relevantNotesCache = [];

// Monotonic toast id — Date.now() collides for same-ms toasts (B11)
let _toastSeq = 0;

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

// Parse localStorage JSON without letting one corrupt value throw during
// Alpine init and blank the whole app.
function safeParse(key, fallback) {
    try {
        return JSON.parse(localStorage.getItem(key)) ?? fallback;
    } catch (e) {
        console.warn(`Corrupt localStorage value for ${key}, using fallback`, e);
        return fallback;
    }
}

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
    'Rth': 'Ruth', 'Rut': 'Ruth', 'Ru': 'Ruth',
    '1Sam': '1 Samuel', '1Sa': '1 Samuel', '1 Sam': '1 Samuel', '1 Sa': '1 Samuel',
    '2Sam': '2 Samuel', '2Sa': '2 Samuel', '2 Sam': '2 Samuel', '2 Sa': '2 Samuel',
    '1Kgs': '1 Kings', '1 Kgs': '1 Kings', '1Ki': '1 Kings', '1 Kings': '1 Kings', '1 Ki': '1 Kings',
    '2Kgs': '2 Kings', '2 Kgs': '2 Kings', '2Ki': '2 Kings', '2 Kings': '2 Kings', '2 Ki': '2 Kings',
    '1Chr': '1 Chronicles', '1Ch': '1 Chronicles', '1 Chr': '1 Chronicles', '1 Chron': '1 Chronicles',
    '2Chr': '2 Chronicles', '2Ch': '2 Chronicles', '2 Chr': '2 Chronicles', '2 Chron': '2 Chronicles',
    'Ezr': 'Ezra',
    'Neh': 'Nehemiah', 'Ne': 'Nehemiah',
    'Esth': 'Esther', 'Est': 'Esther', 'Es': 'Esther',
    'Psa': 'Psalms', 'Ps': 'Psalms', 'Psalm': 'Psalms',
    'Prov': 'Proverbs', 'Pro': 'Proverbs', 'Pr': 'Proverbs',
    'Eccl': 'Ecclesiastes', 'Ecc': 'Ecclesiastes', 'Ec': 'Ecclesiastes',
    'Song': 'Song of Solomon', 'Sol': 'Song of Solomon', 'So': 'Song of Solomon', 'SoS': 'Song of Solomon',
    'Song of Songs': 'Song of Solomon',
    'Isa': 'Isaiah', 'Is': 'Isaiah',
    'Jer': 'Jeremiah', 'Je': 'Jeremiah',
    'Lam': 'Lamentations', 'La': 'Lamentations',
    'Ezek': 'Ezekiel', 'Eze': 'Ezekiel', 'Ezk': 'Ezekiel',
    'Dan': 'Daniel', 'Da': 'Daniel', 'Dn': 'Daniel',
    'Hos': 'Hosea', 'Ho': 'Hosea',
    'Joe': 'Joel', 'Jol': 'Joel', 'Jl': 'Joel',
    'Am': 'Amos', 'Amo': 'Amos',
    'Obad': 'Obadiah', 'Oba': 'Obadiah', 'Ob': 'Obadiah',
    'Jon': 'Jonah', 'Jnh': 'Jonah',
    'Mic': 'Micah', 'Mi': 'Micah',
    'Nah': 'Nahum', 'Nam': 'Nahum', 'Na': 'Nahum',
    'Hab': 'Habakkuk',
    'Zeph': 'Zephaniah', 'Zep': 'Zephaniah',
    'Hag': 'Haggai',
    'Zech': 'Zechariah', 'Zec': 'Zechariah',
    'Mal': 'Malachi',
    // New Testament
    'Mat': 'Matthew', 'Matt': 'Matthew', 'Mt': 'Matthew',
    'Mar': 'Mark', 'Mrk': 'Mark', 'Mk': 'Mark', 'Mr': 'Mark',
    'Luk': 'Luke', 'Lk': 'Luke', 'Lu': 'Luke',
    'Joh': 'John', 'Jhn': 'John', 'Jn': 'John',
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
    'Jud': 'Jude', 'Jde': 'Jude',
    'Rev': 'Revelation', 'Re': 'Revelation'
};

// Add full book names to BOOK_ABBREVS for matching
BIBLE_BOOKS.forEach(book => {
    BOOK_ABBREVS[book] = book;
});

// Case-insensitive lookup derived from BOOK_ABBREVS — the single canonical
// book-name table (topic-index codes, print abbreviations, and full names).
const BOOK_NAME_LOOKUP = {};
Object.entries(BOOK_ABBREVS).forEach(([abbr, full]) => {
    BOOK_NAME_LOOKUP[abbr.toLowerCase()] = full;
});

// Normalize a book name or abbreviation to its canonical full name.
// Case-insensitive, strips a trailing period ("1 Chron." -> "1 Chronicles"),
// and passes unrecognized input through unchanged ("Psalms" -> "Psalms").
function normalizeBookName(book) {
    if (!book) return book;
    const key = String(book).trim().replace(/\.$/, '').toLowerCase();
    return BOOK_NAME_LOOKUP[key] || book;
}

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
    const core = {
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
        activeTab: 'study',
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
        homePickerBook: null,
        showChapterJump: false,

        // Bottom sheet drag state
        sheetDragStyle: '',
        _sheetStartY: 0,
        _sheetStartHeight: 0,
        _sheetDragging: false,
        sheetSnap: 'collapsed', // 'collapsed' | 'half' | 'full'

        // Verse preview tooltip
        versePreview: {
            show: false,
            reference: '',
            text: '',
            x: 0,
            y: 0
        },
        previewTimeout: null,
        _previewToken: 0,  // invalidates in-flight hover previews (B7)

        // Request generation: bumped on each navigation; async loaders capture
        // it at start and bail before assigning state if it changed (B4)
        _loadGeneration: 0,

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
        interlinearLoading: false,  // True while interlinear data is being fetched (lazy load)
        _interlinearRef: null,  // 'Book Chapter' the loaded interlinearData belongs to (null = not loaded)
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
        verseColorMap: {},  // Precomputed 'Book|Chapter|Verse' -> [tag colors] (max 3)
        noteDataVersion: 0,  // Bumped by rebuildVerseColorMap() to invalidate derived-note caches
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
        selectionContext: null,      // {book, chapter} the current selection belongs to (combined plan mode)
        planReadingSections: [],  // Section info for combined reading: [{label, reference, startIndex}]
        planReadingChapters: [],  // Chapters being read in combined mode: [{book, chapter}]
        wasInPlanReading: false,  // True when user navigated away from plan reading (for "return" button)
        combinedCrossRefs: [],  // Store all cross-refs for combined reading (to restore after verse deselect)
        combinedCommentary: [],  // Store all commentary for combined reading (to restore after verse deselect)
        combinedNotes: [],  // Store notes for combined reading chapters

        // Commentary grouping state
        activeCommentarySource: 'All',  // Currently selected commentary source tab
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
        readingHistory: safeParse('readingHistory', []),

        // Bookmarks state
        bookmarks: safeParse('bible-bookmarks', []),

        // Scripture Memory state
        showMemoryTool: false,
        memoryVerses: safeParse('memoryVerses', []),
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
            // Interlinear data is lazy-loaded (P3): fetch on first toggle-on
            this.$watch('showInterlinear', (on) => {
                if (on) this.ensureInterlinearLoaded();
            });
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
            this.setupHeaderAutoHide();

            // Recover from interrupted sheet drags (touchcancel bubbles to
            // document; template only binds touchstart/move/end) (B12)
            document.addEventListener('touchcancel', () => this.sheetTouchCancel(), { passive: true });

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
        // True when any modal/overlay is open — global shortcuts must not fire (B10).
        // Flags enumerated from modal-overlay / side-menu-overlay in index.html.
        anyModalOpen() {
            return this.showSearch || this.showSettings || this.showGuide
                || this.showAbout || this.showPathToChrist || this.showShareModal
                || this.showShareJesus || this.showFeedback || this.showReadingPlan
                || this.showMemoryTool || this.showSideMenu;
        },

        // Close the topmost open modal. Order: transient/stacked dialogs first
        // (share, path-to-christ open on top of the reader), then the big
        // full-screen tools, then the side menu.
        closeTopmostModal() {
            const flags = [
                'showPathToChrist', 'showShareModal', 'showShareJesus',
                'showFeedback', 'showSearch', 'showMemoryTool',
                'showReadingPlan', 'showSettings', 'showGuide', 'showAbout',
                'showSideMenu'
            ];
            for (const f of flags) {
                if (this[f]) { this[f] = false; return true; }
            }
            return false;
        },

        setupHeaderAutoHide() {
            // Mobile de-clutter: the reading pane (.panel-body) is the real
            // scroll container (window never scrolls — .panel-text is
            // viewport-capped). Hide the header scrolling down, reveal
            // scrolling up, and let the pane claim the freed height via
            // body.reading-immersed. Direct classList — no Alpine churn on
            // a per-scroll hot path.
            const header = document.querySelector('.header');
            const pane = document.querySelector('.panel-text .panel-body');
            if (!header || !pane) return;
            const mobile = window.matchMedia('(max-width: 900px)');
            const setH = () => document.documentElement.style.setProperty(
                '--header-h', header.offsetHeight + 'px');
            setH();
            window.addEventListener('resize', setH, { passive: true });
            let lastY = pane.scrollTop, ticking = false;
            pane.addEventListener('scroll', () => {
                if (ticking) return;
                ticking = true;
                requestAnimationFrame(() => {
                    ticking = false;
                    if (!mobile.matches) { document.body.classList.remove('reading-immersed'); return; }
                    const y = pane.scrollTop;
                    const delta = y - lastY;
                    lastY = y;
                    if (this.anyModalOpen && this.anyModalOpen()) return;
                    if (y < 60) document.body.classList.remove('reading-immersed');
                    else if (delta > 6) document.body.classList.add('reading-immersed');
                    else if (delta < -6) document.body.classList.remove('reading-immersed');
                });
            }, { passive: true });
        },

        setupKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
                // Ignore if typing in an input
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                    // But allow Escape to blur inputs
                    if (e.key === 'Escape') {
                        e.target.blur();
                        this.closeTopmostModal();
                        this.selectedWord = null;
                    }
                    return;
                }

                // While a modal is open, only Escape acts — it closes the
                // topmost modal. Everything else (d/f/arrows/space...) is
                // swallowed so shortcuts don't fire under modals (B10).
                if (this.anyModalOpen()) {
                    if (e.key === 'Escape') {
                        e.preventDefault();
                        this.closeTopmostModal();
                    }
                    return;
                }

                switch (e.key) {
                    case 'ArrowLeft':
                        if (this.currentReference) {
                            e.preventDefault();
                            if (this.immersiveMode && this.combinedPlanReading) this.immersivePlanPrev();
                            else this.previousChapter();
                        }
                        break;
                    case 'ArrowRight':
                        if (this.currentReference) {
                            e.preventDefault();
                            if (this.immersiveMode && this.combinedPlanReading) this.immersivePlanNext();
                            else this.nextChapter();
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
            // Match /Book/Chapter, /Book/Chapter/Verse, or /Book/Chapter/First-Last
            const match = path.match(/^\/([^\/]+)\/(\d+)(?:\/(\d+(?:-\d+)?))?$/);
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

        selectHomeBook(book) {
            const chapters = BOOK_CHAPTERS[book] || 1;
            if (chapters === 1) {
                this.homePickerBook = null;
                this.loadReference(book + ' 1');
            } else {
                this.homePickerBook = book;
            }
        },

        selectHomeChapter(ch) {
            const ref = this.homePickerBook + ' ' + ch;
            this.homePickerBook = null;
            this.loadReference(ref);
        },

        toggleChapterJump() {
            this.showChapterJump = !this.showChapterJump;
        },

        jumpToChapter(ch) {
            this.showChapterJump = false;
            this.loadReference(this.currentBook + ' ' + ch);
        },

        getChapterCount(book) {
            return this.bookChapters[book] || 1;
        },

        getChaptersArray(book) {
            const count = this.getChapterCount(book);
            return Array.from({ length: count }, (_, i) => i + 1);
        },

        // Bottom sheet drag for mobile resources panel
        sheetTouchStart(e) {
            if (window.innerWidth > 600) return;
            const panel = this.$refs.resourcesPanel;
            if (!panel) return;
            this._sheetDragging = true;
            this._sheetStartY = e.touches[0].clientY;
            this._sheetStartHeight = panel.offsetHeight;
            panel.style.transition = 'none';
        },

        sheetTouchMove(e) {
            if (!this._sheetDragging || window.innerWidth > 600) return;
            const dy = this._sheetStartY - e.touches[0].clientY;
            const newHeight = Math.max(48, Math.min(window.innerHeight - 40, this._sheetStartHeight + dy));
            const panel = this.$refs.resourcesPanel;
            if (!panel) return;
            panel.style.transform = 'none';
            panel.style.height = newHeight + 'px';
            panel.style.maxHeight = 'none';
            this.sheetDragStyle = '';
        },

        // OS interruption (call, notification shade, alert) fires touchcancel
        // instead of touchend — without this the sheet is left mid-drag with
        // transition:none stuck (B12). Bound via a document-level touchcancel
        // listener in init(); safe to also bind as @touchcancel in the template.
        sheetTouchCancel() {
            if (!this._sheetDragging) return;
            this._sheetDragging = false;
            const panel = this.$refs.resourcesPanel;
            if (panel) {
                panel.style.transition = '';
                panel.style.transform = '';
                panel.style.maxHeight = '';
                panel.style.height = '';
            }
            // Restore the last committed snap styling
            if (this.resourcesPanelExpanded && this.sheetSnap !== 'collapsed') {
                const max = this.sheetSnap === 'full' ? '90vh' : '50vh';
                this.sheetDragStyle = 'max-height: ' + max + '; transform: translateY(0)';
            } else {
                this.sheetDragStyle = '';
            }
        },

        sheetTouchEnd() {
            if (!this._sheetDragging || window.innerWidth > 600) return;
            this._sheetDragging = false;
            const panel = this.$refs.resourcesPanel;
            if (!panel) return;
            const h = panel.offsetHeight;
            const vh = window.innerHeight;
            // Snap points: collapsed (48px), half (50vh), full (90vh)
            const stops = [48, vh * 0.5, vh * 0.9];
            let closest = stops[0], dist = Math.abs(h - stops[0]);
            for (let i = 1; i < stops.length; i++) {
                const d = Math.abs(h - stops[i]);
                if (d < dist) { closest = stops[i]; dist = d; }
            }
            panel.style.transition = '';
            panel.style.transform = '';
            panel.style.maxHeight = '';
            if (closest <= 48) {
                this.resourcesPanelExpanded = false;
                this.sheetSnap = 'collapsed';
                panel.style.height = '';
                this.sheetDragStyle = '';
            } else {
                this.resourcesPanelExpanded = true;
                this.sheetSnap = closest > vh * 0.7 ? 'full' : 'half';
                panel.style.height = '';
                this.sheetDragStyle = 'max-height: ' + closest + 'px; transform: translateY(0)';
            }
        },

        sheetExpand() {
            if (window.innerWidth <= 600) {
                this.sheetSnap = 'half';
                this.sheetDragStyle = 'max-height: 50vh; transform: translateY(0)';
            }
        },

        sheetToggle() {
            if (window.innerWidth > 600) {
                this.resourcesPanelExpanded = !this.resourcesPanelExpanded;
                return;
            }
            if (!this.resourcesPanelExpanded || this.sheetSnap === 'collapsed') {
                this.resourcesPanelExpanded = true;
                this.sheetSnap = 'half';
                this.sheetDragStyle = 'max-height: 50vh; transform: translateY(0)';
            } else if (this.sheetSnap === 'half') {
                this.sheetSnap = 'full';
                this.sheetDragStyle = 'max-height: 90vh; transform: translateY(0)';
            } else {
                this.resourcesPanelExpanded = false;
                this.sheetSnap = 'collapsed';
                this.sheetDragStyle = '';
            }
        },

        // Load a passage
        async loadPassage() {
            if (!this.referenceInput.trim()) return;

            // Dismiss mobile keyboard
            this.$refs.referenceInput?.blur();
            this.showChapterJump = false;

            // Stop TTS when navigating to new passage
            if (this.ttsPlaying) this.ttsStop();

            this.loading = true;
            this.error = null;
            this.selectedWord = null;

            // Invalidate stale async loaders from prior navigations (B4)
            const gen = ++this._loadGeneration;

            // Parse book/chapter (and optional :verse or :start-end) from input
            // BEFORE fetch so offline fallback has correct values
            const refMatch = this.referenceInput.match(/^(.+?)\s+(\d+)(?::(\d+)(?:-(\d+))?)?/);
            const inputBook = refMatch ? refMatch[1] : this.referenceInput;
            const inputChapter = refMatch ? parseInt(refMatch[2]) : 1;
            const inputVerse = refMatch && refMatch[3] ? parseInt(refMatch[3]) : null;
            const inputVerseEnd = refMatch && refMatch[4]
                ? Math.max(inputVerse, parseInt(refMatch[4])) : inputVerse;

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
                        // Show cached data immediately (html precomputed once per assignment)
                        this.verses = cached.map(v => ({ verse: v.verse, text: v.text, html: this.formatVerseText(v.text) }));
                        // Preserve requested verse/range so cross-ref clicks keep
                        // their highlight on the cache-first path (B2)
                        if (inputVerse) {
                            const available = new Set(cached.map(v => v.verse));
                            const hv = [];
                            for (let v = inputVerse; v <= inputVerseEnd; v++) {
                                if (available.has(v)) hv.push(v);
                            }
                            this.highlightedVerses = hv;
                            this.currentReference = inputVerseEnd > inputVerse
                                ? `${inputBook} ${inputChapter}:${inputVerse}-${inputVerseEnd}`
                                : `${inputBook} ${inputChapter}:${inputVerse}`;
                        } else {
                            this.highlightedVerses = [];
                            this.currentReference = `${inputBook} ${inputChapter}`;
                        }
                        this.parseCurrentReference();
                        this.rebuildVerseColorMap();
                        this.crossRefs = [];
                        this.speakerVerses = [];
                        this.updateURL(true);
                        this.observeVerses();
                        this.loading = false;

                        // Scroll to highlighted verse (same behavior as network path)
                        if (this.highlightedVerses.length > 0) {
                            this.$nextTick(() => {
                                const firstHighlighted = document.getElementById(`verse-${this.highlightedVerses[0]}`);
                                if (firstHighlighted) {
                                    firstHighlighted.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                }
                            });
                        }

                        // Load cached commentary/interlinear/cross-refs
                        await this.loadCommentary();
                        await this.loadInterlinearData();
                        try {
                            const cachedRefs = await window.offlineStorage.getChapterCrossRefs(inputBook, inputChapter);
                            if (gen === this._loadGeneration && cachedRefs?.length > 0) this.crossRefs = cachedRefs;
                        } catch (e) { /* silent */ }

                        // Background refresh from API (fire-and-forget)
                        this._backgroundRefresh(inputBook, inputChapter, gen);
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
                if (gen !== this._loadGeneration) return;  // superseded by newer navigation (B4)
                this.currentReference = data.reference;
                // Precompute rendered html once per assignment (P5) instead of per render
                this.verses = (data.verses || []).map(v => ({ ...v, html: this.formatVerseText(v.text) }));
                this.crossRefs = data.cross_references || [];
                this.highlightedVerses = data.highlighted_verses || [];
                this.speakerVerses = data.speaker_verses || [];

                // Parse reference for navigation
                this.parseCurrentReference();
                this.rebuildVerseColorMap();

                // Track in reading history
                this.addToHistory(this.currentReference, this.translation);

                // Update URL with clean path format (new chapter = new history entry)
                this.updateURL(true);

                // Load commentary
                await this.loadCommentary();

                // Load interlinear data if available. Lazy by default (P3): the
                // payload is ~50KB/chapter and the feature is off by default.
                // Eager only when the toggle is already on, or when auto-cache
                // needs the data for offline storage.
                if ((this.showInterlinear || this.autoCacheEnabled)
                        && (OT_BOOKS.includes(this.currentBook) || NT_BOOKS.includes(this.currentBook))) {
                    await this.loadInterlinearData();
                } else {
                    this.interlinearData = {};
                    this._interlinearRef = null;
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
                // Network failed — try IndexedDB fallback (skip if superseded, B4)
                if (gen === this._loadGeneration) {
                    await this._loadFromCache(inputBook, inputChapter, err.message);
                }
            } finally {
                // A newer navigation owns the spinner if gen moved on (B4)
                if (gen === this._loadGeneration) this.loading = false;
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
                    this.verses = cached.map(v => ({ verse: v.verse, text: v.text, html: this.formatVerseText(v.text) }));
                    this.currentReference = `${book} ${chapter}`;
                    this.parseCurrentReference();
                    this.rebuildVerseColorMap();
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

                    // Load cached commentary and interlinear (interlinear lazy
                    // unless shown or auto-cache wants it — P3)
                    await this.loadCommentary();
                    if (this.showInterlinear || this.autoCacheEnabled) {
                        await this.loadInterlinearData();
                    } else {
                        this.interlinearData = {};
                        this._interlinearRef = null;
                    }

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
        async _backgroundRefresh(book, chapter, gen) {
            try {
                const ref = `${book} ${chapter}`;
                const response = await fetch(
                    `/api/passage/${encodeURIComponent(ref)}?translation=${this.translation}`
                );
                if (!response.ok) return;
                const data = await response.json();

                // Stale response after fast navigation — do not clobber state (B4)
                if (gen !== undefined && gen !== this._loadGeneration) return;

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
            this.showChapterJump = false;
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

        // Shared fetch-with-offline-fallback. Pattern: forcedOffline check ->
        // fetch -> on network failure (or forced offline) fall back to IndexedDB
        // via cacheGetter. A non-OK HTTP response does NOT hit the cache (matches
        // the original loaders). Never throws.
        // Returns { ok, data, fromCache, error }:
        //   fromCache=true -> data is the cached array
        //   ok=true        -> data is the parsed API response
        //   ok=false       -> non-OK response, or fetch + cache both came up empty
        async _fetchOrCache(url, cacheGetter, { forcedOfflineCheck = true } = {}) {
            try {
                if (forcedOfflineCheck && this.forcedOffline) {
                    throw new Error('offline');
                }
                const response = await fetch(url);
                if (!response.ok) {
                    return { ok: false, data: null, fromCache: false, error: null };
                }
                return { ok: true, data: await response.json(), fromCache: false, error: null };
            } catch (err) {
                if (window.offlineStorage) {
                    try {
                        const cached = await cacheGetter();
                        if (cached && cached.length > 0) {
                            return { ok: true, data: cached, fromCache: true, error: null };
                        }
                    } catch (cacheErr) {
                        console.debug('Cache fallback failed:', cacheErr);
                    }
                }
                return { ok: false, data: null, fromCache: false, error: err };
            }
        },

        // Load commentary for current chapter (always full chapter for browsing)
        async loadCommentary() {
            if (!this.currentBook || !this.currentChapter) {
                this.commentary = [];
                return;
            }

            const gen = this._loadGeneration;
            this.loadingCommentary = true;
            const chapterRef = `${this.currentBook} ${this.currentChapter}`;
            const result = await this._fetchOrCache(
                `/api/passage/${encodeURIComponent(chapterRef)}/commentary`,
                () => window.offlineStorage.getChapterCommentary(this.currentBook, this.currentChapter)
            );
            if (gen !== this._loadGeneration) {
                // Stale response after navigation — leave state alone (B4)
                this.loadingCommentary = false;
                return;
            }
            if (result.fromCache) {
                this.commentary = result.data;
            } else if (result.ok) {
                this.commentary = result.data.entries || [];
            } else {
                this.commentary = [];
            }
            this.loadingCommentary = false;
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
            // Convert -SubTopic headings to styled lines
            let html = text.replace(/^-/gm, '<br>&#x2022; ')
                          .replace(/\n/g, '<br>')
                          .replace(/\s{5,}/g, '<br>&nbsp;&nbsp;&nbsp;');
            // Make verse references clickable using data-ref (same pattern as commentary)
            html = html.replace(
                /([A-Z1-3][A-Z]{1,4})\s+(\d+):(\d+)/g,
                (match, abbr, ch, vs) => {
                    const book = normalizeBookName(abbr);
                    if (!BIBLE_BOOKS.includes(book)) return match;
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
            const currentVerse = this.getNoteStartVerse();
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
            this.loadCrossRefs(null, verseNum);

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

        // Handle click on verse box - select verse unless clicking a word
        async handleVerseBoxClick(event, verseNum, verseIdx) {
            // Skip if long-press just fired (prevents double-action)
            if (this._longPressTriggered) {
                this._longPressTriggered = false;
                return;
            }

            // In note edit mode, handle verse selection for multi-verse notes
            if (this.noteEditMode) {
                // Combined plan mode: notes anchor to one chapter — ignore
                // clicks on verses outside the selection's chapter
                if (this.combinedPlanReading && verseIdx !== undefined
                    && !this.verseInSelectionScope(this.verses[verseIdx])) return;
                this.handleVerseSelection(verseNum, event);
                return;
            }

            // On touch: if this verse is already selected, check for word tap
            if (this.isTouchDevice) {
                if (this.highlightedVerses.length === 1 && this.highlightedVerses[0] === verseNum) {
                    const wordEl = event.target.closest('.word');
                    if (wordEl) {
                        // ponytail: two-level tap — verse selected, now word tapped
                        await this.handleWordClick(event);
                        return;
                    }
                }
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

        getCommentarySourceTabs() {
            const sources = this.getCommentarySources();
            return sources.length > 1 ? ['All', ...sources] : sources;
        },

        // Commentary grouped by source for the active verse/study panel.
        getStudyCommentaryGroups() {
            const activeVerse = this.getActiveVerse();
            const bySource = {};
            for (const entry of this.commentary) {
                const start = entry.reference_start || 1;
                const end = entry.reference_end || start;
                if (activeVerse && !(activeVerse >= start && activeVerse <= end)) {
                    continue;
                }
                const source = entry.source || 'Unknown';
                if (!bySource[source]) bySource[source] = [];
                bySource[source].push(entry);
            }

            // If a verse has no exact match, fall back to the first entries from each source
            // so the Study tab still exposes available commentators for the chapter.
            if (Object.keys(bySource).length === 0) {
                for (const source of this.getCommentarySources()) {
                    bySource[source] = this.commentary
                        .filter(entry => (entry.source || 'Unknown') === source)
                        .slice(0, 2);
                }
            }
            return this.getCommentarySources()
                .filter(source => bySource[source]?.length > 0)
                .map(source => ({ source, entries: bySource[source] }));
        },

        getStudyReferenceLabel() {
            const activeVerse = this.getActiveVerse();
            if (!this.currentBook || !this.currentChapter) return 'Study';
            return activeVerse
                ? `${this.currentBook} ${this.currentChapter}:${activeVerse}`
                : `${this.currentBook} ${this.currentChapter}`;
        },

        getStudyCrossRefs(limit = 6) {
            return this.getFilteredCrossRefs().slice(0, limit);
        },

        openStudySection(tab) {
            this.activeTab = tab;
            if (tab === 'topics') this.initTopicSections();
        },

        // Get the currently active commentary source (defaults to first)
        getActiveCommentarySource() {
            const sources = this.getCommentarySources();
            if (sources.length === 0) return null;
            if (this.activeCommentarySource === 'All' && sources.length > 1) {
                return 'All';
            }
            if (this.activeCommentarySource && sources.includes(this.activeCommentarySource)) {
                return this.activeCommentarySource;
            }
            return sources.length > 1 ? 'All' : sources[0];
        },

        // Get commentary entries for the active source tab
        getActiveSourceEntries() {
            const activeSource = this.getActiveCommentarySource();
            if (!activeSource) return [];
            if (activeSource === 'All') return this.commentary;
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
            this.selectionContext = null;
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
        openStudyForSelected() {
            this.activeTab = 'study';
            this.resourcesPanelExpanded = true;
            this.sheetExpand();
            if (this.sidebarCollapsed) this.toggleSidebar();
            const v = this.highlightedVerses[0];
            if (v) this.$nextTick(() => this.scrollCommentaryToVerse(v));
        },

        memorizeSelected() {
            let added = 0;
            this.highlightedVerses.forEach(v => {
                if (!this.isInMemory(v) && this.addToMemory(v, true)) added++;
            });
            if (added > 0) {
                this.showToast(added === 1
                    ? 'Added to memory verses'
                    : `Added ${added} verses to memory`, 'success');
            }
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
            // Combined plan mode: selection is scoped to one chapter. Clicking a
            // verse in a different chapter starts a fresh selection there instead
            // of toggling the same verse number across every chapter.
            const verseObj = (this.combinedPlanReading && verseIdx !== undefined)
                ? this.verses[verseIdx] : null;
            const sameScope = !verseObj || !this.selectionContext
                || (verseObj._book === this.selectionContext.book
                    && verseObj._chapter === this.selectionContext.chapter);
            if (this.combinedPlanReading && !sameScope) {
                this.highlightedVerses = [];
            }

            // If this verse is already the only highlighted verse, deselect it
            if (sameScope && this.highlightedVerses.length === 1 && this.highlightedVerses[0] === verseNum) {
                this.clearVerseSelection();
                return;
            }

            // Multi-select: if already have selection, add/remove this verse
            if (sameScope && this.highlightedVerses.length > 0 && this.highlightedVerses.includes(verseNum)) {
                // Remove from selection
                this.highlightedVerses = this.highlightedVerses.filter(v => v !== verseNum);
                return;
            }

            if (sameScope && this.highlightedVerses.length > 0) {
                // Add to selection
                this.highlightedVerses = [...this.highlightedVerses, verseNum];
                return;
            }

            // New single selection
            this.highlightedVerses = [verseNum];
            this.selectionContext = verseObj
                ? { book: verseObj._book, chapter: verseObj._chapter } : null;
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
                    // (independent requests — run concurrently)
                    await Promise.all([
                        this.loadCrossRefs(),
                        this.loadCommentary(),
                        this.loadTopicsForVerse(verseNum)
                    ]);
                    this.$nextTick(() => this.scrollCommentaryToVerse(verseNum));
                }
                return;
            }

            // Update reference display
            this.currentReference = `${this.currentBook} ${this.currentChapter}:${verseNum}`;
            this.referenceInput = this.currentReference;

            // Update URL
            this.updateURL();

            // Reload cross-references and topics for the selected verse, concurrently.
            // Commentary is chapter-scoped and already loaded by loadPassage — no refetch (P2).
            await Promise.all([
                this.loadCrossRefs(),
                this.loadTopicsForVerse(verseNum)
            ]);
            this.$nextTick(() => this.scrollCommentaryToVerse(verseNum));
        },

        // Load cross-references. No args: current reference (chapter-scoped cache
        // fallback, clears crossRefs on failure). With verseNum: that verse of the
        // current chapter (verse-scoped cache fallback, keeps existing crossRefs on
        // failure). refOverride wins for the fetch URL if provided.
        async loadCrossRefs(refOverride = null, verseNum = null) {
            const gen = this._loadGeneration;
            const ref = refOverride
                || (verseNum != null
                    ? `${this.currentBook} ${this.currentChapter}:${verseNum}`
                    : this.currentReference);
            const result = await this._fetchOrCache(
                `/api/passage/${encodeURIComponent(ref)}/crossrefs`,
                () => verseNum != null
                    ? window.offlineStorage.getChapterCrossRefs(this.currentBook, this.currentChapter, verseNum, verseNum)
                    : window.offlineStorage.getChapterCrossRefs(this.currentBook, this.currentChapter)
            );
            if (gen !== this._loadGeneration) return;  // stale after navigation (B4)
            if (result.fromCache) {
                this.crossRefs = result.data;
                return;
            }
            if (result.ok) {
                this.crossRefs = result.data.cross_references || [];
                return;
            }
            if (result.error) console.error('Failed to load cross-refs:', result.error);
            if (verseNum == null) this.crossRefs = [];
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

            // Invalidate older in-flight previews — last hover wins (B7)
            const token = ++this._previewToken;

            // Delay slightly to avoid flickering
            this.previewTimeout = setTimeout(async () => {
                try {
                    const response = await fetch(
                        `/api/verse/${encodeURIComponent(ref)}?translation=${this.translation}`
                    );
                    // Superseded by a newer hover or hidePreview — drop it (B7)
                    if (token !== this._previewToken) return;

                    if (response.ok) {
                        const data = await response.json();
                        if (token !== this._previewToken) return;
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
            // Invalidate any in-flight preview fetch so it can't pop the
            // tooltip back open after hide (B7)
            this._previewToken++;
            this.versePreview.show = false;
        },

        // Lazy interlinear (P3): called when the toggle turns on. No-op if the
        // current chapter's data is already loaded, a load is in flight, or
        // we're in combined plan reading (which loads interlinear eagerly).
        async ensureInterlinearLoaded() {
            if (this.combinedPlanReading || this.interlinearLoading) return;
            if (!this.currentBook || !this.currentChapter) return;
            if (this._interlinearRef === `${this.currentBook} ${this.currentChapter}`) return;
            if (!(OT_BOOKS.includes(this.currentBook) || NT_BOOKS.includes(this.currentBook))) return;
            await this.loadInterlinearData();
        },

        // Load interlinear data for the entire chapter
        async loadInterlinearData() {
            const gen = this._loadGeneration;
            this.interlinearLoading = true;
            this.interlinearData = {};
            this._interlinearRef = null;

            const ref = `${this.currentBook} ${this.currentChapter}`;
            const result = await this._fetchOrCache(
                `/api/passage/${encodeURIComponent(ref)}/interlinear?translation=${this.translation}`,
                () => window.offlineStorage.getChapterInterlinear(this.currentBook, this.currentChapter)
            );

            if (gen !== this._loadGeneration) {
                // Stale response after navigation — leave state alone (B4)
                this.interlinearLoading = false;
                return;
            }

            if (result.fromCache) {
                const lang = OT_BOOKS.includes(this.currentBook) ? 'hebrew' : 'greek';
                this.interlinearLanguage = lang;
                const byVerse = {};
                for (const word of result.data) {
                    if (!byVerse[word.verse]) byVerse[word.verse] = [];
                    byVerse[word.verse].push(word);
                }
                for (const [verseNum, words] of Object.entries(byVerse)) {
                    this.interlinearData[parseInt(verseNum)] = {
                        language: lang,
                        words: words
                    };
                }
            } else if (result.ok) {
                const data = result.data;
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
            // Mark loaded only on success so a failed fetch retries on next toggle
            if (result.ok) this._interlinearRef = ref;
            this.interlinearLoading = false;
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
        // Highlight the interlinear word matching an original-language position
        _highlightInterlinearWord(verseBox, origPos) {
            if (!this.showInterlinear || !origPos) return;
            verseBox?.querySelectorAll('.interlinear-word').forEach((el, idx) => {
                if (idx + 1 === origPos) el.classList.add('selected');
            });
        },

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

                        this._highlightInterlinearWord(verseBox, align.original_word_position);
                        return;
                    }
                } catch (err) {
                    console.error('Word alignment lookup failed:', err);
                }
            }

            // Offline fallback: cached alignments + lexicon (saved with offline books)
            if (window.offlineStorage && this.currentBook && this.currentChapter && verseNum && wordPosition) {
                try {
                    const align = await window.offlineStorage.getWordAlignment(
                        this.translation, this.currentBook, this.currentChapter, verseNum, wordPosition);
                    if (align) {
                        // Cached alignments carry no transliteration/extended definition; lexicon does
                        const lex = align.strong_number
                            ? await window.offlineStorage.getLexiconEntry(align.strong_number).catch(() => null)
                            : null;
                        this.selectedWord = {
                            text: word,
                            original: align.original_text || lex?.original,
                            transliteration: lex?.transliteration,
                            strong_number: align.strong_number,
                            parsing: null,
                            definition: align.definition || lex?.definition,
                            extended_definition: lex?.extended_definition,
                            language: align.language || lex?.language,
                            occurrences: [],
                            count: 0
                        };
                        this._highlightInterlinearWord(verseBox, align.original_word_position);
                        return;
                    }
                } catch (err) {
                    console.error('Offline word lookup failed:', err);
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
                        // API caps occurrences at 500; total is the real count
                        count: data.total ?? data.count,
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
                if (this.combinedPlanReading) {
                    if (diff > 0) this.immersivePlanPrev();
                    else this.immersivePlanNext();
                } else {
                    if (diff > 0) this.previousChapter();
                    else this.nextChapter();
                }
            }
        },

        immersivePlanPrev() {
            if (this.planDay > 1) {
                this.planDay--;
                this.startPlanReading();
            }
        },

        immersivePlanNext() {
            if (this.planDay < (this.currentPlan?.duration_days || 365)) {
                this.markPlanDayAndContinue();
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

    };
    // Feature modules (modules/*.js) load first and register on
    // window.BibleModules; script order in index.html sets merge order.
    return Object.assign(core, ...Object.values(window.BibleModules || {}));
}
