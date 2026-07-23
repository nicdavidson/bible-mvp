// bibleApp feature module: tts — merged via Object.assign in app.js
window.BibleModules = window.BibleModules || {};
window.BibleModules.tts = {
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
};
