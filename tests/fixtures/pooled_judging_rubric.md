# Pooled relevance judging: rubric (2026-11)

Used to extend `tests/fixtures/semantic_questions.json` with `pooled_refs`.

The pool for each question is the union of the top 10 verses from every method in the
evaluation:
- today's FTS and the OR keyword baseline
- vectors, hybrid, boost and auto for every model, including the fine-tuned ones and the
  qwen3 ceiling

The verses already listed for the question are removed. Candidates are shown in canonical
order with BSB text only, and never with the method that found them.

For each candidate, answer one question: **would a reader who typed this question be glad
to find this verse among the answers?**

Relevant (yes) when the verse itself speaks to what the question asks:
- it teaches, commands, promises or prays what the question is about, or
- it is a clear, well-known example of it (e.g. Jesus weeping for "comfort when
  grieving"), or
- for "what does the Bible say about X", it says something about X itself.

Not relevant (no) when it:
- only shares a word or a neighbouring theme ("the fear of the LORD" for anxiety; "I am
  poor and needy" for helping the poor);
- mentions the topic in passing inside narrative, genealogy, law details or prophecy
  against a nation, without bearing on the reader's question;
- asks the question instead of answering it ("Who then can be saved?").

Judge each verse alone, as written in the BSB, without the surrounding chapter. When
genuinely unsure, answer no. Fame is not a criterion: an obscure verse that answers the
question is relevant.
