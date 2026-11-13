"""Word alignment of English translations to the Hebrew/Greek source (STEPBible positions).

Modules:
    text     -- the UI's word tokenizer (positions contract) and English normalization
    sources  -- source-language tokens per verse, edition filtering, model features
    clear    -- Clear-Bible manual alignments (BSB, YLT) re-keyed to STEPBible positions
    kjv      -- eBible KJV (Strong's-tagged USFM) parsed and resolved to positions
    model    -- the statistical aligner (training, decoding, confidence)
    metrics  -- precision / recall / F1 / AER, calibration, error classes

See docs/ALIGNMENT_2026-11.md.
"""
