-- Migration: 006_feedback_and_accounts
-- 1. Feedback without an account.  2. Users can delete their own account.

-- Signed-out feedback: no user id, no triage fields, no screenshot (uploads need an account).
-- The email is optional and unverified; treat it as "where to reply", nothing more.
-- ponytail: no rate limit; add one (edge function or captcha) if this gets spammed.
DROP POLICY IF EXISTS "Anyone can send feedback" ON bug_reports;
CREATE POLICY "Anyone can send feedback" ON bug_reports
    FOR INSERT TO anon WITH CHECK (
        user_id IS NULL
        AND coalesce(status, 'new') = 'new'
        AND admin_notes IS NULL
        AND screenshot_path IS NULL
    );

ALTER TABLE bug_reports DROP CONSTRAINT IF EXISTS bug_reports_email_len;
ALTER TABLE bug_reports ADD CONSTRAINT bug_reports_email_len
    CHECK (char_length(user_email) <= 254) NOT VALID;

-- Account deletion. Notes, tags and plan progress go by ON DELETE CASCADE; feedback
-- rows stay with user_id set to NULL (ON DELETE SET NULL).
CREATE OR REPLACE FUNCTION public.delete_own_account()
RETURNS void
LANGUAGE sql
SECURITY DEFINER
SET search_path = ''
AS $$
    DELETE FROM auth.users WHERE id = auth.uid();
$$;

REVOKE ALL ON FUNCTION public.delete_own_account() FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.delete_own_account() TO authenticated;
