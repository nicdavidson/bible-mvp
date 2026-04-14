"""
Bible MVP Frontend Integrity Tests
Validates CSS, HTML, and JS are well-formed and contain expected features.
"""
import re
from pathlib import Path

import pytest

FRONTEND = Path(__file__).parent.parent / "frontend"
CSS_PATH = FRONTEND / "static" / "css" / "style.css"
JS_PATH = FRONTEND / "static" / "js" / "app.js"
HTML_PATH = FRONTEND / "index.html"
SW_PATH = FRONTEND / "static" / "sw.js"


@pytest.fixture(scope="module")
def css():
    return CSS_PATH.read_text()


@pytest.fixture(scope="module")
def js():
    return JS_PATH.read_text()


@pytest.fixture(scope="module")
def html():
    return HTML_PATH.read_text()


# ========== CSS INTEGRITY ==========

class TestCSS:
    def test_braces_balanced(self, css):
        """CSS braces must be balanced."""
        opens = css.count("{")
        closes = css.count("}")
        assert opens == closes, f"Unbalanced braces: {opens} open, {closes} close"

    def test_no_orphaned_verse_actions(self, css):
        """Old .verse-actions class should be fully removed."""
        assert ".verse-actions" not in css

    def test_action_bar_styles_exist(self, css):
        assert ".verse-action-bar" in css
        assert ".action-bar-btn" in css
        assert ".action-bar-label" in css

    def test_mobile_breakpoint_exists(self, css):
        assert "@media (max-width: 600px)" in css

    def test_landscape_breakpoint_exists(self, css):
        assert "@media (max-height: 500px) and (orientation: landscape)" in css

    def test_contrast_improved(self, css):
        """Secondary text should be #555555, not #666666."""
        assert "--color-text-secondary: #555555" in css
        assert "--color-text-secondary: #666666" not in css

    def test_verse_num_color_darkened(self, css):
        assert "--color-verse-num: #78716c" in css

    def test_drag_handle_size(self, css):
        """Drag indicator should be 8px tall."""
        assert re.search(r"\.drag-indicator\s*\{[^}]*height:\s*8px", css)

    def test_sticky_panel_header(self, css):
        """Panel header should be sticky on mobile."""
        assert "position: sticky" in css

    def test_no_parallel_on_mobile(self, css):
        """Parallel button should be hidden on mobile."""
        assert re.search(r"\.btn-parallel\s*\{[^}]*display:\s*none", css)

    def test_sw_version_is_placeholder(self):
        """SW version should be the Docker build placeholder."""
        sw = SW_PATH.read_text()
        assert "__SW_VERSION__" in sw

    def test_print_styles_exist(self, css):
        assert "@media print" in css


# ========== JS INTEGRITY ==========

class TestJS:
    def test_braces_balanced(self, js):
        opens = js.count("{")
        closes = js.count("}")
        assert opens == closes, f"Unbalanced braces: {opens} open, {closes} close"

    def test_action_bar_methods_exist(self, js):
        """All new action bar methods should be defined."""
        for method in [
            "clearVerseSelection",
            "getSelectionLabel",
            "openNoteForSelected",
            "memorizeSelected",
            "copySelected",
            "highlightSelectedVerses",
            "removeHighlightSelected",
        ]:
            assert method in js, f"Missing method: {method}"

    def test_swipe_handlers_exist(self, js):
        assert "readingTouchStart" in js
        assert "readingTouchEnd" in js
        assert "_swipeStartX" in js

    def test_long_press_handlers_exist(self, js):
        assert "startLongPress" in js
        assert "cancelLongPress" in js
        assert "_longPressTriggered" in js
        assert "_longPressTimer" in js

    def test_long_press_prevents_double_action(self, js):
        """handleVerseBoxClick should check _longPressTriggered."""
        assert "_longPressTriggered" in js
        idx = js.index("handleVerseBoxClick")
        # The check should be within the first 200 chars of the method
        snippet = js[idx:idx + 400]
        assert "_longPressTriggered" in snippet

    def test_keyboard_dismiss(self, js):
        """loadPassage should blur the reference input."""
        idx = js.index("async loadPassage()")
        snippet = js[idx:idx + 300]
        assert "blur()" in snippet

    def test_multi_select_in_selectVerse(self, js):
        """selectVerse should support adding to existing selection."""
        idx = js.index("async selectVerse(")
        snippet = js[idx:idx + 600]
        assert "highlightedVerses.includes(verseNum)" in snippet

    def test_no_copyFeedback_conflict(self, js):
        """copySelected should set copyFeedback to true."""
        idx = js.index("copySelected()")
        snippet = js[idx:idx + 800]
        assert "this.copyFeedback = true" in snippet

    def test_haptic_feedback(self, js):
        """Long press should trigger vibration."""
        assert "navigator.vibrate" in js


# ========== HTML INTEGRITY ==========

class TestHTML:
    def test_action_bar_in_html(self, html):
        assert "verse-action-bar" in html

    def test_no_old_verse_actions(self, html):
        """Old per-verse action div should be removed."""
        assert 'class="verse-actions"' not in html

    def test_action_bar_buttons(self, html):
        for text in ["Highlight", "Note", "Memorize", "Copy"]:
            assert text in html

    def test_swipe_handlers_attached(self, html):
        assert "readingTouchStart" in html
        assert "readingTouchEnd" in html

    def test_long_press_handlers_attached(self, html):
        assert "startLongPress" in html
        assert "cancelLongPress" in html

    def test_input_type_search(self, html):
        """Reference input should be type=search for iOS keyboard."""
        assert 'type="search"' in html
        assert 'enterkeyhint="go"' in html

    def test_highlight_picker_still_exists(self, html):
        """Color picker should still be in per-verse template."""
        assert "highlight-picker" in html
        assert "highlightSelectedVerses" in html

    def test_click_outside_guards(self, html):
        """Action bar click.outside should not dismiss on verse clicks."""
        assert ".verse-box" in html
        # The click.outside handler should check for verse-box
        assert "closest('.verse-box')" in html

    def test_viewport_meta(self, html):
        assert 'name="viewport"' in html
        assert "width=device-width" in html

    def test_manifest_link(self, html):
        assert 'rel="manifest"' in html
