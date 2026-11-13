// Run the reader's real formatVerseText() (extracted from app.js) on the shared
// test vectors and check every verse yields the expected words and positions.
// Usage: node tests/js/tokenize_parity.mjs <app.js> <vectors.json>
import { readFileSync } from 'node:fs';

const [appPath, vectorsPath] = process.argv.slice(2);
const src = readFileSync(appPath, 'utf8');
const start = src.indexOf('formatVerseText(text) {');
if (start < 0) throw new Error('formatVerseText not found in ' + appPath);
let i = src.indexOf('{', start);
const bodyStart = i + 1;
let depth = 0;
for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}' && --depth === 0) break;
}
const formatVerseText = new Function('text', src.slice(bodyStart, i));

const vectors = JSON.parse(readFileSync(vectorsPath, 'utf8'));
let failures = 0;
for (const v of vectors) {
    const html = formatVerseText(v.text);
    const got = [];
    for (const m of html.matchAll(/data-word="([^"]*)" data-position="(\d+)"/g)) {
        if (Number(m[2]) !== got.length + 1) throw new Error(`non-sequential position in ${v.ref}`);
        got.push(m[1]);
    }
    if (JSON.stringify(got) !== JSON.stringify(v.words)) {
        failures++;
        if (failures <= 5) {
            console.log(`MISMATCH ${v.ref}\n  text: ${v.text}\n  js:   ${JSON.stringify(got)}\n  py:   ${JSON.stringify(v.words)}`);
        }
    }
}
console.log(`${vectors.length - failures}/${vectors.length} verses identical`);
process.exit(failures ? 1 : 0);
