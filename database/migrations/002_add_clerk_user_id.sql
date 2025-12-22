-- Migration: Add clerk_user_id column to users table
-- Run this if you already ran 001_add_telegram_web_linking.sql before this column was added

-- Add clerk_user_id column (for Clerk/web user ID after linking)
ALTER TABLE users ADD COLUMN IF NOT EXISTS clerk_user_id TEXT UNIQUE;

-- Create index for the new column
CREATE INDEX IF NOT EXISTS idx_users_clerk_user_id ON users(clerk_user_id);

-- Done!

