-- Database Schema
-- This file contains the SQL schema for reference.
-- To apply migrations, use Supabase Dashboard or run SQL directly.
-- WARNING: This will drop all existing tables and recreate them!

-- ============================================================================
-- Drop existing tables (in reverse dependency order)
-- ============================================================================

DROP TABLE IF EXISTS nutritional_info;
DROP TABLE IF EXISTS spreadsheet_configs;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS chats;
DROP TABLE IF EXISTS users;

-- ============================================================================
-- Create tables
-- ============================================================================

-- users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_user_id NUMERIC UNIQUE,
    username VARCHAR,
    first_name VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_telegram_user_id ON users(telegram_user_id);

-- chats table
CREATE TABLE IF NOT EXISTS chats (
    id SERIAL PRIMARY KEY,
    telegram_chat_id NUMERIC UNIQUE,
    user_id INTEGER REFERENCES users(id),
    chat_type VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_chats_telegram_chat_id ON chats(telegram_chat_id);
CREATE INDEX IF NOT EXISTS idx_chat_user_id ON chats(user_id);

-- messages table
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER NOT NULL REFERENCES chats(id),
    telegram_message_id NUMERIC,
    text TEXT,
    role VARCHAR NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'bot')),
    message_type VARCHAR NOT NULL DEFAULT 'text' CHECK (message_type IN ('text', 'photo', 'document')),
    from_user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_message_chat_id ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_message_from_user_id ON messages(from_user_id);
CREATE INDEX IF NOT EXISTS idx_message_role ON messages(role);
CREATE INDEX IF NOT EXISTS idx_message_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_message_type ON messages(message_type);

-- spreadsheet_configs table
CREATE TABLE IF NOT EXISTS spreadsheet_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
    spreadsheet_id VARCHAR,
    oauth_token TEXT,
    refresh_token TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_spreadsheet_configs_user_id ON spreadsheet_configs(user_id);

-- nutritional_info table
CREATE TABLE IF NOT EXISTS nutritional_info (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    calories NUMERIC NOT NULL,
    proteins NUMERIC NOT NULL,
    carbs NUMERIC NOT NULL,
    fats NUMERIC NOT NULL,
    meal_type VARCHAR NOT NULL,
    extra_details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nutritional_info_user_id ON nutritional_info(user_id);
CREATE INDEX IF NOT EXISTS idx_nutritional_info_created_at ON nutritional_info(created_at);

-- ============================================================================
-- Notes
-- ============================================================================
-- All timestamps use TIMESTAMP WITH TIME ZONE for proper timezone handling
-- Foreign keys ensure referential integrity
-- Indexes improve query performance
-- The role field distinguishes between user messages and bot responses
-- Bot messages have from_user_id as NULL and role as 'bot'
-- The message_type field indicates content type:
--   - 'text': Plain text message
--   - 'photo': Photo (check text field for caption)
--   - 'document': Document file (check text field for caption)
