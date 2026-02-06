// Cross-Reference Map — Data Constants & Utilities
// Extracted from map.html for modularity

// ========== Book abbreviation map ==========
const BOOK_ABBREVS = {
    "Genesis": "Gen", "Exodus": "Ex", "Leviticus": "Lev", "Numbers": "Num",
    "Deuteronomy": "Deut", "Joshua": "Josh", "Judges": "Judg", "Ruth": "Ruth",
    "1 Samuel": "1Sa", "2 Samuel": "2Sa", "1 Kings": "1Ki", "2 Kings": "2Ki",
    "1 Chronicles": "1Ch", "2 Chronicles": "2Ch", "Ezra": "Ezr", "Nehemiah": "Neh",
    "Esther": "Est", "Job": "Job", "Psalms": "Ps", "Proverbs": "Prov",
    "Ecclesiastes": "Ecc", "Song of Solomon": "Song", "Isaiah": "Isa",
    "Jeremiah": "Jer", "Lamentations": "Lam", "Ezekiel": "Ezek", "Daniel": "Dan",
    "Hosea": "Hos", "Joel": "Joel", "Amos": "Amos", "Obadiah": "Obad",
    "Jonah": "Jon", "Micah": "Mic", "Nahum": "Nah", "Habakkuk": "Hab",
    "Zephaniah": "Zeph", "Haggai": "Hag", "Zechariah": "Zech", "Malachi": "Mal",
    "Matthew": "Mt", "Mark": "Mk", "Luke": "Lk", "John": "Jn", "Acts": "Acts",
    "Romans": "Rom", "1 Corinthians": "1Co", "2 Corinthians": "2Co",
    "Galatians": "Gal", "Ephesians": "Eph", "Philippians": "Phil",
    "Colossians": "Col", "1 Thessalonians": "1Th", "2 Thessalonians": "2Th",
    "1 Timothy": "1Ti", "2 Timothy": "2Ti", "Titus": "Tit", "Philemon": "Phm",
    "Hebrews": "Heb", "James": "Jas", "1 Peter": "1Pe", "2 Peter": "2Pe",
    "1 John": "1Jn", "2 John": "2Jn", "3 John": "3Jn", "Jude": "Jude",
    "Revelation": "Rev"
};

function abbrev(book) { return BOOK_ABBREVS[book] || book; }

// Genre mapping for color coding
const BOOK_GENRES = {
    "Genesis": "law", "Exodus": "law", "Leviticus": "law", "Numbers": "law", "Deuteronomy": "law",
    "Joshua": "history", "Judges": "history", "Ruth": "history", "1 Samuel": "history", "2 Samuel": "history",
    "1 Kings": "history", "2 Kings": "history", "1 Chronicles": "history", "2 Chronicles": "history",
    "Ezra": "history", "Nehemiah": "history", "Esther": "history",
    "Job": "wisdom", "Psalms": "wisdom", "Proverbs": "wisdom", "Ecclesiastes": "wisdom", "Song of Solomon": "wisdom",
    "Isaiah": "major_prophet", "Jeremiah": "major_prophet", "Lamentations": "major_prophet", "Ezekiel": "major_prophet", "Daniel": "major_prophet",
    "Hosea": "minor_prophet", "Joel": "minor_prophet", "Amos": "minor_prophet", "Obadiah": "minor_prophet",
    "Jonah": "minor_prophet", "Micah": "minor_prophet", "Nahum": "minor_prophet", "Habakkuk": "minor_prophet",
    "Zephaniah": "minor_prophet", "Haggai": "minor_prophet", "Zechariah": "minor_prophet", "Malachi": "minor_prophet",
    "Matthew": "gospel", "Mark": "gospel", "Luke": "gospel", "John": "gospel",
    "Acts": "history_nt",
    "Romans": "epistle", "1 Corinthians": "epistle", "2 Corinthians": "epistle", "Galatians": "epistle",
    "Ephesians": "epistle", "Philippians": "epistle", "Colossians": "epistle",
    "1 Thessalonians": "epistle", "2 Thessalonians": "epistle", "1 Timothy": "epistle", "2 Timothy": "epistle",
    "Titus": "epistle", "Philemon": "epistle", "Hebrews": "epistle", "James": "epistle",
    "1 Peter": "epistle", "2 Peter": "epistle", "1 John": "epistle", "2 John": "epistle", "3 John": "epistle", "Jude": "epistle",
    "Revelation": "apocalyptic"
};

const GENRE_LABELS = {
    law: 'Law', history: 'History', wisdom: 'Wisdom',
    major_prophet: 'Major Prophets', minor_prophet: 'Minor Prophets',
    gospel: 'Gospels', history_nt: 'Acts', epistle: 'Epistles', apocalyptic: 'Apocalyptic',
};

const GENRE_COLORS = {
    law:            { fill: '#22c55e', glow: 'rgba(34,197,94,0.35)',  rgb: '34,197,94' },
    history:        { fill: '#3b82f6', glow: 'rgba(59,130,246,0.35)', rgb: '59,130,246' },
    wisdom:         { fill: '#eab308', glow: 'rgba(234,179,8,0.35)',  rgb: '234,179,8' },
    major_prophet:  { fill: '#ef4444', glow: 'rgba(239,68,68,0.35)',  rgb: '239,68,68' },
    minor_prophet:  { fill: '#f97316', glow: 'rgba(249,115,22,0.35)', rgb: '249,115,22' },
    gospel:         { fill: '#a855f7', glow: 'rgba(168,85,247,0.35)', rgb: '168,85,247' },
    history_nt:     { fill: '#06b6d4', glow: 'rgba(6,182,212,0.35)',  rgb: '6,182,212' },
    epistle:        { fill: '#ec4899', glow: 'rgba(236,72,153,0.35)', rgb: '236,72,153' },
    apocalyptic:    { fill: '#8b5cf6', glow: 'rgba(139,92,246,0.35)', rgb: '139,92,246' },
};

// ========== Author data ==========
const BOOK_AUTHORS = {
    "Genesis": "Moses", "Exodus": "Moses", "Leviticus": "Moses", "Numbers": "Moses", "Deuteronomy": "Moses", "Job": "Moses",
    "Joshua": "Joshua", "Judges": "Samuel", "Ruth": "Samuel", "1 Samuel": "Samuel", "2 Samuel": "Samuel",
    "1 Kings": "Jeremiah", "2 Kings": "Jeremiah",
    "1 Chronicles": "Ezra", "2 Chronicles": "Ezra", "Ezra": "Ezra", "Nehemiah": "Nehemiah", "Esther": "Esther",
    "Psalms": "David", "Proverbs": "Solomon", "Ecclesiastes": "Solomon", "Song of Solomon": "Solomon",
    "Isaiah": "Isaiah", "Jeremiah": "Jeremiah", "Lamentations": "Jeremiah",
    "Ezekiel": "Ezekiel", "Daniel": "Daniel",
    "Hosea": "Minor Prophets", "Joel": "Minor Prophets", "Amos": "Minor Prophets", "Obadiah": "Minor Prophets",
    "Jonah": "Minor Prophets", "Micah": "Minor Prophets", "Nahum": "Minor Prophets", "Habakkuk": "Minor Prophets",
    "Zephaniah": "Minor Prophets", "Haggai": "Minor Prophets", "Zechariah": "Minor Prophets", "Malachi": "Minor Prophets",
    "Matthew": "Matthew", "Mark": "Mark", "Luke": "Luke", "Acts": "Luke",
    "John": "John", "1 John": "John", "2 John": "John", "3 John": "John", "Revelation": "John",
    "Romans": "Paul", "1 Corinthians": "Paul", "2 Corinthians": "Paul", "Galatians": "Paul",
    "Ephesians": "Paul", "Philippians": "Paul", "Colossians": "Paul",
    "1 Thessalonians": "Paul", "2 Thessalonians": "Paul", "1 Timothy": "Paul", "2 Timothy": "Paul",
    "Titus": "Paul", "Philemon": "Paul", "Hebrews": "Paul",
    "James": "James", "1 Peter": "Peter", "2 Peter": "Peter", "Jude": "Jude",
};

const AUTHOR_COLORS = {
    "Moses":          { fill: '#22c55e', glow: 'rgba(34,197,94,0.35)',   rgb: '34,197,94' },
    "Joshua":         { fill: '#16a34a', glow: 'rgba(22,163,74,0.35)',   rgb: '22,163,74' },
    "Samuel":         { fill: '#3b82f6', glow: 'rgba(59,130,246,0.35)',  rgb: '59,130,246' },
    "David":          { fill: '#eab308', glow: 'rgba(234,179,8,0.35)',   rgb: '234,179,8' },
    "Solomon":        { fill: '#f59e0b', glow: 'rgba(245,158,11,0.35)', rgb: '245,158,11' },
    "Isaiah":         { fill: '#ef4444', glow: 'rgba(239,68,68,0.35)',   rgb: '239,68,68' },
    "Jeremiah":       { fill: '#dc2626', glow: 'rgba(220,38,38,0.35)',   rgb: '220,38,38' },
    "Ezekiel":        { fill: '#f97316', glow: 'rgba(249,115,22,0.35)', rgb: '249,115,22' },
    "Daniel":         { fill: '#fb923c', glow: 'rgba(251,146,60,0.35)', rgb: '251,146,60' },
    "Ezra":           { fill: '#0ea5e9', glow: 'rgba(14,165,233,0.35)', rgb: '14,165,233' },
    "Nehemiah":       { fill: '#0284c7', glow: 'rgba(2,132,199,0.35)',   rgb: '2,132,199' },
    "Esther":         { fill: '#06b6d4', glow: 'rgba(6,182,212,0.35)',   rgb: '6,182,212' },
    "Minor Prophets": { fill: '#e11d48', glow: 'rgba(225,29,72,0.35)',   rgb: '225,29,72' },
    "Matthew":        { fill: '#a855f7', glow: 'rgba(168,85,247,0.35)', rgb: '168,85,247' },
    "Mark":           { fill: '#9333ea', glow: 'rgba(147,51,234,0.35)', rgb: '147,51,234' },
    "Luke":           { fill: '#c084fc', glow: 'rgba(192,132,252,0.35)', rgb: '192,132,252' },
    "John":           { fill: '#8b5cf6', glow: 'rgba(139,92,246,0.35)', rgb: '139,92,246' },
    "Paul":           { fill: '#ec4899', glow: 'rgba(236,72,153,0.35)', rgb: '236,72,153' },
    "James":          { fill: '#14b8a6', glow: 'rgba(20,184,166,0.35)', rgb: '20,184,166' },
    "Peter":          { fill: '#2dd4bf', glow: 'rgba(45,212,191,0.35)', rgb: '45,212,191' },
    "Jude":           { fill: '#5eead4', glow: 'rgba(94,234,212,0.35)', rgb: '94,234,212' },
};

// ========== Era data ==========
const BOOK_ERAS = {
    "Genesis": "Patriarchs", "Exodus": "Exodus & Law", "Leviticus": "Exodus & Law", "Numbers": "Exodus & Law", "Deuteronomy": "Exodus & Law",
    "Joshua": "Conquest", "Judges": "Conquest", "Ruth": "Conquest",
    "1 Samuel": "Kingdom", "2 Samuel": "Kingdom", "1 Kings": "Kingdom", "2 Kings": "Kingdom",
    "1 Chronicles": "Kingdom", "2 Chronicles": "Kingdom",
    "Job": "Patriarchs", "Psalms": "Kingdom", "Proverbs": "Kingdom", "Ecclesiastes": "Kingdom", "Song of Solomon": "Kingdom",
    "Isaiah": "Prophets", "Jeremiah": "Prophets", "Lamentations": "Prophets", "Ezekiel": "Prophets", "Daniel": "Prophets",
    "Hosea": "Prophets", "Joel": "Prophets", "Amos": "Prophets", "Obadiah": "Prophets",
    "Jonah": "Prophets", "Micah": "Prophets", "Nahum": "Prophets", "Habakkuk": "Prophets",
    "Zephaniah": "Prophets", "Haggai": "Prophets", "Zechariah": "Prophets", "Malachi": "Prophets",
    "Ezra": "Return", "Nehemiah": "Return", "Esther": "Return",
    "Matthew": "Gospels", "Mark": "Gospels", "Luke": "Gospels", "John": "Gospels",
    "Acts": "Early Church", "Romans": "Early Church", "1 Corinthians": "Early Church", "2 Corinthians": "Early Church",
    "Galatians": "Early Church", "Ephesians": "Early Church", "Philippians": "Early Church", "Colossians": "Early Church",
    "1 Thessalonians": "Early Church", "2 Thessalonians": "Early Church", "1 Timothy": "Early Church", "2 Timothy": "Early Church",
    "Titus": "Early Church", "Philemon": "Early Church", "Hebrews": "Early Church", "James": "Early Church",
    "1 Peter": "Early Church", "2 Peter": "Early Church", "1 John": "Early Church", "2 John": "Early Church",
    "3 John": "Early Church", "Jude": "Early Church", "Revelation": "Early Church",
};

const ERA_LIST = ['Patriarchs', 'Exodus & Law', 'Conquest', 'Kingdom', 'Prophets', 'Return', 'Gospels', 'Early Church'];

const ERA_COLORS = {
    "Patriarchs":    { fill: '#22c55e', glow: 'rgba(34,197,94,0.35)',   rgb: '34,197,94' },
    "Exodus & Law":  { fill: '#16a34a', glow: 'rgba(22,163,74,0.35)',   rgb: '22,163,74' },
    "Conquest":      { fill: '#3b82f6', glow: 'rgba(59,130,246,0.35)',  rgb: '59,130,246' },
    "Kingdom":       { fill: '#eab308', glow: 'rgba(234,179,8,0.35)',   rgb: '234,179,8' },
    "Prophets":      { fill: '#ef4444', glow: 'rgba(239,68,68,0.35)',   rgb: '239,68,68' },
    "Return":        { fill: '#06b6d4', glow: 'rgba(6,182,212,0.35)',   rgb: '6,182,212' },
    "Gospels":       { fill: '#a855f7', glow: 'rgba(168,85,247,0.35)', rgb: '168,85,247' },
    "Early Church":  { fill: '#ec4899', glow: 'rgba(236,72,153,0.35)', rgb: '236,72,153' },
};

// Generate a unique hue per book_order (1-66)
function bookColor(bookOrder) {
    const hue = ((bookOrder - 1) / 66) * 360;
    // Convert HSL to RGB for gradient use
    const h = hue / 360, s = 0.7, l = 0.55;
    const hue2rgb = (p, q, t) => { if (t < 0) t += 1; if (t > 1) t -= 1; if (t < 1/6) return p + (q - p) * 6 * t; if (t < 1/2) return q; if (t < 2/3) return p + (q - p) * (2/3 - t) * 6; return p; };
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    const r = Math.round(hue2rgb(p, q, h + 1/3) * 255);
    const g = Math.round(hue2rgb(p, q, h) * 255);
    const b = Math.round(hue2rgb(p, q, h - 1/3) * 255);
    return {
        fill: `hsl(${hue}, 70%, 55%)`,
        glow: `hsla(${hue}, 70%, 55%, 0.35)`,
        rgb: `${r},${g},${b}`,
        hue: hue,
    };
}

// Depth colors (cool to warm gradient)
const DEPTH_COLORS = [
    { fill: '#f43f5e', glow: 'rgba(244,63,94,0.4)',  rgb: '244,63,94' },   // 0 - center (red/pink)
    { fill: '#f97316', glow: 'rgba(249,115,22,0.35)', rgb: '249,115,22' },  // 1
    { fill: '#eab308', glow: 'rgba(234,179,8,0.35)',  rgb: '234,179,8' },   // 2
    { fill: '#22c55e', glow: 'rgba(34,197,94,0.35)',  rgb: '34,197,94' },   // 3
    { fill: '#3b82f6', glow: 'rgba(59,130,246,0.35)', rgb: '59,130,246' },  // 4
    { fill: '#8b5cf6', glow: 'rgba(139,92,246,0.35)', rgb: '139,92,246' },  // 5
    { fill: '#a855f7', glow: 'rgba(168,85,247,0.35)', rgb: '168,85,247' },  // 6
    { fill: '#6366f1', glow: 'rgba(99,102,241,0.35)', rgb: '99,102,241' },  // 7+
];

function getNodeColor(node, mode, graph) {
    if (mode === 'genre') {
        const genre = BOOK_GENRES[node.book] || 'epistle';
        return GENRE_COLORS[genre];
    }
    if (mode === 'book') {
        return bookColor(node.book_order || 1);
    }
    if (mode === 'depth') {
        const d = Math.min(node.depth || 0, DEPTH_COLORS.length - 1);
        return DEPTH_COLORS[d];
    }
    if (mode === 'author') {
        const author = BOOK_AUTHORS[node.book] || 'Paul';
        return AUTHOR_COLORS[author] || AUTHOR_COLORS['Paul'];
    }
    if (mode === 'era') {
        const era = BOOK_ERAS[node.book] || 'Early Church';
        return ERA_COLORS[era] || ERA_COLORS['Early Church'];
    }
    if (mode === 'christological') {
        if (node.isChrist) return { fill: '#fef3c7', glow: 'rgba(254,243,199,0.6)', rgb: '254,243,199' };
        if (node.isSeed) return { fill: '#fbbf24', glow: 'rgba(251,191,36,0.45)', rgb: '251,191,36' };
        // Gradient from gold (near) → teal → blue (far) based on depth
        const d = node.depth || 1;
        if (d <= 2) return { fill: '#f59e0b', glow: 'rgba(245,158,11,0.35)', rgb: '245,158,11' };
        if (d <= 3) return { fill: '#14b8a6', glow: 'rgba(20,184,166,0.35)', rgb: '20,184,166' };
        return { fill: '#3b82f6', glow: 'rgba(59,130,246,0.35)', rgb: '59,130,246' };
    }
    if (mode === 'connectivity') {
        // Heat based on edge count — computed from graph data
        const count = node._connCount || 0;
        const max = graph?._maxConnCount || 1;
        const t = Math.min(count / max, 1);
        // Cool (blue) → warm (yellow) → hot (red)
        const r = Math.round(t < 0.5 ? t * 2 * 255 : 255);
        const g = Math.round(t < 0.5 ? t * 2 * 200 : (1 - t) * 2 * 200);
        const b = Math.round(t < 0.5 ? (1 - t * 2) * 255 : 0);
        return {
            fill: `rgb(${r},${g},${b})`,
            glow: `rgba(${r},${g},${b},0.35)`,
            rgb: `${r},${g},${b}`,
        };
    }
    // Default: testament
    return node.testament === 'OT'
        ? { fill: '#f59e0b', glow: 'rgba(245,158,11,0.35)', rgb: '245,158,11' }
        : { fill: '#38bdf8', glow: 'rgba(56,189,248,0.35)', rgb: '56,189,248' };
}

function shortLabel(node) {
    if (node.isChrist) return 'CHRIST';
    return abbrev(node.book) + ' ' + node.chapter + ':' + node.verse;
}

function fullLabel(node) {
    if (node.isChrist) return 'Christ';
    return node.book + ' ' + node.chapter + ':' + node.verse;
}

// ========== Parse user reference query into API path ==========
function parseReference(q) {
    q = q.trim();
    // Backend expects standard format: "John 3:16", "Genesis 1", "Rom 8:28"
    // Convert dot notation back to standard if needed
    const dotMatch = q.match(/^(.+?)\.(\d+)\.(\d+)$/);
    if (dotMatch) {
        q = dotMatch[1] + ' ' + dotMatch[2] + ':' + dotMatch[3];
    }
    return encodeURIComponent(q);
}
