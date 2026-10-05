-- Security hardening from docs/SECURITY_REVIEW_2026-10.md (Supabase/RLS findings).
-- Idempotent: safe to run on a project that already has 001-004 applied.
-- Apply to the DEV project first, then prod.

-- M4: screenshot uploads must go in the uploader's own folder; enforce size/type server-side.
UPDATE storage.buckets
SET public = false,
    file_size_limit = 5242880,  -- 5 MB, matches the client check
    allowed_mime_types = ARRAY['image/png', 'image/jpeg', 'image/webp', 'image/gif']
WHERE id = 'bug-screenshots';

DROP POLICY IF EXISTS "Users can upload screenshots" ON storage.objects;
CREATE POLICY "Users can upload screenshots" ON storage.objects
    FOR INSERT WITH CHECK (
        bucket_id = 'bug-screenshots'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

DROP POLICY IF EXISTS "Users can view own screenshots" ON storage.objects;
CREATE POLICY "Users can view own screenshots" ON storage.objects
    FOR SELECT USING (
        bucket_id = 'bug-screenshots'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

-- Bug reports: users can't set triage fields, spoof their email, or post megabytes.
DROP POLICY IF EXISTS "Users can insert own bug reports" ON bug_reports;
CREATE POLICY "Users can insert own bug reports" ON bug_reports
    FOR INSERT WITH CHECK (
        auth.uid() = user_id
        AND coalesce(status, 'new') = 'new'
        AND admin_notes IS NULL
        AND (user_email IS NULL OR user_email = auth.jwt() ->> 'email')
    );

ALTER TABLE bug_reports DROP CONSTRAINT IF EXISTS bug_reports_description_len;
ALTER TABLE bug_reports ADD CONSTRAINT bug_reports_description_len
    CHECK (char_length(description) <= 5000) NOT VALID;  -- NOT VALID: don't fail on existing rows

ALTER TABLE user_notes DROP CONSTRAINT IF EXISTS user_notes_content_len;
ALTER TABLE user_notes ADD CONSTRAINT user_notes_content_len
    CHECK (char_length(content) <= 50000) NOT VALID;

-- note_tags: the tag must belong to the user too, not just the note.
DROP POLICY IF EXISTS "Users can insert own note tags" ON note_tags;
CREATE POLICY "Users can insert own note tags" ON note_tags
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM user_notes
                WHERE user_notes.id = note_tags.note_id AND user_notes.user_id = auth.uid())
        AND EXISTS (SELECT 1 FROM user_tags
                    WHERE user_tags.id = note_tags.tag_id AND user_tags.user_id = auth.uid())
    );

-- reading_plan_progress: the client upserts, which needs an UPDATE policy under RLS.
DROP POLICY IF EXISTS "Users can update own progress" ON reading_plan_progress;
CREATE POLICY "Users can update own progress" ON reading_plan_progress
    FOR UPDATE USING (
        EXISTS (SELECT 1 FROM user_reading_plans
                WHERE user_reading_plans.id = reading_plan_progress.user_plan_id
                  AND user_reading_plans.user_id = auth.uid())
    );
