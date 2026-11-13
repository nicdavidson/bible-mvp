// How sure a tapped word's link to the Hebrew/Greek is (pure; window.BibleWordLink).
// Not a bibleApp module: app.js reads it when a word is tapped, online or offline.
//
// docs/ALIGNMENT_2026-11.md ("One threshold or two?"): confidence is calibrated
// (about the chance the link is right), and a shown link is right about nine times
// in ten at >= 0.5 for content words but needs >= 0.7 for function words.
// Human alignments (method 0, the BSB gold) always show.
//
// FUNCTION_WORDS is every word in the alignment table that the aligner's calibration
// treated as a function word: is_function(normalize(word)) in scripts/aligner
// (rerank.py, text.py). That is why archaic forms (hath, thee, wilt) and a few stems
// of the normalizer ("noted" -> "not", "withs" -> "with") are here.
// tests/test_word_confidence.py rebuilds the list from the aligner and the DB and
// fails if this one drifts. Lower case, curly apostrophe.
window.BibleWordLink = (() => {
    const FUNCTION_WORDS = new Set((
        "a all am an and are art as at be been being but butting by can canst did didst do does doing "
        + "done dost doth for from had hadst has hast hath have having he her hers herself him himself "
        + "his i if in into is it its itself it’s let lets letting let’s may mayest me might mightest "
        + "mine must my myself nay no not noted of on or our ours ourselves our’s shall shalt she should "
        + "shouldest so that that’s the thee their theirs them themselves then they thine this thou thy "
        + "thyself to unto upon us was wast we were wert we’re what when which who will willing wills "
        + "wilt with withs would wouldest ye you your yours yourself yourselves"
    ).split(' '));
    const CONTENT_MIN = 0.5;
    const FUNCTION_MIN = 0.7;

    const isFunctionWord = (word) => FUNCTION_WORDS.has(String(word || '').toLowerCase().replace(/'/g, '’'));

    // 'sure' | 'unsure'. A link saved offline by an older version carries no confidence:
    // those were BSB human links, so they count as sure.
    function strength(word, confidence, method) {
        if (method === 0 || confidence == null) return 'sure';
        return confidence >= (isFunctionWord(word) ? FUNCTION_MIN : CONTENT_MIN) ? 'sure' : 'unsure';
    }

    return { FUNCTION_WORDS, isFunctionWord, strength, CONTENT_MIN, FUNCTION_MIN };
})();
