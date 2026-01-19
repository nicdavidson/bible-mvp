-- Migration: 004_bug_reports
-- Description: Create bug_reports table for user feedback submissions
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/_/sql

-- Create bug_reports table
CREATE TABLE bug_reports (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    user_email TEXT,  -- Store email in case user is deleted later

    -- Report category: 'bug', 'accuracy', 'feature'
    category TEXT NOT NULL CHECK (category IN ('bug', 'accuracy', 'feature')),

    -- Common fields
    description TEXT NOT NULL,

    -- Accuracy-specific fields (nullable for other categories)
    verse_reference TEXT,           -- e.g., "John 3:16"
    translation TEXT,               -- e.g., "BSB", "KJV", "WEB"
    accuracy_type TEXT,             -- 'text', 'original_lang', 'commentary', 'cross_ref', 'other'

    -- Screenshot (stored as Supabase Storage path)
    screenshot_path TEXT,

    -- Metadata
    current_url TEXT,               -- URL user was on when reporting
    user_agent TEXT,                -- Browser info for debugging
    status TEXT DEFAULT 'new' CHECK (status IN ('new', 'reviewed', 'resolved', 'wont_fix')),
    admin_notes TEXT,               -- For admin to add notes during review

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX idx_bug_reports_user_id ON bug_reports(user_id);
CREATE INDEX idx_bug_reports_category ON bug_reports(category);
CREATE INDEX idx_bug_reports_status ON bug_reports(status);
CREATE INDEX idx_bug_reports_created_at ON bug_reports(created_at DESC);

-- Enable Row Level Security
ALTER TABLE bug_reports ENABLE ROW LEVEL SECURITY;

-- Users can insert their own bug reports
CREATE POLICY "Users can insert own bug reports" ON bug_reports
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Users can view their own bug reports
CREATE POLICY "Users can view own bug reports" ON bug_reports
    FOR SELECT USING (auth.uid() = user_id);

-- Note: Admin access would be configured separately (service role key or admin role)
-- For now, users can only see their own reports

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_bug_reports_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_bug_reports_updated_at
    BEFORE UPDATE ON bug_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_bug_reports_updated_at();

-- Create storage bucket for screenshots (run separately or via dashboard)
-- INSERT INTO storage.buckets (id, name, public) VALUES ('bug-screenshots', 'bug-screenshots', false);

-- Storage policies for bug screenshots bucket (run after bucket is created)
-- CREATE POLICY "Users can upload screenshots" ON storage.objects
--     FOR INSERT WITH CHECK (
--         bucket_id = 'bug-screenshots' AND
--         auth.uid() IS NOT NULL
--     );

-- CREATE POLICY "Users can view own screenshots" ON storage.objects
--     FOR SELECT USING (
--         bucket_id = 'bug-screenshots' AND
--         (storage.foldername(name))[1] = auth.uid()::text
--     );
