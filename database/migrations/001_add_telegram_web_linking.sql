-- Migration: Add Telegram-Web account linking support
-- Run this on your existing Supabase database to add account linking features
-- This migration is safe to run multiple times (uses IF NOT EXISTS / IF EXISTS)

-- ============================================================================
-- Step 1: Add new columns to users table
-- ============================================================================

-- Add telegram_user_id column (for explicit Telegram ID storage)
ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_user_id TEXT UNIQUE;

-- Add clerk_user_id column (for Clerk/web user ID after linking)
ALTER TABLE users ADD COLUMN IF NOT EXISTS clerk_user_id TEXT UNIQUE;

-- Add email column for account unification (stores email after successful linking)
ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR UNIQUE;

-- Add email_verified_at to track when account was linked
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP WITH TIME ZONE;

-- Create indexes for the new columns
CREATE INDEX IF NOT EXISTS idx_users_telegram_user_id ON users(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_users_clerk_user_id ON users(clerk_user_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ============================================================================
-- Step 2: Create telegram_linking_codes table (for web-initiated linking)
-- ============================================================================
-- Flow:
-- 1. Web user generates a code (stored here with clerk_user_id and clerk_email)
-- 2. Telegram user sends /linkweb CODE to the bot
-- 3. Code is validated, marked as used, accounts are linked
-- 4. User record is updated with email and email_verified_at

CREATE TABLE IF NOT EXISTS telegram_linking_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(8) NOT NULL UNIQUE,              -- 8-char alphanumeric code
    clerk_user_id TEXT NOT NULL,                  -- Clerk user ID from web
    clerk_email TEXT NOT NULL,                    -- Email from Clerk (already verified)
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, -- Code expiration (10 min TTL)
    used_at TIMESTAMP WITH TIME ZONE,             -- When code was used (NULL if unused)
    linked_user_id INTEGER REFERENCES users(id),  -- Telegram user that claimed the code
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_linking_codes_code ON telegram_linking_codes(code);
CREATE INDEX IF NOT EXISTS idx_linking_codes_clerk_user ON telegram_linking_codes(clerk_user_id);

-- ============================================================================
-- Step 3: Backfill telegram_user_id for existing Telegram users
-- ============================================================================
-- For existing users where external_user_id looks like a Telegram ID (numeric),
-- copy it to telegram_user_id
UPDATE users 
SET telegram_user_id = external_user_id 
WHERE telegram_user_id IS NULL 
  AND external_user_id ~ '^\d+$';

-- ============================================================================
-- Done! Your database now supports Telegram-Web account linking.
-- ============================================================================

