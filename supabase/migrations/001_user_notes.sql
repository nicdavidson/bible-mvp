-- Migration: 001_user_notes
-- Description: Create user_notes table for synced notes across devices
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/_/sql

-- Create user_notes table
CREATE TABLE user_notes (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    start_verse INTEGER NOT NULL,
    end_verse INTEGER,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for fast lookups
CREATE INDEX idx_user_notes_user_id ON user_notes(user_id);
CREATE INDEX idx_user_notes_reference ON user_notes(book, chapter);

-- Enable Row Level Security
ALTER TABLE user_notes ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own notes
CREATE POLICY "Users can view own notes" ON user_notes
    FOR SELECT USING (auth.uid() = user_id);

-- Policy: Users can insert their own notes
CREATE POLICY "Users can insert own notes" ON user_notes
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own notes
CREATE POLICY "Users can update own notes" ON user_notes
    FOR UPDATE USING (auth.uid() = user_id);

-- Policy: Users can delete their own notes
CREATE POLICY "Users can delete own notes" ON user_notes
    FOR DELETE USING (auth.uid() = user_id);
