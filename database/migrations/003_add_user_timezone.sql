-- Migration: Add timezone column to users table
-- This allows users to set their timezone for date display purposes
-- Database timestamps remain in UTC, but dates are converted to user timezone when displayed

-- Add timezone column with default 'UTC'
ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'UTC';

-- Done!
