-- Migration: 003_reading_plans
-- Description: Create tables for user reading plan subscriptions and progress tracking
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/_/sql

-- Create user_reading_plans table for subscribed plans
CREATE TABLE user_reading_plans (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    plan_id TEXT NOT NULL,  -- e.g., "chronological", "canonical", etc.
    start_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, plan_id)
);

-- Create reading_plan_progress table for tracking completed days
CREATE TABLE reading_plan_progress (
    id BIGSERIAL PRIMARY KEY,
    user_plan_id BIGINT REFERENCES user_reading_plans(id) ON DELETE CASCADE NOT NULL,
    day_number INTEGER NOT NULL,
    completed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_plan_id, day_number)
);

-- Create indexes for fast lookups
CREATE INDEX idx_user_reading_plans_user_id ON user_reading_plans(user_id);
CREATE INDEX idx_user_reading_plans_active ON user_reading_plans(user_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_reading_plan_progress_user_plan_id ON reading_plan_progress(user_plan_id);

-- Enable Row Level Security
ALTER TABLE user_reading_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE reading_plan_progress ENABLE ROW LEVEL SECURITY;

-- Policies for user_reading_plans: Users can only manage their own plans
CREATE POLICY "Users can view own plans" ON user_reading_plans
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own plans" ON user_reading_plans
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own plans" ON user_reading_plans
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own plans" ON user_reading_plans
    FOR DELETE USING (auth.uid() = user_id);

-- Policies for reading_plan_progress: Users can only manage progress on their own plans
CREATE POLICY "Users can view own progress" ON reading_plan_progress
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_reading_plans
            WHERE user_reading_plans.id = reading_plan_progress.user_plan_id
            AND user_reading_plans.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert own progress" ON reading_plan_progress
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM user_reading_plans
            WHERE user_reading_plans.id = reading_plan_progress.user_plan_id
            AND user_reading_plans.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete own progress" ON reading_plan_progress
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM user_reading_plans
            WHERE user_reading_plans.id = reading_plan_progress.user_plan_id
            AND user_reading_plans.user_id = auth.uid()
        )
    );

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update updated_at on user_reading_plans
CREATE TRIGGER update_user_reading_plans_updated_at
    BEFORE UPDATE ON user_reading_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
