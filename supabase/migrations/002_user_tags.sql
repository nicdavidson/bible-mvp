-- Migration: 002_user_tags
-- Description: Create user_tags table and note_tags junction table for tagging notes
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/_/sql

-- Create user_tags table for user-defined tags with colors
CREATE TABLE user_tags (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    name TEXT NOT NULL,
    color TEXT NOT NULL,  -- hex color e.g. "#ef4444"
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, name)
);

-- Create note_tags junction table for many-to-many relationship
CREATE TABLE note_tags (
    note_id BIGINT REFERENCES user_notes(id) ON DELETE CASCADE,
    tag_id BIGINT REFERENCES user_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (note_id, tag_id)
);

-- Create indexes for fast lookups
CREATE INDEX idx_user_tags_user_id ON user_tags(user_id);
CREATE INDEX idx_note_tags_note_id ON note_tags(note_id);
CREATE INDEX idx_note_tags_tag_id ON note_tags(tag_id);

-- Enable Row Level Security
ALTER TABLE user_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE note_tags ENABLE ROW LEVEL SECURITY;

-- Policies for user_tags: Users can only manage their own tags
CREATE POLICY "Users can view own tags" ON user_tags
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own tags" ON user_tags
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own tags" ON user_tags
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own tags" ON user_tags
    FOR DELETE USING (auth.uid() = user_id);

-- Policies for note_tags: Users can only manage tags on their own notes
-- We need to check that the note belongs to the user
CREATE POLICY "Users can view own note tags" ON note_tags
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_notes
            WHERE user_notes.id = note_tags.note_id
            AND user_notes.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert own note tags" ON note_tags
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM user_notes
            WHERE user_notes.id = note_tags.note_id
            AND user_notes.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete own note tags" ON note_tags
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM user_notes
            WHERE user_notes.id = note_tags.note_id
            AND user_notes.user_id = auth.uid()
        )
    );
